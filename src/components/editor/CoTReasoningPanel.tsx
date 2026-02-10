import { useEditorStore } from "@/stores/editor-store";
import { cn } from "@/lib/cn";

interface CoTReasoningPanelProps {
  chapterId: number;
}

export function CoTReasoningPanel({ chapterId: _chapterId }: CoTReasoningPanelProps) {
  const { activeSegmentId, showReasoning, toggleReasoning } = useEditorStore();

  // TODO: Fetch reasoning data based on active segment's batch_id
  const reasoningData = {
    situation: "Battle scene between warrior and dragon in a fantasy setting.",
    characterEvents: [
      "Warrior demonstrates courage by confronting the dragon",
      "Formal speech pattern suggests high status or nobility",
    ],
    translationReasoning: "Used formal register to match the warrior's dignified speech. 'How dare you' captures the indignation while maintaining literary quality.",
  };

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
          <span className="text-muted-foreground">Chain-of-Thought Reasoning</span>
          {activeSegmentId && (
            <span className="text-xs text-muted-foreground/70">
              (Segment #{activeSegmentId})
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
          <div>
            <h3 className="font-semibold text-xs uppercase tracking-wide text-muted-foreground mb-2">
              Situation Summary
            </h3>
            <p className="text-foreground/90 leading-relaxed">{reasoningData.situation}</p>
          </div>

          <div>
            <h3 className="font-semibold text-xs uppercase tracking-wide text-muted-foreground mb-2">
              Character Events
            </h3>
            <ul className="space-y-1">
              {reasoningData.characterEvents.map((event, i) => (
                <li key={i} className="text-foreground/90 leading-relaxed pl-4 relative before:content-['•'] before:absolute before:left-0">
                  {event}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-xs uppercase tracking-wide text-muted-foreground mb-2">
              Translation Reasoning
            </h3>
            <p className="text-foreground/90 leading-relaxed">{reasoningData.translationReasoning}</p>
          </div>
        </div>
      )}
    </div>
  );
}
