use serde_json::Value;
use tauri::State;
use crate::state::AppState;

#[tauri::command]
pub async fn rpc_call(
    state: State<'_, AppState>,
    method: String,
    params: Option<Value>,
) -> Result<Value, String> {
    let mut sidecar = state.sidecar.lock().await;
    sidecar.call(&method, params).await
}

#[tauri::command]
pub async fn sidecar_status(state: State<'_, AppState>) -> Result<bool, String> {
    let sidecar = state.sidecar.lock().await;
    Ok(sidecar.is_connected().await)
}
