import { Button } from "@/components/ui/Button";
import type { Chapter } from "@/api/types";
import { cn } from "@/lib/cn";

interface ChapterCardProps {
  chapter: Chapter;
  onTranslate: () => void;
  onEdit: () => void;
}

export function ChapterCard({ chapter, onTranslate, onEdit }: ChapterCardProps) {
  const progress = chapter.segment_count && chapter.translated_count
    ? (chapter.translated_count / chapter.segment_count) * 100
    : 0;

  const isComplete = progress === 100;
  const hasProgress = progress > 0;

  return (
    <div
      className={cn(
        "p-4 border border-border rounded-lg bg-card hover:border-accent transition-colors",
        "flex items-center justify-between gap-4"
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-2">
          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary text-sm font-semibold">
            {chapter.order}
          </span>
          <h3 className="text-lg font-semibold truncate">{chapter.title}</h3>
        </div>

        {chapter.segment_count !== undefined && (
          <div className="ml-11">
            <div className="flex items-center gap-2 mb-1.5">
              <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full transition-all duration-300",
                    isComplete ? "bg-green-500" : "bg-primary"
                  )}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-xs text-muted-foreground font-medium min-w-[3rem] text-right">
                {Math.round(progress)}%
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              {chapter.translated_count || 0} / {chapter.segment_count} segments
            </div>
          </div>
        )}

        {chapter.translation_stale && (
          <div className="ml-11 mt-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 text-xs font-medium">
              Translation stale
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" onClick={onEdit}>
          Edit
        </Button>
        <Button
          variant={hasProgress ? "secondary" : "primary"}
          size="sm"
          onClick={onTranslate}
        >
          {hasProgress ? "Continue" : "Translate"}
        </Button>
      </div>
    </div>
  );
}
