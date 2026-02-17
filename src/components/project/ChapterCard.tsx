import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/Button";
import type { Chapter } from "@/api/types";
import { cn } from "@/lib/cn";

interface ChapterCardProps {
  chapter: Chapter;
  onTranslate: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function ChapterCard({ chapter, onTranslate, onEdit, onDelete }: ChapterCardProps) {
  const { t } = useTranslation("project");

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
              {t("chapters.card.segments", { translated: chapter.translated_count || 0, total: chapter.segment_count })}
            </div>
          </div>
        )}

        {chapter.translation_stale && (
          <div className="ml-11 mt-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 text-xs font-medium">
              {t("chapters.card.translationStale")}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={onDelete}
          className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
          title={t("chapters.card.deleteTooltip")}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </Button>
        <Button variant="secondary" size="sm" onClick={onEdit}>
          {t("common:edit")}
        </Button>
        <Button
          variant={hasProgress ? "secondary" : "primary"}
          size="sm"
          onClick={onTranslate}
        >
          {hasProgress ? t("chapters.card.continue") : t("chapters.card.translate")}
        </Button>
      </div>
    </div>
  );
}
