use std::sync::Arc;
use tokio::sync::Mutex;
use crate::sidecar::SidecarProcess;

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
