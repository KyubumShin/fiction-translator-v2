use serde::{Deserialize, Serialize};

// Kept for future use with Tauri event system
#[allow(dead_code)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineProgressEvent {
    pub stage: String,
    pub progress: f64,
    pub message: String,
}

// Kept for future use with Tauri event system
#[allow(dead_code)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SidecarStatusEvent {
    pub connected: bool,
    pub error: Option<String>,
}
