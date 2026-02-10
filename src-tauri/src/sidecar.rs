use std::collections::HashMap;
use std::process::Stdio;
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::{oneshot, Mutex, RwLock};
use log::info;
use serde_json::Value;

use tauri::{Emitter, Manager};

use crate::ipc::{JsonRpcRequest, JsonRpcResponse, JsonRpcNotification};

type PendingRequests = Arc<Mutex<HashMap<u64, oneshot::Sender<Result<Value, String>>>>>;

pub struct SidecarProcess {
    child: Option<Child>,
    stdin: Option<tokio::process::ChildStdin>,
    pending: PendingRequests,
    connected: Arc<RwLock<bool>>,
}

impl SidecarProcess {
    pub fn new() -> Self {
        Self {
            child: None,
            stdin: None,
            pending: Arc::new(Mutex::new(HashMap::new())),
            connected: Arc::new(RwLock::new(false)),
        }
    }

    pub async fn start(&mut self, app_handle: tauri::AppHandle) -> Result<(), String> {
        // Try to find sidecar - in dev mode, run Python directly
        let mut cmd = if cfg!(debug_assertions) {
            // Dev mode: run Python module directly
            let mut c = Command::new("python3.11");
            c.args(["-m", "fiction_translator"]);
            c.current_dir(
                std::env::current_dir()
                    .unwrap()
                    .parent()
                    .unwrap()
                    .join("sidecar"),
            );
            c
        } else {
            // Production: use bundled binary
            let sidecar_path = app_handle
                .path()
                .resource_dir()
                .map_err(|e| e.to_string())?
                .join("binaries")
                .join(if cfg!(target_os = "windows") {
                    "fiction-translator-sidecar.exe"
                } else {
                    "fiction-translator-sidecar"
                });
            Command::new(sidecar_path)
        };

        cmd.stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        let mut child = cmd.spawn().map_err(|e| format!("Failed to spawn sidecar: {e}"))?;

        let stdin = child.stdin.take().ok_or("Failed to capture stdin")?;
        let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;
        let stderr = child.stderr.take().ok_or("Failed to capture stderr")?;

        self.stdin = Some(stdin);
        self.child = Some(child);

        let pending = self.pending.clone();
        let connected = self.connected.clone();
        let app = app_handle.clone();

        // Spawn stdout reader (JSON-RPC responses + notifications)
        tokio::spawn(async move {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();

            while let Ok(Some(line)) = lines.next_line().await {
                if line.trim().is_empty() {
                    continue;
                }

                // Try to parse as response (has "id" field)
                if let Ok(response) = serde_json::from_str::<JsonRpcResponse>(&line) {
                    if let Some(id) = response.id {
                        let mut pending = pending.lock().await;
                        if let Some(sender) = pending.remove(&id) {
                            let result = if let Some(error) = response.error {
                                Err(error.to_string())
                            } else {
                                Ok(response.result.unwrap_or(Value::Null))
                            };
                            let _ = sender.send(result);
                        }
                        continue;
                    }
                }

                // Try to parse as notification (no "id" field)
                if let Ok(notification) = serde_json::from_str::<JsonRpcNotification>(&line) {
                    // Forward as Tauri event
                    let event_name = notification.method.replace('.', ":");
                    if let Some(params) = notification.params {
                        let _ = app.emit(&event_name, params);
                    }
                }
            }

            *connected.write().await = false;
            let _ = app.emit("sidecar:status", serde_json::json!({"connected": false}));
        });

        // Spawn stderr reader (logging)
        tokio::spawn(async move {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();

            while let Ok(Some(line)) = lines.next_line().await {
                info!("[sidecar] {}", line);
            }
        });

        *self.connected.write().await = true;
        let _ = app_handle.emit("sidecar:status", serde_json::json!({"connected": true}));

        info!("Sidecar process started successfully");
        Ok(())
    }

    pub async fn call(&mut self, method: &str, params: Option<Value>) -> Result<Value, String> {
        let stdin = self.stdin.as_mut().ok_or("Sidecar not started")?;

        let request = JsonRpcRequest::new(method, params);
        let id = request.id;
        let line = request.to_line();

        let (tx, rx) = oneshot::channel();
        self.pending.lock().await.insert(id, tx);

        stdin
            .write_all(line.as_bytes())
            .await
            .map_err(|e| format!("Failed to write to sidecar: {e}"))?;

        stdin
            .flush()
            .await
            .map_err(|e| format!("Failed to flush sidecar stdin: {e}"))?;

        // Wait for response with timeout
        match tokio::time::timeout(std::time::Duration::from_secs(120), rx).await {
            Ok(Ok(result)) => result,
            Ok(Err(_)) => Err("Response channel closed".to_string()),
            Err(_) => {
                self.pending.lock().await.remove(&id);
                Err("Sidecar call timed out after 120s".to_string())
            }
        }
    }

    pub async fn stop(&mut self) {
        if let Some(mut child) = self.child.take() {
            let _ = child.kill().await;
            info!("Sidecar process stopped");
        }
        self.stdin = None;
        *self.connected.write().await = false;
    }

    pub async fn is_connected(&self) -> bool {
        *self.connected.read().await
    }
}
