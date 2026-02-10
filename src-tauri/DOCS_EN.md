# Fiction Translator v2.0 — Tauri Rust Shell Documentation

## Overview

The Tauri Rust shell is the "glue" between the React frontend and the Python sidecar. It manages the native window, spawns the Python process, proxies JSON-RPC calls, and forwards events.

**Architecture Summary:**
- **Frontend (React)**: UI components, state management (Zustand), user interaction
- **Rust Shell (Tauri)**: Window management, process lifecycle, IPC routing
- **Python Sidecar**: Core business logic, LLM integration, translation pipeline

The Rust layer is intentionally thin — it handles infrastructure concerns while delegating all business logic to Python.

## Why This Architecture?

### Why Tauri (not Electron)?

| Aspect | Tauri | Electron |
|--------|-------|----------|
| **Bundle Size** | ~15MB | ~150MB |
| **Memory Usage** | Lower (shared system webview) | Higher (bundled Chromium) |
| **Performance** | Native Rust backend | Node.js backend |
| **Security** | Fine-grained permission system | Broader permissions |
| **Maturity** | Tauri v2 is production-ready | Very mature |

**Key Benefits:**
- 10x smaller bundle size makes distribution faster
- System webview reduces memory footprint
- Rust's performance and safety guarantees
- Modern plugin ecosystem with active development

### Why Rust as the shell (not Node.js)?

1. **Native to Tauri**: Tauri's core is written in Rust, making it the natural choice
2. **Robust Process Management**: Rust's async runtime (Tokio) excels at managing child processes with stdin/stdout/stderr
3. **Type Safety**: Compile-time guarantees for IPC message handling via serde
4. **Performance**: Zero-cost abstractions, no garbage collection pauses
5. **Reliability**: Strong error handling with Result types

### Why stdin/stdout IPC (not HTTP or WebSocket)?

| Approach | Pros | Cons |
|----------|------|------|
| **stdin/stdout** | No port conflicts, simple, secure, tied to process lifecycle | Only works with local processes |
| **HTTP** | Language-agnostic, familiar | Port conflicts, requires server setup, network exposure |
| **WebSocket** | Bidirectional, real-time | Similar issues to HTTP |

**Why stdin/stdout wins:**
- **Guaranteed availability**: stdin/stdout always exists, no port conflicts
- **Native Tauri pattern**: Sidecar communication via pipes is idiomatic
- **Simplicity**: Line-based JSON protocol, no server setup
- **Security**: No network exposure, communication is private to the process
- **Lifecycle binding**: When the app closes, the Python process automatically terminates

### Why the Rust shell is thin?

**Philosophy**: Keep the Rust layer minimal, put business logic in Python.

**Benefits:**
- Faster iteration: Python changes don't require Rust recompilation
- Language choice: Python is better suited for LLM integration and data processing
- Maintainability: You rarely need to touch Rust code
- Separation of concerns: Infrastructure (Rust) vs. business logic (Python)

**Rust responsibilities:**
- Window lifecycle management
- Python process spawning and monitoring
- JSON-RPC message routing
- Event forwarding

**Python responsibilities:**
- Translation pipeline execution
- LLM API integration
- Database operations
- File processing
- All business logic

## Directory Structure

```
src-tauri/
├── Cargo.toml                  # Rust dependencies and package metadata
├── tauri.conf.json             # Tauri app configuration (window, build, plugins)
├── build.rs                    # Build script (auto-generated)
├── capabilities/
│   └── default.json            # Tauri v2 permission capabilities
└── src/
    ├── main.rs                 # Entry point (minimal, calls lib::run())
    ├── lib.rs                  # App builder, plugin registration, setup hook
    ├── sidecar.rs              # Python process lifecycle management
    ├── ipc.rs                  # JSON-RPC message type definitions
    ├── commands.rs             # Tauri command handlers (RPC bridge)
    ├── state.rs                # Shared application state
    └── events.rs               # Event type definitions
```

## Module Documentation

### main.rs — Entry Point

```rust
fn main() {
    env_logger::init();
    fiction_translator_v2_lib::run();
}
```

**Purpose**: Minimal entry point that initializes logging and delegates to the library.

