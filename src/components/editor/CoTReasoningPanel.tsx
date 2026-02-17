import { useTranslation } from "react-i18next";
import { useEditorStore } from "@/stores/editor-store";
import { cn } from "@/lib/cn";
import { api } from "@/api/tauri-bridge";
import { useQuery } from "@tanstack/react-query";

interface CoTReasoningPanelProps {
  chapterId: number;
}

export function CoTReasoningPanel({ chapterId: _chapterId }: CoTReasoningPanelProps) {
  const { t } = useTranslation("editor");
  const { activeSegmentId, showReasoning, toggleReasoning, segmentMap } = useEditorStore();
  const useCoT = useEditorStore((s) => s.useCoT);

  const activeSegment = activeSegmentId
    ? segmentMap.find((entry) => entry.segment_id === activeSegmentId)
    : null;
  const batchId = activeSegment?.batch_id;

  const { data: reasoningData } = useQuery({
    queryKey: ["batch-reasoning", batchId],
    queryFn: () => api.getBatchReasoning(batchId!),
    enabled: !!batchId,
  });

  if (!activeSegmentId) {
    return null;
  }

  return (
    <div className="border-t border-border bg-card/50">
      <button
        onClick={toggleReasoning}
        className="w-full px-6 py-3 flex items-center justify-between text-sm font-medium hover:bg-accent/50 transition-colors"
      >
        <span className="flex items-center gap-2">
          <span className="text-muted-foreground">{t("cotPanel.title")}</span>
          {activeSegmentId && (
            <span className="text-xs text-muted-foreground/70">
              {t("cotPanel.segment", { id: activeSegmentId })}
            </span>
          )}
        </span>
        <svg
          className={cn("w-4 h-4 text-muted-foreground transition-transform", showReasoning && "rotate-180")}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {showReasoning && (
        <div className="px-6 py-4 space-y-4 text-sm border-t border-border/50">
          {!useCoT ? (
            <p className="text-muted-foreground italic">
              {t("cotPanel.notUsed")}
            </p>
          ) : !batchId ? (
            <p className="text-muted-foreground italic">
              {t("cotPanel.notAvailable")}
            </p>
          ) : !reasoningData?.found ? (
            <p className="text-muted-foreground italic">
              {t("cotPanel.notFound", { batchId })}
            </p>
          ) : (
            <>
              {reasoningData.situation_summary && (
                <div>
                  <h3 className="font-semibold text-xs uppercase tracking-wide text-muted-foreground mb-2">
                    {t("cotPanel.situationSummary")}
                  </h3>
                  <p className="text-foreground/90 leading-relaxed">{reasoningData.situation_summary}</p>
                </div>
              )}

              {reasoningData.character_events && typeof reasoningData.character_events === "object" && Object.keys(reasoningData.character_events).length > 0 && (
                <div>
                  <h3 className="font-semibold text-xs uppercase tracking-wide text-muted-foreground mb-2">
                    {t("cotPanel.characterEvents")}
                  </h3>
                  <ul className="space-y-1">
                    {Object.entries(reasoningData.character_events).map(([character, events]) => (
                      <li key={character} className="text-foreground/90 leading-relaxed">
                        <span className="font-medium">{character}:</span> {String(events)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {reasoningData.review_feedback && typeof reasoningData.review_feedback === "object" && Object.keys(reasoningData.review_feedback).length > 0 && (
                <div>
                  <h3 className="font-semibold text-xs uppercase tracking-wide text-muted-foreground mb-2">
                    {t("cotPanel.reviewFeedback")}
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(reasoningData.review_feedback).map(([key, value]) => (
                      <div key={key}>
                        <span className="font-medium text-foreground/80">{key}:</span>{" "}
                        <span className="text-foreground/90">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
