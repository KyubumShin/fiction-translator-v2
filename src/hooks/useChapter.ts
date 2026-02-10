import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/tauri-bridge";
import type { Chapter, EditorData } from "@/api/types";

export function useChapters(projectId: number | null) {
  return useQuery({
    queryKey: ["chapters", projectId],
    queryFn: () => api.listChapters(projectId!) as Promise<Chapter[]>,
    enabled: projectId !== null,
  });
}

export function useChapter(id: number | null) {
  return useQuery({
    queryKey: ["chapter", id],
    queryFn: () => api.getChapter(id!) as Promise<Chapter>,
    enabled: id !== null,
  });
}

export function useEditorData(chapterId: number | null, targetLanguage: string) {
  return useQuery({
    queryKey: ["editor-data", chapterId, targetLanguage],
    queryFn: () => api.getEditorData(chapterId!, targetLanguage) as Promise<EditorData>,
    enabled: chapterId !== null,
  });
}

export function useCreateChapter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { project_id: number; title: string; source_content?: string }) =>
      api.createChapter(data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["chapters", vars.project_id] });
    },
  });
}

export function useUpdateChapter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: number } & Record<string, unknown>) =>
      api.updateChapter(id, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["chapter", vars.id] });
      qc.invalidateQueries({ queryKey: ["chapters"] });
    },
  });
}

export function useDeleteChapter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteChapter(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chapters"] });
    },
  });
}
