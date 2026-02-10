import { useEffect } from "react";
import { onPipelineProgress } from "@/api/tauri-bridge";
import { usePipelineStore } from "@/stores/pipeline-store";

export function useProgress() {
  const setProgress = usePipelineStore((s) => s.setProgress);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    onPipelineProgress((p) => {
      setProgress(p.stage, p.progress, p.message);
    }).then((fn) => { unlisten = fn; });
    return () => { unlisten?.(); };
  }, [setProgress]);

  return usePipelineStore();
}
