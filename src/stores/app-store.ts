import { create } from "zustand";

interface AppState {
  sidecarConnected: boolean;
  setSidecarConnected: (connected: boolean) => void;
  theme: "light" | "dark" | "system";
  setTheme: (theme: "light" | "dark" | "system") => void;
  commandBarOpen: boolean;
  setCommandBarOpen: (open: boolean) => void;
  toggleCommandBar: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidecarConnected: false,
  setSidecarConnected: (connected) => set({ sidecarConnected: connected }),
  theme: "system",
  setTheme: (theme) => {
    set({ theme });
    // Apply to document
    const root = document.documentElement;
    if (theme === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
  },
  commandBarOpen: false,
  setCommandBarOpen: (open) => set({ commandBarOpen: open }),
  toggleCommandBar: () => set((s) => ({ commandBarOpen: !s.commandBarOpen })),
}));