**Why separate from lib.rs?**
- Allows the library to be used as both a binary and a library
- Follows Rust best practices for binary crates
- `#[cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` prevents console window on Windows in release builds

### lib.rs — App Builder

The heart of the Tauri application setup.

```rust
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
```

**Components:**

1. **Plugin Registration**
   - `.plugin(tauri_plugin_shell::init())`: Enables shell commands and sidecar support
   - Plugins provide additional capabilities (file system, HTTP, etc.)

2. **State Management**
   - `.manage(app_state)`: Makes `AppState` available to all commands
   - State is shared across the application via `Arc<Mutex<T>>`

3. **Command Handler Registration**
   - `invoke_handler`: Registers commands that can be called from the frontend
   - `commands::rpc_call`: Main RPC bridge to Python
   - `commands::sidecar_status`: Health check command

4. **Setup Hook**
   - Runs once when the app is ready
   - Spawns an async task to start the Python sidecar
   - Performs health check via `health.check` RPC call
   - Errors are logged but don't prevent the app from starting (graceful degradation)

### sidecar.rs — Process Lifecycle (MOST IMPORTANT)

This is the core of the Rust shell. It manages the Python process lifecycle and handles all IPC communication.

#### Data Structures

```rust
type PendingRequests = Arc<Mutex<HashMap<u64, oneshot::Sender<Result<Value, String>>>>>;

pub struct SidecarProcess {
    child: Option<Child>,                    // Python process handle
    stdin: Option<tokio::process::ChildStdin>,  // stdin pipe for sending requests
    pending: PendingRequests,                // Map of request IDs to response channels
    connected: Arc<RwLock<bool>>,            // Connection status flag
}
```

**Design notes:**
- `pending`: Tracks in-flight RPC requests by ID, allowing async request/response matching
- `connected`: Shared flag readable from multiple tasks to check connection status
- `Arc<Mutex<T>>` allows safe sharing between async tasks

#### Constructor

```rust
pub fn new() -> Self
```

Creates an empty `SidecarProcess` with no running process.

#### Process Startup

```rust
pub async fn start(&mut self, app_handle: tauri::AppHandle) -> Result<(), String>
```

**Behavior:**

1. **Environment Detection**:
   - **Dev mode** (`cfg!(debug_assertions)`): Runs `python -m fiction_translator` from `../sidecar/` directory
   - **Production**: Uses bundled binary from `resources/binaries/fiction-translator-sidecar[.exe]`

2. **Process Spawn**:
   - Configures stdin/stdout/stderr as piped (captured)
   - Spawns the Python process
   - Extracts pipe handles

3. **Background Tasks**:
   - **Stdout reader**: Parses JSON-RPC responses and notifications
   - **Stderr reader**: Logs Python's stderr output

4. **Status Update**:
   - Sets `connected` flag to `true`
   - Emits `sidecar:status` event to frontend

**Stdout Reader Task** (lines 78-115):

```rust
tokio::spawn(async move {
    let reader = BufReader::new(stdout);
    let mut lines = reader.lines();

    while let Ok(Some(line)) = lines.next_line().await {
        // Try to parse as response (has "id" field)
        if let Ok(response) = serde_json::from_str::<JsonRpcResponse>(&line) {
            if let Some(id) = response.id {
                // Match to pending request and send result
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

    // Process ended
    *connected.write().await = false;
    let _ = app.emit("sidecar:status", serde_json::json!({"connected": false}));
});
```

**Key behaviors:**
- Reads stdout line-by-line (JSON-RPC messages are newline-delimited)
- **Responses** (have `id`): Matched to pending requests via the ID
- **Notifications** (no `id`): Converted to Tauri events (e.g., `pipeline.progress` → `pipeline:progress`)
- When stdout ends (process died), sets `connected = false` and emits status event

**Stderr Reader Task** (lines 118-125):

```rust
tokio::spawn(async move {
    let reader = BufReader::new(stderr);
    let mut lines = reader.lines();

    while let Ok(Some(line)) = lines.next_line().await {
        info!("[sidecar] {}", line);
    }
});
```

Simple: forwards Python's stderr to Rust's logger.

#### RPC Call

```rust
pub async fn call(&mut self, method: &str, params: Option<Value>) -> Result<Value, String>
```

Sends a JSON-RPC request to Python and waits for the response.

