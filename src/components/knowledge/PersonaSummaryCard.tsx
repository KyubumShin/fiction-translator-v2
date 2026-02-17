import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/Button";
import type { Persona } from "@/api/types";
import { cn } from "@/lib/cn";

interface PersonaSummaryCardProps {
  persona: Persona;
  onEdit: () => void;
  onDelete: () => void;
  onShowGraph?: () => void;
}

export function PersonaSummaryCard({ persona, onEdit, onDelete, onShowGraph }: PersonaSummaryCardProps) {
  const { t } = useTranslation("knowledge");

  const getFormalityLabel = (level: number) => {
    if (level <= 2) return t("personaPanel.veryCasual");
    if (level <= 4) return t("personaPanel.casual");
    if (level <= 6) return t("personaPanel.neutral");
    if (level <= 8) return t("personaPanel.formal");
    return t("personaPanel.veryFormal");
  };

  const getFormalityColor = (level: number) => {
    if (level <= 2) return "bg-purple-500";
    if (level <= 4) return "bg-blue-500";
    if (level <= 6) return "bg-green-500";
    if (level <= 8) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <div className="group p-5 border border-border rounded-xl bg-card hover:border-primary/50 hover:shadow-md transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold mb-1">{persona.name}</h3>
          {persona.aliases && persona.aliases.length > 0 && (
            <div className="flex gap-1.5 flex-wrap">
              {persona.aliases.map((alias, i) => (
                <span
                  key={i}
                  className="text-xs px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground"
                >
                  {alias}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {persona.auto_detected && (
            <span className="inline-flex items-center px-2 py-1 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-medium">
              {t("personaPanel.auto")}
            </span>
          )}
          {onShowGraph && (
            <button
              onClick={(e) => { e.stopPropagation(); onShowGraph(); }}
              className="p-1 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
              title={t("personaPanel.showRelationships")}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="6" cy="6" r="2.5" strokeWidth={1.5} />
                <circle cx="18" cy="6" r="2.5" strokeWidth={1.5} />
                <circle cx="12" cy="18" r="2.5" strokeWidth={1.5} />
                <path strokeLinecap="round" strokeWidth={1.5} d="M8 7.5l4 8.5M16 7.5l-4 8.5M8.5 6h7" />
              </svg>
            </button>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="p-1 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
            title={t("personaPanel.deletePersonaTooltip")}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {persona.personality && (
        <div className="mb-3">
          <p className="text-sm text-foreground/80 line-clamp-2">{persona.personality}</p>
        </div>
      )}

      {persona.speech_style && (
        <div className="mb-3 p-2 rounded-md bg-accent/30 border border-border/50">
          <div className="text-xs text-muted-foreground mb-1">{t("personaPanel.speechStyle")}</div>
          <div className="text-sm font-medium">{persona.speech_style}</div>
        </div>
      )}

      <div className="space-y-2 mb-4">
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-muted-foreground">{t("personaPanel.formalityLevel")}</span>
            <span className="text-xs font-medium">{getFormalityLabel(persona.formality_level)}</span>
          </div>
          <div className="flex gap-1">
            {Array.from({ length: 10 }).map((_, i) => (
              <div
                key={i}
                className={cn(
                  "h-2 flex-1 rounded-full",
                  i < persona.formality_level
                    ? getFormalityColor(persona.formality_level)
                    : "bg-secondary"
                )}
              />
            ))}
          </div>
        </div>

        {persona.age_group && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{t("personaPanel.ageGroup")}</span>
            <span className="font-medium">{persona.age_group}</span>
          </div>
        )}

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{t("personaPanel.appearances")}</span>
          <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-primary/10 text-primary text-xs font-semibold">
            {persona.appearance_count}
          </span>
        </div>
      </div>

      <Button variant="secondary" size="sm" className="w-full" onClick={onEdit}>
        {t("personaPanel.editDetails")}
      </Button>
    </div>
  );
}
