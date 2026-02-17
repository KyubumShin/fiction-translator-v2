import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type Connection,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button } from "@/components/ui/Button";
import { RelationshipEdge } from "./RelationshipEdge";
import { RelationshipEdgeDialog } from "./RelationshipEdgeDialog";
import {
  useRelationships,
  useCreateRelationship,
  useUpdateRelationship,
  useDeleteRelationship,
} from "@/hooks/useRelationships";
import type { Persona, CharacterRelationship } from "@/api/types";

const edgeTypes = { relationship: RelationshipEdge };

interface RelationshipGraphProps {
  projectId: number;
  personas: Persona[];
  onEditPersona: (persona: Persona) => void;
}

function buildNodes(personas: Persona[]): Node[] {
  const cols = Math.max(3, Math.ceil(Math.sqrt(personas.length)));
  return personas.map((p, i) => ({
    id: String(p.id),
    position: {
      x: (i % cols) * 220 + 50,
      y: Math.floor(i / cols) * 160 + 50,
    },
    data: { label: p.name, persona: p },
    type: "default",
    style: {
      padding: "12px 16px",
      borderRadius: "12px",
      fontSize: "14px",
      fontWeight: 600,
      minWidth: "120px",
      textAlign: "center" as const,
    },
  }));
}

function buildEdges(
  relationships: CharacterRelationship[],
  onEdit: (id: number) => void,
): Edge[] {
  return relationships.map((r) => ({
    id: `rel-${r.id}`,
    source: String(r.persona_id_1),
    target: String(r.persona_id_2),
    type: "relationship",
    data: {
      relationship_type: r.relationship_type,
      intimacy_level: r.intimacy_level,
      description: r.description,
      relationship_id: r.id,
      onEdit,
    },
  }));
}

export function RelationshipGraph({ projectId, personas, onEditPersona }: RelationshipGraphProps) {
  const { data: relationships = [] } = useRelationships(projectId);
  const createRelationship = useCreateRelationship();
  const updateRelationship = useUpdateRelationship();
  const deleteRelationship = useDeleteRelationship();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRelationship, setEditingRelationship] = useState<CharacterRelationship | null>(null);

  const handleEditRelationship = useCallback(
    (id: number) => {
      const rel = relationships.find((r) => r.id === id);
      if (rel) {
        setEditingRelationship(rel);
        setDialogOpen(true);
      }
    },
    [relationships],
  );

  // Only show personas that have at least one relationship
  const connectedPersonas = useMemo(() => {
    if (relationships.length === 0) return [];
    const connectedIds = new Set<number>();
    for (const r of relationships) {
      connectedIds.add(r.persona_id_1);
      connectedIds.add(r.persona_id_2);
    }
    return personas.filter((p) => connectedIds.has(p.id));
  }, [personas, relationships]);

  const initialNodes = useMemo(() => buildNodes(connectedPersonas), [connectedPersonas]);
  const initialEdges = useMemo(
    () => buildEdges(relationships, handleEditRelationship),
    [relationships, handleEditRelationship],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync when data changes
  useEffect(() => {
    setNodes(buildNodes(connectedPersonas));
  }, [connectedPersonas, setNodes]);

  useEffect(() => {
    setEdges(buildEdges(relationships, handleEditRelationship));
  }, [relationships, handleEditRelationship, setEdges]);

  const onConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target && connection.source !== connection.target) {
        setEditingRelationship(null);
        setDialogOpen(true);
        // Pre-fill will happen via the dialog's default state with these persona IDs
        // We store them temporarily
        const p1 = Number(connection.source);
        const p2 = Number(connection.target);
        setEditingRelationship({
          id: 0, // sentinel for "new"
          project_id: projectId,
          persona_id_1: Math.min(p1, p2),
          persona_id_2: Math.max(p1, p2),
          relationship_type: "acquaintance",
          description: null,
          intimacy_level: 5,
          auto_detected: false,
          detection_confidence: null,
          created_at: "",
          updated_at: "",
        } as CharacterRelationship);
      }
    },
    [projectId],
  );

  const onNodeDoubleClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const persona = personas.find((p) => p.id === Number(node.id));
      if (persona) onEditPersona(persona);
    },
    [personas, onEditPersona],
  );

  const handleSave = async (data: {
    persona_id_1: number;
    persona_id_2: number;
    relationship_type: string;
    description: string;
    intimacy_level: number;
  }) => {
    if (editingRelationship && editingRelationship.id > 0) {
      await updateRelationship.mutateAsync({
        id: editingRelationship.id,
        relationship_type: data.relationship_type,
        description: data.description,
        intimacy_level: data.intimacy_level,
      });
    } else {
      await createRelationship.mutateAsync({
        project_id: projectId,
        ...data,
      });
    }
    setDialogOpen(false);
    setEditingRelationship(null);
  };

  const handleDelete = async (id: number) => {
    await deleteRelationship.mutateAsync(id);
    setDialogOpen(false);
    setEditingRelationship(null);
  };

  const handleAddRelationship = () => {
    setEditingRelationship(null);
    setDialogOpen(true);
  };

  if (personas.length < 2) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p>Add at least two personas to create relationships.</p>
      </div>
    );
  }

  const hasRelationships = relationships.length > 0;

  return (
    <div className="flex-1 relative">
      <div className="absolute top-2 right-2 z-10">
        <Button variant="primary" size="sm" onClick={handleAddRelationship}>
          + Add Relationship
        </Button>
      </div>

      {!hasRelationships && (
        <div className="absolute inset-0 z-[5] flex items-center justify-center pointer-events-none">
          <div className="bg-background/80 backdrop-blur-sm rounded-xl border border-border p-6 text-center max-w-sm pointer-events-auto">
            <p className="text-sm font-medium mb-2">No relationships yet</p>
            <p className="text-xs text-muted-foreground mb-4">
              Drag from one character node to another, or use the button below to connect them.
            </p>
            <Button variant="primary" size="sm" onClick={handleAddRelationship}>
              + Add Relationship
            </Button>
          </div>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeDoubleClick={onNodeDoubleClick}
        edgeTypes={edgeTypes}
        fitView
        className="bg-background"
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>

      <RelationshipEdgeDialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          setEditingRelationship(null);
        }}
        relationship={editingRelationship}
        personas={personas}
        onSave={handleSave}
        onDelete={handleDelete}
      />
    </div>
  );
}