**Flow:**

1. Create a `JsonRpcRequest` with auto-incrementing ID
2. Serialize to JSON and append newline
3. Create a oneshot channel for the response
4. Store the sender in `pending` map (keyed by request ID)
5. Write the request to stdin
6. Flush stdin to ensure delivery
7. Wait for response with 120-second timeout
8. Return result or error

**Timeout behavior:**
- If no response after 120s, removes the pending request and returns timeout error
- Prevents memory leaks from lost requests

**Example:**
```rust
let result = sidecar.call("project.list", None).await?;
```

Sends: `{"jsonrpc":"2.0","method":"project.list","id":1}\n`

Receives: `{"jsonrpc":"2.0","id":1,"result":[...]}\n`

#### Process Shutdown

```rust
pub async fn stop(&mut self)
```

Kills the Python process and cleans up state:
- Calls `child.kill()` to terminate the process
- Clears stdin handle
- Sets `connected = false`

#### Connection Status

```rust
pub async fn is_connected(&self) -> bool
```

Thread-safe read of the connection status flag.

### ipc.rs — Message Types

Defines the JSON-RPC 2.0 protocol types.

#### Request ID Generation

```rust
static REQUEST_ID: AtomicU64 = AtomicU64::new(1);

pub fn next_id() -> u64 {
    REQUEST_ID.fetch_add(1, Ordering::Relaxed)
}
```

Thread-safe auto-incrementing ID generator. Starts at 1 and increments atomically.

#### JsonRpcRequest

```rust
#[derive(Debug, Serialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<Value>,
    pub id: u64,
}

impl JsonRpcRequest {
    pub fn new(method: &str, params: Option<Value>) -> Self
    pub fn to_line(&self) -> String  // Serializes to JSON + "\n"
}
```

**Example:**
```json
{"jsonrpc":"2.0","method":"project.list","params":null,"id":42}
```

#### JsonRpcResponse

```rust
#[derive(Debug, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: Option<u64>,
    pub result: Option<Value>,
    pub error: Option<JsonRpcError>,
}
```

**Behavior:**
- If `id` is present: it's a response to a request
- If `id` is absent: it's a notification (should be parsed as `JsonRpcNotification`)
- Either `result` or `error` should be present (not both)

#### JsonRpcError

```rust
#[derive(Debug, Deserialize, Clone)]
pub struct JsonRpcError {
    pub code: i64,
    pub message: String,
    pub data: Option<Value>,
}

impl std::fmt::Display for JsonRpcError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "RPC Error {}: {}", self.code, self.message)
    }
}
```

Standard JSON-RPC error object. `Display` implementation allows easy error printing.

#### JsonRpcNotification

```rust
#[derive(Debug, Deserialize)]
pub struct JsonRpcNotification {
    pub method: String,
    pub params: Option<Value>,
}
```

A message from Python that doesn't expect a response (no `id` field).

**Example:**
```json
{"jsonrpc":"2.0","method":"pipeline.progress","params":{"stage":"translation","progress":0.5}}
```

This gets converted to a Tauri event: `pipeline:progress` with the params as payload.

### commands.rs — Tauri Command Handlers

Exposes two commands to the frontend.

#### rpc_call

```rust
#[tauri::command]
pub async fn rpc_call(
    state: State<'_, AppState>,
    method: String,
    params: Option<Value>,
) -> Result<Value, String>
```

**Purpose**: Main bridge between frontend and Python.

**Flow:**
1. Acquires lock on the sidecar process
2. Calls `sidecar.call(method, params)`
3. Returns result or error to the frontend

**Frontend usage:**
```typescript
const result = await invoke('rpc_call', {
  method: 'project.list',
  params: null
});
```

#### sidecar_status

```rust
#[tauri::command]
pub async fn sidecar_status(state: State<'_, AppState>) -> Result<bool, String>
```

**Purpose**: Health check to verify the Python sidecar is running.

**Returns**: `true` if connected, `false` otherwise

**Frontend usage:**
```typescript
const isConnected = await invoke('sidecar_status');
```

### state.rs — Application State

```rust
pub struct AppState {
    pub sidecar: Arc<Mutex<SidecarProcess>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            sidecar: Arc::new(Mutex::new(SidecarProcess::new())),
        }
    }
}
```

