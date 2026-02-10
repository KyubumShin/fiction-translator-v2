import { useProgress } from "@/hooks/useProgress";
import { PipelineStageIndicator } from "./PipelineStageIndicator";
import { PIPELINE_STAGES } from "@/lib/constants";
import { Button } from "@/components/ui/Button";
import { api } from "@/api/tauri-bridge";

export function ProgressOverlay() {
  const { isRunning, progress, currentStage, message } = useProgress();

  if (!isRunning) {
    return null;
  }

  const handleCancel = async () => {
    await api.cancelPipeline();
  };

  // Map current stage to pipeline stages
  const getStageStatus = (stageKey: string): "completed" | "active" | "pending" => {
    if (!currentStage) return "pending";

    const currentIndex = PIPELINE_STAGES.findIndex(s => s.key === currentStage);
    const stageIndex = PIPELINE_STAGES.findIndex(s => s.key === stageKey);

    if (stageIndex < currentIndex) return "completed";
    if (stageIndex === currentIndex) return "active";
    return "pending";
  };

  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-md z-50 flex items-center justify-center">
      <div className="bg-card border border-border rounded-xl shadow-2xl p-8 w-full max-w-md">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-2">Translating Chapter</h2>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Progress</span>
            <span className="font-mono">{Math.round(progress * 100)}%</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-8 bg-secondary rounded-full h-2 overflow-hidden">
          <div
            className="bg-primary h-full transition-all duration-300 ease-out"
            style={{ width: `${progress * 100}%` }}
          />
        </div>

        {/* Pipeline Stages */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-muted-foreground mb-4 uppercase tracking-wide">
            Pipeline Stages
          </h3>
          <div className="space-y-3">
            {PIPELINE_STAGES.map((stage) => (
              <PipelineStageIndicator
                key={stage.key}
                label={stage.label}
                status={getStageStatus(stage.key)}
                detail={currentStage === stage.key ? message : undefined}
              />
            ))}
          </div>
        </div>

        {/* Cancel Button */}
        <div className="flex justify-end pt-4 border-t border-border">
          <Button variant="secondary" size="sm" onClick={handleCancel}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
