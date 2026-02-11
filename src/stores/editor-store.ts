import { create } from "zustand";
import type { SegmentMapEntry } from "@/api/types";

interface EditorState {
  activeSegmentId: number | null;
  setActiveSegment: (id: number | null) => void;
  editingSegmentId: number | null;
  setEditingSegment: (id: number | null) => void;
  editText: string;
  setEditText: (text: string) => void;
  segmentMap: SegmentMapEntry[];
  setSegmentMap: (map: SegmentMapEntry[]) => void;
  showReasoning: boolean;
  toggleReasoning: () => void;
  useCoT: boolean;
  setUseCoT: (value: boolean) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  activeSegmentId: null,
  setActiveSegment: (id) => set({ activeSegmentId: id }),
  editingSegmentId: null,
  setEditingSegment: (id) => set({ editingSegmentId: id }),
  editText: "",
  setEditText: (text) => set({ editText: text }),
  segmentMap: [],
  setSegmentMap: (map) => set({ segmentMap: map }),
  showReasoning: false,
  toggleReasoning: () => set((s) => ({ showReasoning: !s.showReasoning })),
  useCoT: true,
  setUseCoT: (value) => set({ useCoT: value }),
}));