**Purpose**: Shared state accessible to all Tauri commands.

**Design:**
- `Arc<Mutex<T>>`: Thread-safe shared ownership with interior mutability
- `Arc`: Multiple tasks can hold references to the same state
- `Mutex`: Ensures exclusive access during RPC calls

**Access pattern:**
```rust
pub async fn some_command(state: State<'_, AppState>) -> Result<Value, String> {
    let mut sidecar = state.sidecar.lock().await;
    sidecar.call("method", None).await
}
```

### events.rs — Event Type Definitions

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineProgressEvent {
    pub stage: String,
    pub progress: f64,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SidecarStatusEvent {
    pub connected: bool,
    pub error: Option<String>,
}
```

**Purpose**: Type-safe event payloads for documentation and future type checking.

**Note**: These types are currently **not enforced** at runtime (events use `serde_json::Value`), but they document the expected structure and can be used for stronger typing in the future.

**Event names:**
- `pipeline:progress`: Emitted during translation pipeline execution
- `sidecar:status`: Emitted when sidecar connection status changes

## Data Flow

### Request Flow (Frontend → Sidecar)

```
┌─────────────────────────────────────────────────────────────────────┐
│ React Frontend                                                      │
│                                                                     │
│  api.listProjects()                                                │
│    ↓                                                                │
│  invoke("rpc_call", {                                              │
│    method: "project.list",                                         │
│    params: {}                                                      │
│  })                                                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ IPC
┌─────────────────────────────────────────────────────────────────────┐
│ Tauri Rust Shell                                                    │
│                                                                     │
│  commands::rpc_call()                                              │
│    ↓                                                                │
│  state.sidecar.lock().await                                        │
│    ↓                                                                │
│  sidecar.call("project.list", {})                                  │
│    ↓                                                                │
│  JsonRpcRequest {                                                  │
│    jsonrpc: "2.0",                                                 │
│    method: "project.list",                                         │
│    id: 42                                                          │
│  }                                                                 │
│    ↓                                                                │
│  Write to stdin: {"jsonrpc":"2.0","method":"project.list","id":42}\n│
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ stdin pipe
┌─────────────────────────────────────────────────────────────────────┐
│ Python Sidecar                                                      │
│                                                                     │
│  JSON-RPC Server reads line from stdin                             │
│    ↓                                                                │
│  Parses request                                                    │
│    ↓                                                                │
│  Routes to ProjectService.list_projects()                          │
│    ↓                                                                │
│  Executes business logic                                           │
│    ↓                                                                │
│  Returns result                                                    │
│    ↓                                                                │
│  Writes to stdout:                                                 │
│    {"jsonrpc":"2.0","id":42,"result":[...]}\n                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ stdout pipe
┌─────────────────────────────────────────────────────────────────────┐
│ Tauri Rust Shell                                                    │
│                                                                     │
│  Stdout reader task reads line                                     │
│    ↓                                                                │
│  Parses as JsonRpcResponse                                         │
│    ↓                                                                │
│  Matches id=42 to pending request                                  │
│    ↓                                                                │
│  Sends result via oneshot channel                                  │
│    ↓                                                                │
│  sidecar.call() receives result                                    │
│    ↓                                                                │
│  commands::rpc_call() returns Value                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ IPC
┌─────────────────────────────────────────────────────────────────────┐
│ React Frontend                                                      │
│                                                                     │
│  invoke() resolves with result                                     │
│    ↓                                                                │
│  api.listProjects() returns Project[]                              │
│    ↓                                                                │
│  UI updates                                                        │
└─────────────────────────────────────────────────────────────────────┘
```

**Key points:**
- Request ID (`42`) is used to match async response to the correct pending request
- Mutex ensures only one RPC call writes to stdin at a time (serialization)
- 120-second timeout prevents hanging on unresponsive Python process

### Event Flow (Sidecar → Frontend)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Python Sidecar                                                      │
│                                                                     │
│  During pipeline execution:                                        │
│    await server.send_notification(                                 │
│      "pipeline.progress",                                          │
│      {                                                             │
│        "stage": "translation",                                     │
│        "progress": 0.5,                                            │
│        "message": "Translating batch 1/2"                          │
│      }                                                             │
│    )                                                               │
│    ↓                                                                │
│  Writes to stdout:                                                 │
│    {"jsonrpc":"2.0","method":"pipeline.progress","params":{...}}\n │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ stdout pipe
┌─────────────────────────────────────────────────────────────────────┐
│ Tauri Rust Shell                                                    │
│                                                                     │
│  Stdout reader task reads line                                     │
│    ↓                                                                │
│  Tries to parse as JsonRpcResponse (has "id")                      │
│    → Fails (no "id" field)                                         │
│    ↓                                                                │
│  Tries to parse as JsonRpcNotification (no "id")                   │
│    → Success!                                                      │
│    ↓                                                                │
│  Converts method name:                                             │
│    "pipeline.progress" → "pipeline:progress"                       │
│    ↓                                                                │
│  app_handle.emit("pipeline:progress", params)                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ Tauri event system
┌─────────────────────────────────────────────────────────────────────┐
│ React Frontend                                                      │
│                                                                     │
│  listen("pipeline:progress", (event) => {                          │
│    const { stage, progress, message } = event.payload;            │
│    usePipelineStore.getState().setProgress(stage, progress);      │
│  })                                                                │
│    ↓                                                                │
│  ProgressOverlay component re-renders                              │
│    ↓                                                                │
│  User sees updated progress bar and message                        │
└─────────────────────────────────────────────────────────────────────┘
```

**Key points:**
- Notifications have **no `id` field** (they don't expect a response)
- Method names use dot notation in Python (`pipeline.progress`)
- Converted to colon notation for Tauri events (`pipeline:progress`)
- Multiple listeners can subscribe to the same event

### Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ App Startup                                                         │
│                                                                     │
│  main() calls lib::run()                                           │
│    ↓                                                                │
│  tauri::Builder::default()                                         │
│    .plugin(tauri_plugin_shell::init())                             │
│    .manage(AppState::new())                                        │
│    .invoke_handler(...)                                            │
│    .setup(|app| {                                                  │
│      // Spawn async task                                           │
│      tauri::async_runtime::spawn(async move {                      │
│        let state = handle.state::<AppState>();                     │
│        let mut sidecar = state.sidecar.lock().await;               │
│                                                                     │
│        sidecar.start(handle.clone()).await?;                       │
│          ↓                                                          │
│          ┌─────────────────────────────────────────┐               │
│          │ 1. Detect environment (dev/prod)       │               │
│          │ 2. Spawn Python process                │               │
│          │ 3. Capture stdin/stdout/stderr         │               │
│          │ 4. Spawn stdout reader task            │               │
│          │ 5. Spawn stderr reader task            │               │
│          │ 6. Set connected = true                │               │
│          │ 7. Emit "sidecar:status" event         │               │
│          └─────────────────────────────────────────┘               │
│                                                                     │
│        // Health check                                             │
│        sidecar.call("health.check", None).await?;                  │
│      });                                                           │
│    })                                                              │
│    .run(...)                                                       │
│    ↓                                                                │
│  Frontend loads and connects to sidecar                            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Normal Operation                                                    │
│                                                                     │
│  Frontend → invoke("rpc_call") → Rust → Python → Rust → Frontend  │
│  Python → notification → Rust → event → Frontend                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ App Shutdown                                                        │
│                                                                     │
│  User closes window                                                │
│    ↓                                                                │
│  Tauri triggers cleanup                                            │
│    ↓                                                                │
│  Python process killed (child process termination)                 │
│    ↓                                                                │
│  Stdout reader task detects EOF                                    │
│    ↓                                                                │
│  Sets connected = false                                            │
│    ↓                                                                │
│  App exits                                                         │
└─────────────────────────────────────────────────────────────────────┘
```

**Error handling:**
- If sidecar fails to start: Error is logged, app continues (graceful degradation)
- If health check fails: Warning is logged, app continues
- If Python crashes during operation: `connected` becomes `false`, frontend can detect via `sidecar_status` command

## Configuration

### tauri.conf.json

```json
{
  "productName": "Fiction Translator",
  "version": "2.0.0",
  "identifier": "com.fiction-translator.v2",
  "build": {
    "beforeDevCommand": "",
    "beforeBuildCommand": "npm run build",
    "devUrl": "http://localhost:1420",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "title": "Fiction Translator",
        "width": 1400,
        "height": 900,
        "minWidth": 800,
        "minHeight": 600,
        "resizable": true,
        "fullscreen": false
      }
    ],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [...]
  },
  "plugins": {
    "shell": {
      "scope": [
        {
          "name": "translator-sidecar",
          "sidecar": true,
          "args": true
        }
      ]
    }
  }
}
```

**Key settings:**

- **identifier**: Unique app ID for the OS (`com.fiction-translator.v2`)
- **build.devUrl**: Dev server URL (Vite runs on port 1420)
- **build.frontendDist**: Production build output directory
- **app.windows**: Default window configuration
  - 1400x900 default size
  - Minimum 800x600
  - Resizable, not fullscreen
- **security.csp**: Content Security Policy disabled (allows inline scripts)
- **plugins.shell**: Allows executing the sidecar binary

### capabilities/default.json

```json
{
  "identifier": "default",
  "description": "Default permissions for Fiction Translator",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-execute",
    "shell:allow-open"
  ]
}
```

**Permissions:**

- `core:default`: Basic Tauri core functionality (window management, events, etc.)
- `shell:allow-execute`: Allows executing shell commands (required for sidecar)
- `shell:allow-open`: Allows opening files/URLs with default applications

**Security note**: These permissions are scoped to the main window only. Tauri v2's capability system provides fine-grained control over what the frontend can do.

### Cargo.toml

```toml
[package]
name = "fiction-translator-v2"
version = "2.0.0"
edition = "2021"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
log = "0.4"
env_logger = "0.11"

