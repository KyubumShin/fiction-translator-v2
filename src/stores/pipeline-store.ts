import { create } from "zustand";

interface PipelineState {
  isRunning: boolean;
  currentStage: string | null;
  progress: number;
  message: string;
  setProgress: (stage: string, progress: number, message: string) => void;
  start: () => void;
  finish: () => void;
  reset: () => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  isRunning: false,
  currentStage: null,
  progress: 0,
  message: "",
  setProgress: (stage, progress, message) => set({ currentStage: stage, progress, message }),
  start: () => set({ isRunning: true, progress: 0, currentStage: null, message: "" }),
  finish: () => set({ isRunning: false, progress: 1, currentStage: "complete" }),
  reset: () => set({ isRunning: false, progress: 0, currentStage: null, message: "" }),
}));
