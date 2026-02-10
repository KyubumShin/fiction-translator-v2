import { useEditorStore } from "@/stores/editor-store";
import type { SegmentMapEntry } from "@/api/types";

interface SegmentHighlighterProps {
  segmentMap: SegmentMapEntry[];
  children: (props: {
    activeSegmentId: number | null;
    onSegmentClick: (id: number) => void;
    onSegmentDoubleClick: (id: number) => void;
  }) => React.ReactNode;
}

export function SegmentHighlighter({ segmentMap: _segmentMap, children }: SegmentHighlighterProps) {
  const { activeSegmentId, setActiveSegment } = useEditorStore();

  const handleSegmentClick = (id: number) => {
    setActiveSegment(id);
  };

  const handleSegmentDoubleClick = (_id: number) => {
    // Double-click is handled by ConnectedTextView for editing
    // This is just a pass-through for consistency
  };

  return (
    <>
      {children({
        activeSegmentId,
        onSegmentClick: handleSegmentClick,
        onSegmentDoubleClick: handleSegmentDoubleClick,
      })}
    </>
  );
}