[lib]
name = "fiction_translator_v2_lib"
crate-type = ["staticlib", "cdylib", "rlib"]
```

**Key dependencies:**

- **tauri**: Core Tauri framework (v2)
- **tauri-plugin-shell**: Shell plugin for sidecar support
- **serde**: Serialization/deserialization framework
- **serde_json**: JSON support for RPC messages
- **tokio**: Async runtime (with `full` features for process, io, sync, etc.)
- **log**: Logging facade
- **env_logger**: Simple logger implementation

**Library configuration:**
- `staticlib`: For native integration
- `cdylib`: For dynamic linking
- `rlib`: For Rust library usage

## Development Workflow

### Running in Dev Mode

```bash
npm run tauri dev
```

**What happens:**
1. Vite dev server starts on `http://localhost:1420`
2. Tauri builds and runs the Rust app
3. Rust detects `cfg!(debug_assertions)` is true
4. Spawns `python -m fiction_translator` from `../sidecar/`
5. Python hot-reloads when code changes (if using watchdog)
6. Frontend hot-reloads when code changes (Vite HMR)

**Logs:**
- Rust logs: Console where you ran `npm run tauri dev`
- Python logs: Same console (via stderr reader)
- Frontend logs: Browser DevTools console

### Building for Production

```bash
npm run tauri build
```

