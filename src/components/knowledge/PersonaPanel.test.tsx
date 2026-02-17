import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Persona } from "@/api/types";

// Mock hooks
vi.mock("@/hooks/usePersonas", () => ({
  usePersonas: vi.fn(),
  useCreatePersona: () => ({ mutateAsync: vi.fn() }),
  useUpdatePersona: () => ({ mutateAsync: vi.fn() }),
  useDeletePersona: () => ({ mutateAsync: vi.fn() }),
}));

// Mock RelationshipGraph since it depends on ReactFlow
vi.mock("./RelationshipGraph", () => ({
  RelationshipGraph: () => <div data-testid="relationship-graph">Graph View</div>,
}));

import { PersonaPanel } from "./PersonaPanel";
import { usePersonas } from "@/hooks/usePersonas";

const makePersona = (id: number, name: string): Persona => ({
  id,
  project_id: 1,
  name,
  aliases: null,
  personality: null,
  speech_style: null,
  formality_level: 5,
  age_group: null,
  appearance_count: 1,
  auto_detected: false,
});

describe("PersonaPanel", () => {
  it("renders persona list by default", () => {
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice"), makePersona(2, "Bob")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    (usePersonas as any).mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<PersonaPanel projectId={1} />);

    expect(screen.getByText("Loading personas...")).toBeInTheDocument();
  });

  it("shows empty state when no personas", () => {
    (usePersonas as any).mockReturnValue({
      data: [],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    expect(screen.getByText("No personas yet.")).toBeInTheDocument();
  });

  it("has a graph toggle icon button", () => {
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    expect(screen.getByTitle("Show relationship graph")).toBeInTheDocument();
  });

  it("toggles to graph view when graph icon is clicked", async () => {
    const user = userEvent.setup();
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice"), makePersona(2, "Bob")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    // Click graph icon
    await user.click(screen.getByTitle("Show relationship graph"));

    // Should show graph view
    expect(screen.getByTestId("relationship-graph")).toBeInTheDocument();
    // Title should change to "Show list view"
    expect(screen.getByTitle("Show list view")).toBeInTheDocument();
  });

  it("toggles back to list view", async () => {
    const user = userEvent.setup();
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice"), makePersona(2, "Bob")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    // Toggle to graph
    await user.click(screen.getByTitle("Show relationship graph"));
    expect(screen.getByTestId("relationship-graph")).toBeInTheDocument();

    // Toggle back to list
    await user.click(screen.getByTitle("Show list view"));
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("graph icon button has no 'Graph' text label", () => {
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    // Should NOT have a button with text "Graph"
    expect(screen.queryByRole("button", { name: "Graph" })).not.toBeInTheDocument();
    // Should NOT have text "List" button either
    expect(screen.queryByRole("button", { name: "List" })).not.toBeInTheDocument();
  });
});
