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
  onSegmentRetranslate?: (segmentId: number) => void;
}

export function ConnectedTextView({
  text,
  segmentMap,
  side,
  activeSegmentId,
  onSegmentClick,
  onSegmentDoubleClick,
  onSegmentEdit,
  onSegmentRetranslate,
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

  const [toolbarPosition, setToolbarPosition] = useState<{ top: number; left: number } | null>(null);

  const handleClick = (segmentId: number) => {
    onSegmentClick(segmentId);

    // Calculate toolbar position for translated side
    if (side === "translated" && onSegmentRetranslate) {
      requestAnimationFrame(() => {
        const span = containerRef.current?.querySelector(`[data-segment-id="${segmentId}"]`);
        const containerRect = containerRef.current?.getBoundingClientRect();
        if (span && containerRect) {
          const rect = span.getBoundingClientRect();
          setToolbarPosition({
            top: rect.bottom - containerRect.top + 4,
            left: rect.left - containerRect.left,
          });
        }
      });
    } else {
      setToolbarPosition(null);
    }
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

      {side === "translated" && activeSegmentId !== null && toolbarPosition && !editingSegmentId && onSegmentRetranslate && (
        <div
          className="absolute z-30 flex items-center gap-1 bg-card border border-border rounded-lg shadow-lg px-1.5 py-1"
          style={{ top: toolbarPosition.top, left: toolbarPosition.left }}
        >
          <button
            onClick={() => {
              const seg = segments.find(s => s.id === activeSegmentId);
              if (seg) {
                const fakeEvent = { currentTarget: containerRef.current?.querySelector(`[data-segment-id="${activeSegmentId}"]`) } as unknown as React.MouseEvent<HTMLSpanElement>;
                handleDoubleClick(activeSegmentId, fakeEvent);
              }
            }}
            className="flex items-center gap-1.5 px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-accent rounded transition-colors"
            title="Edit translation"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Edit
          </button>
          <div className="w-px h-4 bg-border" />
          <button
            onClick={() => onSegmentRetranslate(activeSegmentId)}
            className="flex items-center gap-1.5 px-2 py-1 text-xs text-muted-foreground hover:text-primary hover:bg-primary/10 rounded transition-colors"
            title="Re-translate with guidance"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Re-translate
          </button>
        </div>
      )}
    </div>
  );
}