**What happens:**
1. Runs `npm run build` (Vite build)
2. Compiles Rust in release mode
3. Bundles Python sidecar binary (via PyInstaller or similar)
4. Creates platform-specific installer (DMG, MSI, AppImage, etc.)

**Production behavior:**
- Rust loads sidecar from `resources/binaries/fiction-translator-sidecar[.exe]`
- All assets are bundled, no external dependencies
- Optimized performance (Rust release mode, minified JS)

### Debugging Sidecar Communication

**View RPC traffic:**

Add logging to `sidecar.rs`:
```rust
pub async fn call(&mut self, method: &str, params: Option<Value>) -> Result<Value, String> {
    let request = JsonRpcRequest::new(method, params);
    log::debug!("→ RPC: {}", serde_json::to_string(&request).unwrap());
    // ... send request ...
    log::debug!("← RPC response: {:?}", result);
    result
}
```

**Test sidecar independently:**
```bash
cd sidecar
python -m fiction_translator
# Then manually send JSON-RPC requests via stdin:
{"jsonrpc":"2.0","method":"health.check","id":1}
```

## Troubleshooting

### Sidecar won't start in dev mode

**Symptom**: "Failed to start sidecar" error

**Solutions:**
1. Check Python is installed and on PATH: `python --version`
2. Check you're in the right directory: `cd src-tauri && cargo run`
3. Check `../sidecar/` exists relative to `src-tauri/`
4. Verify Python module structure: `cd ../sidecar && python -m fiction_translator`

