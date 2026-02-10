mod commands;
mod events;
mod ipc;
mod sidecar;
mod state;

use state::AppState;
use tauri::{Manager, State};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::init();
    let app_state = AppState::new();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            commands::rpc_call,
            commands::sidecar_status,
        ])
        .setup(|app| {
            let handle = app.handle().clone();

            // Spawn sidecar on app ready
            tauri::async_runtime::spawn(async move {
                let state: State<'_, AppState> = handle.state();
                let mut sidecar = state.sidecar.lock().await;

                match sidecar.start(handle.clone()).await {
                    Ok(()) => {
                        log::info!("Sidecar started successfully");
                        // Health check
                        match sidecar.call("health.check", None).await {
                            Ok(result) => log::info!("Sidecar health: {:?}", result),
                            Err(e) => log::error!("Sidecar health check failed: {}", e),
                        }
                    }
                    Err(e) => {
                        log::error!("Failed to start sidecar: {}", e);
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
