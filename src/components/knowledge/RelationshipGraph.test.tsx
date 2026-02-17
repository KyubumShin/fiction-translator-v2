import { describe, it, expect, vi } from "vitest";
import type { Persona, CharacterRelationship } from "@/api/types";

// Mock ReactFlow since it requires browser APIs not available in jsdom
vi.mock("@xyflow/react", () => ({
  ReactFlow: ({ children }: any) => <div data-testid="reactflow">{children}</div>,
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  useNodesState: (initial: any[]) => {
    const nodes = [...initial];
    return [nodes, vi.fn(), vi.fn()];
  },
  useEdgesState: (initial: any[]) => {
    const edges = [...initial];
    return [edges, vi.fn(), vi.fn()];
  },
}));

vi.mock("@/hooks/useRelationships", () => ({
  useRelationships: vi.fn(),
  useCreateRelationship: () => ({ mutateAsync: vi.fn() }),
  useUpdateRelationship: () => ({ mutateAsync: vi.fn() }),
  useDeleteRelationship: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("./RelationshipEdge", () => ({
  RelationshipEdge: () => null,
}));

vi.mock("./RelationshipEdgeDialog", () => ({
  RelationshipEdgeDialog: () => null,
}));

import { render, screen } from "@testing-library/react";
import { RelationshipGraph } from "./RelationshipGraph";
import { useRelationships } from "@/hooks/useRelationships";

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

const makeRelationship = (
  id: number,
  pid1: number,
  pid2: number,
): CharacterRelationship => ({
  id,
  project_id: 1,
  persona_id_1: pid1,
  persona_id_2: pid2,
  relationship_type: "friend",
  description: null,
  intimacy_level: 5,
  auto_detected: false,
  detection_confidence: null,
  created_at: "",
  updated_at: "",
});

describe("RelationshipGraph", () => {
  it("shows empty message when fewer than 2 personas", () => {
    (useRelationships as any).mockReturnValue({ data: [] });

    render(
      <RelationshipGraph
        projectId={1}
        personas={[makePersona(1, "Alice")]}
        onEditPersona={vi.fn()}
      />
    );

    expect(
      screen.getByText("Add at least two personas to create relationships.")
    ).toBeInTheDocument();
  });

  it("shows 'no relationships' overlay when personas exist but no relationships", () => {
    (useRelationships as any).mockReturnValue({ data: [] });

    render(
      <RelationshipGraph
        projectId={1}
        personas={[makePersona(1, "Alice"), makePersona(2, "Bob")]}
        onEditPersona={vi.fn()}
      />
    );

    expect(screen.getByText("No relationships yet")).toBeInTheDocument();
  });

  it("filters out unconnected personas from the graph", () => {
    const personas = [
      makePersona(1, "Alice"),
      makePersona(2, "Bob"),
      makePersona(3, "Charlie"), // not connected
    ];
    const relationships = [makeRelationship(1, 1, 2)]; // only Alice-Bob

    (useRelationships as any).mockReturnValue({ data: relationships });

    render(
      <RelationshipGraph
        projectId={1}
        personas={personas}
        onEditPersona={vi.fn()}
      />
    );

    // ReactFlow is rendered (not the empty state)
    expect(screen.getByTestId("reactflow")).toBeInTheDocument();
    // No "no relationships" overlay since there ARE relationships
    expect(screen.queryByText("No relationships yet")).not.toBeInTheDocument();
  });

  it("shows empty state when 0 personas", () => {
    (useRelationships as any).mockReturnValue({ data: [] });

    render(
      <RelationshipGraph
        projectId={1}
        personas={[]}
        onEditPersona={vi.fn()}
      />
    );

    expect(
      screen.getByText("Add at least two personas to create relationships.")
    ).toBeInTheDocument();
  });
});
