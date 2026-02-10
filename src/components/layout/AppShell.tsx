import React from "react";
import { Sidebar } from "./Sidebar";
import { CommandBar } from "./CommandBar";
import { useTheme } from "@/hooks/useTheme";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  useTheme();

  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
      <CommandBar />
    </div>
  );
}
