import { Link, useLocation } from "react-router-dom";
import { useProjects } from "@/hooks/useProject";
import { cn } from "@/lib/cn";

export function Sidebar() {
  const location = useLocation();
  const { data: projects } = useProjects();

  const navItems = [
    { label: "Projects", path: "/", icon: "📁" },
    { label: "Settings", path: "/settings", icon: "⚙️" },
  ];

  return (
    <div className="w-64 border-r border-border bg-card flex flex-col">
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-bold">Fiction Translator</h1>
        <p className="text-xs text-muted-foreground">v2.0</p>
      </div>

      <nav className="flex-1 overflow-auto p-2">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-sm mb-1 transition-colors",
              location.pathname === item.path
                ? "bg-accent text-accent-foreground"
                : "hover:bg-accent/50"
            )}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}

        {projects && projects.length > 0 && (
          <>
            <div className="mt-4 mb-2 px-3 text-xs font-semibold text-muted-foreground uppercase">
              Recent Projects
            </div>
            {projects.slice(0, 5).map((project) => (
              <Link
                key={project.id}
                to={`/project/${project.id}`}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-lg text-sm mb-1 transition-colors truncate",
                  location.pathname === `/project/${project.id}`
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-accent/50"
                )}
              >
                <span>📖</span>
                <span className="truncate">{project.name}</span>
              </Link>
            ))}
          </>
        )}
      </nav>

      <div className="p-4 border-t border-border text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span>Sidecar Connected</span>
        </div>
      </div>
    </div>
  );
}