### Sidecar won't start in production

**Symptom**: App opens but sidecar status is disconnected

**Solutions:**
1. Verify bundled binary exists in `resources/binaries/`
2. Check binary has execute permissions (Unix)
3. Check antivirus isn't blocking the sidecar
4. Look for errors in Tauri logs

### RPC calls timeout

**Symptom**: "Sidecar call timed out after 120s"

**Possible causes:**
1. Python process is stuck/crashed (check stderr logs)
2. Request is malformed (Python can't parse it)
3. Python method doesn't exist or throws an error
4. Python is waiting for user input (shouldn't happen)

**Debug:**
- Add logging to Python RPC handler
- Test the Python method in isolation
- Reduce timeout temporarily to fail faster

### Events not reaching frontend

**Symptom**: `listen("pipeline:progress")` never fires

**Checklist:**
1. Python uses correct notification format (no `id` field)
2. Method name conversion is correct (`pipeline.progress` → `pipeline:progress`)
3. Frontend listener is registered before event is emitted
4. Check browser DevTools console for errors

## Extension Points

### Adding a new RPC method

**Python side** (`sidecar/src/fiction_translator/ipc/server.py`):
```python
async def handle_request(self, method: str, params: Any) -> Any:
    if method == "my_new_method":
        return await self.my_new_handler(params)
```

**Frontend side** (`src/lib/api.ts`):
```typescript
export async function myNewMethod(params: any) {
  return invoke('rpc_call', { method: 'my_new_method', params });
}
```

**No Rust changes needed!**

### Adding a new event

**Python side**:
```python
await server.send_notification("my.event", {"key": "value"})
```

**Frontend side**:
```typescript
import { listen } from '@tauri-apps/api/event';

listen('my:event', (event) => {
  console.log('Event received:', event.payload);
});
```

**No Rust changes needed!**

### Adding a new Tauri command

**Rust side** (`commands.rs`):
```rust
#[tauri::command]
pub async fn my_command(state: State<'_, AppState>) -> Result<String, String> {
    Ok("Hello from Rust!".to_string())
}
```

**Register in `lib.rs`**:
```rust
.invoke_handler(tauri::generate_handler![
    commands::rpc_call,
    commands::sidecar_status,
    commands::my_command,  // Add here
])
```

**Frontend side**:
```typescript
const result = await invoke('my_command');
```

## Best Practices

### When to modify Rust code

**Rarely needed:**
- Adding RPC methods → Python only
- Adding events → Python only
- UI changes → Frontend only
- Business logic → Python only

**Rust changes needed for:**
- New Tauri commands (direct Rust functionality)
- New plugins (file system, HTTP, etc.)
- Window management changes
- Deep integration with OS features

### Error handling

**Pattern:**
```rust
pub async fn something() -> Result<Value, String> {
    let result = risky_operation()
        .await
        .map_err(|e| format!("Context: {}", e))?;
    Ok(result)
}
```

**Always:**
- Use `Result<T, String>` for Tauri commands (String errors serialize nicely)
- Add context to errors (not just `.map_err(|e| e.to_string())`)
- Log errors before returning them
- Handle errors in frontend (don't assume success)

### Performance

**Tips:**
- RPC calls are async, don't block the UI
- Use events for progress updates (not polling)
- Batch multiple RPC calls when possible
- Consider streaming for large data transfers

### Security

**Remember:**
- stdin/stdout IPC is **local only** (no network exposure)
- Tauri's permission system protects against unauthorized access
- Validate inputs on the Python side (don't trust frontend)
- Sensitive data in RPC messages is not encrypted (local process only)

## Conclusion

The Tauri Rust shell is a thin, reliable bridge between the React UI and Python business logic. By keeping it minimal and delegating to Python, we achieve:

- Fast iteration (Python changes don't require recompilation)
- Small binary size (Rust is compiled, Python is interpreted)
- Clear separation of concerns (infrastructure vs. business logic)
- Robust process management (Tokio's async runtime)

For most development work, you'll interact with the Rust layer only when debugging IPC issues or adding native integrations. The design prioritizes simplicity and maintainability.
