import { cn } from "@/lib/cn";

interface PipelineStageIndicatorProps {
  label: string;
  status: "completed" | "active" | "pending";
  detail?: string;
}

export function PipelineStageIndicator({ label, status, detail }: PipelineStageIndicatorProps) {
  return (
    <div className="flex items-start gap-3">
      <div className={cn(
        "flex-shrink-0 mt-0.5",
        status === "completed" && "text-green-500",
        status === "active" && "text-primary",
        status === "pending" && "text-muted-foreground/40"
      )}>
        {status === "completed" && (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )}
        {status === "active" && (
          <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
        {status === "pending" && (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" strokeWidth="2" />
          </svg>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className={cn(
          "text-sm font-medium",
          status === "completed" && "text-foreground",
          status === "active" && "text-foreground",
          status === "pending" && "text-muted-foreground/60"
        )}>
          {label}
        </div>
        {detail && status === "active" && (
          <div className="text-xs text-muted-foreground mt-1">
            {detail}
          </div>
        )}
      </div>
    </div>
  );
}
