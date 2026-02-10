import { useMemo, useState, useRef } from "react";
import { cn } from "@/lib/cn";
import { InlineEditor } from "./InlineEditor";
import type { SegmentMapEntry } from "@/api/types";

interface ConnectedTextViewProps {
  text: string;
  segmentMap: SegmentMapEntry[];
  side: "source" | "translated";
  activeSegmentId: number | null;
  onSegmentClick: (segmentId: number) => void;
  onSegmentDoubleClick?: (segmentId: number) => void;
  onSegmentEdit?: (segmentId: number, newText: string) => void;
}

export function ConnectedTextView({
  text,
  segmentMap,
  side,
  activeSegmentId,
  onSegmentClick,
  onSegmentDoubleClick,
  onSegmentEdit,
}: ConnectedTextViewProps) {
  const [editingSegmentId, setEditingSegmentId] = useState<number | null>(null);
  const [editorPosition, setEditorPosition] = useState<{ top: number; left: number; width: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Build segment spans
  const segments = useMemo(() => {
    const result: Array<{
      id: number;
      text: string;
      start: number;
      end: number;
      type: string;
      speaker: string | null;
    }> = [];

    segmentMap.forEach((entry) => {
      const start = side === "source" ? entry.source_start : entry.translated_start;
      const end = side === "source" ? entry.source_end : entry.translated_end;
      const segmentText = text.slice(start, end);

      result.push({
        id: entry.segment_id,
        text: segmentText,
        start,
        end,
        type: entry.type,
        speaker: entry.speaker,
      });
    });

    return result;
  }, [text, segmentMap, side]);

  const handleClick = (segmentId: number) => {
    onSegmentClick(segmentId);
  };

  const handleDoubleClick = (segmentId: number, event: React.MouseEvent<HTMLSpanElement>) => {
    if (side === "translated" && onSegmentDoubleClick && onSegmentEdit) {
      const target = event.currentTarget;
      const rect = target.getBoundingClientRect();
      const containerRect = containerRef.current?.getBoundingClientRect();

      if (containerRect) {
        setEditorPosition({
          top: rect.top - containerRect.top,
          left: rect.left - containerRect.left,
          width: rect.width,
        });
        setEditingSegmentId(segmentId);
        onSegmentDoubleClick(segmentId);
      }
    }
  };

  const handleSaveEdit = (newText: string) => {
    if (editingSegmentId !== null && onSegmentEdit) {
      onSegmentEdit(editingSegmentId, newText);
      setEditingSegmentId(null);
      setEditorPosition(null);
    }
  };

  const handleCancelEdit = () => {
    setEditingSegmentId(null);
    setEditorPosition(null);
  };

  const editingSegment = segments.find(s => s.id === editingSegmentId);

  return (
    <div ref={containerRef} className="relative prose prose-slate dark:prose-invert max-w-none">
      <div className="leading-relaxed text-[15px]" style={{ lineHeight: "1.8" }}>
        {segments.map((segment) => (
          <span
            key={segment.id}
            data-segment-id={segment.id}
            onClick={() => handleClick(segment.id)}
            onDoubleClick={(e) => handleDoubleClick(segment.id, e)}
            className={cn(
              "segment cursor-pointer transition-all duration-150 rounded-sm",
              activeSegmentId === segment.id && "segment-active",
              segment.type === "dialogue" && "segment-dialogue",
              side === "source" && "text-muted-foreground/90"
            )}
          >
            {segment.text}
          </span>
        ))}
      </div>

      {editingSegmentId !== null && editorPosition && editingSegment && (
        <InlineEditor
          segmentId={editingSegmentId}
          initialText={editingSegment.text}
          position={editorPosition}
          onSave={handleSaveEdit}
          onCancel={handleCancelEdit}
        />
      )}
    </div>
  );
}
