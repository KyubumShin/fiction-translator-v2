import { formatRelativeTime, languageName } from "@/lib/formatters";
import type { Project } from "@/api/types";
import { cn } from "@/lib/cn";

interface ProjectCardProps {
  project: Project;
  onClick: () => void;
}

export function ProjectCard({ project, onClick }: ProjectCardProps) {
  return (
    <button
      className={cn(
        "group relative p-6 border border-border rounded-xl bg-card text-left",
        "hover:border-primary/50 hover:shadow-lg transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      )}
      onClick={onClick}
    >
      <div className="flex flex-col h-full">
        <h3 className="text-xl font-semibold mb-2 group-hover:text-primary transition-colors">
          {project.name}
        </h3>

        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
          <span className="font-medium">{languageName(project.source_language)}</span>
          <span>→</span>
          <span className="font-medium">{languageName(project.target_language)}</span>
        </div>

        {project.description && (
          <p className="text-sm text-foreground/80 mb-4 line-clamp-2 flex-1">
            {project.description}
          </p>
        )}

        <div className="flex items-center justify-between mt-auto pt-4 border-t border-border/50">
          {project.chapter_count !== undefined && (
            <div className="flex items-center gap-1.5">
              <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-primary/10 text-primary text-xs font-medium">
                {project.chapter_count} {project.chapter_count === 1 ? 'chapter' : 'chapters'}
              </span>
            </div>
          )}

          <div className="text-xs text-muted-foreground">
            {formatRelativeTime(project.updated_at)}
          </div>
        </div>
      </div>
    </button>
  );
}
