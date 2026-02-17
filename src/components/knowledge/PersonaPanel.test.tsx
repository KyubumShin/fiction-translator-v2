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

  it("has List and Graph text toggle buttons", () => {
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    expect(screen.getByRole("button", { name: "List" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Graph" })).toBeInTheDocument();
  });

  it("toggles to graph view when Graph button is clicked", async () => {
    const user = userEvent.setup();
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice"), makePersona(2, "Bob")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    await user.click(screen.getByRole("button", { name: "Graph" }));

    expect(screen.getByTestId("relationship-graph")).toBeInTheDocument();
  });

  it("toggles back to list view", async () => {
    const user = userEvent.setup();
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice"), makePersona(2, "Bob")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    // Toggle to graph
    await user.click(screen.getByRole("button", { name: "Graph" }));
    expect(screen.getByTestId("relationship-graph")).toBeInTheDocument();

    // Toggle back to list
    await user.click(screen.getByRole("button", { name: "List" }));
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("each persona card has a graph icon button", () => {
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice"), makePersona(2, "Bob")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    const graphButtons = screen.getAllByTitle("Show relationships");
    expect(graphButtons).toHaveLength(2);
  });

  it("card graph icon switches to graph view", async () => {
    const user = userEvent.setup();
    (usePersonas as any).mockReturnValue({
      data: [makePersona(1, "Alice")],
      isLoading: false,
    });

    render(<PersonaPanel projectId={1} />);

    await user.click(screen.getByTitle("Show relationships"));
    expect(screen.getByTestId("relationship-graph")).toBeInTheDocument();
  });
});
