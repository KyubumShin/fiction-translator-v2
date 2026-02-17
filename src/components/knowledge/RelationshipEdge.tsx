import { type EdgeProps, BaseEdge, EdgeLabelRenderer, getBezierPath } from "@xyflow/react";

const TYPE_COLORS: Record<string, string> = {
  romantic: "#e11d48",
  family: "#f59e0b",
  friend: "#22c55e",
  rival: "#6366f1",
  mentor: "#0ea5e9",
  subordinate: "#8b5cf6",
  enemy: "#dc2626",
  ally: "#14b8a6",
  acquaintance: "#94a3b8",
};

export interface RelationshipEdgeData {
  relationship_type: string;
  intimacy_level: number;
  description: string | null;
  relationship_id: number;
  onEdit: (id: number) => void;
}

export function RelationshipEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const edgeData = data as RelationshipEdgeData | undefined;
  const type = edgeData?.relationship_type ?? "acquaintance";
  const intimacy = edgeData?.intimacy_level ?? 5;
  const color = TYPE_COLORS[type] ?? TYPE_COLORS.acquaintance;
  const strokeWidth = Math.max(1, Math.min(6, intimacy * 0.6));

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{ stroke: color, strokeWidth, opacity: 0.7 }}
      />
      <EdgeLabelRenderer>
        <button
          className="nodrag nopan px-2 py-0.5 rounded-full text-xs font-medium border shadow-sm bg-background hover:bg-accent transition-colors cursor-pointer"
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            borderColor: color,
            color: color,
            pointerEvents: "all",
          }}
          onClick={() => edgeData?.onEdit(edgeData.relationship_id)}
        >
          {type}
        </button>
      </EdgeLabelRenderer>
    </>
  );
}
