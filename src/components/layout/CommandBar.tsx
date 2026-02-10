import React from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "@/stores/app-store";
import { useProjects } from "@/hooks/useProject";

export function CommandBar() {
  const navigate = useNavigate();
  const { commandBarOpen, setCommandBarOpen } = useAppStore();
  const { data: projects } = useProjects();
  const [search, setSearch] = React.useState("");

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandBarOpen(!commandBarOpen);
      }
      if (e.key === "Escape") {
        setCommandBarOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commandBarOpen, setCommandBarOpen]);

  if (!commandBarOpen) return null;

  const commands = [
    { label: "Go to Projects", action: () => navigate("/") },
    { label: "Go to Settings", action: () => navigate("/settings") },
    ...(projects || []).map((p) => ({
      label: `Open: ${p.name}`,
      action: () => navigate(`/project/${p.id}`),
    })),
  ];

  const filtered = commands.filter((c) =>
    c.label.toLowerCase().includes(search.toLowerCase())
  );

  const handleSelect = (action: () => void) => {
    action();
    setCommandBarOpen(false);
    setSearch("");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-32">
      <div className="fixed inset-0 bg-black/50" onClick={() => setCommandBarOpen(false)} />
      <div className="relative z-50 w-full max-w-lg mx-4 bg-card rounded-xl border border-border shadow-2xl">
        <input
          type="text"
          placeholder="Type a command or search..."
          className="w-full px-4 py-3 bg-transparent border-b border-border focus:outline-none"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          autoFocus
        />
        <div className="max-h-96 overflow-auto">
          {filtered.map((cmd, i) => (
            <button
              key={i}
              className="w-full px-4 py-2 text-left hover:bg-accent transition-colors"
              onClick={() => handleSelect(cmd.action)}
            >
              {cmd.label}
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="px-4 py-8 text-center text-muted-foreground text-sm">
              No results found
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
