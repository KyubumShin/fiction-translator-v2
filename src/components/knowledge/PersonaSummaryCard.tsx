import { Button } from "@/components/ui/Button";
import type { Persona } from "@/api/types";
import { cn } from "@/lib/cn";

interface PersonaSummaryCardProps {
  persona: Persona;
  onEdit: () => void;
}

export function PersonaSummaryCard({ persona, onEdit }: PersonaSummaryCardProps) {
  const getFormalityLabel = (level: number) => {
    if (level <= 2) return "Very Casual";
    if (level <= 4) return "Casual";
    if (level <= 6) return "Neutral";
    if (level <= 8) return "Formal";
    return "Very Formal";
  };

  const getFormalityColor = (level: number) => {
    if (level <= 2) return "bg-purple-500";
    if (level <= 4) return "bg-blue-500";
    if (level <= 6) return "bg-green-500";
    if (level <= 8) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <div className="p-5 border border-border rounded-xl bg-card hover:border-primary/50 hover:shadow-md transition-all">
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
        {persona.auto_detected && (
          <span className="inline-flex items-center px-2 py-1 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-medium">
            Auto
          </span>
        )}
      </div>

      {persona.personality && (
        <div className="mb-3">
          <p className="text-sm text-foreground/80 line-clamp-2">{persona.personality}</p>
        </div>
      )}

      {persona.speech_style && (
        <div className="mb-3 p-2 rounded-md bg-accent/30 border border-border/50">
          <div className="text-xs text-muted-foreground mb-1">Speech Style</div>
          <div className="text-sm font-medium">{persona.speech_style}</div>
        </div>
      )}

      <div className="space-y-2 mb-4">
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-muted-foreground">Formality Level</span>
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
            <span className="text-muted-foreground">Age Group</span>
            <span className="font-medium">{persona.age_group}</span>
          </div>
        )}

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Appearances</span>
          <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-primary/10 text-primary text-xs font-semibold">
            {persona.appearance_count}
          </span>
        </div>
      </div>

      <Button variant="secondary" size="sm" className="w-full" onClick={onEdit}>
        Edit Details
      </Button>
    </div>
  );
}
