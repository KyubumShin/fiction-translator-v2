import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/tauri-bridge";
import type { GlossaryEntry } from "@/api/types";

export function useGlossary(projectId: number | null) {
  return useQuery({
    queryKey: ["glossary", projectId],
    queryFn: () => api.listGlossary(projectId!) as Promise<GlossaryEntry[]>,
    enabled: projectId !== null,
  });
}

export function useCreateGlossaryEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { project_id: number; source_term: string; translated_term: string; term_type?: string; notes?: string }) =>
      api.createGlossaryEntry(data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["glossary", vars.project_id] });
    },
  });
}

export function useUpdateGlossaryEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: number } & Record<string, unknown>) =>
      api.updateGlossaryEntry(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["glossary"] });
    },
  });
}

export function useDeleteGlossaryEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api.deleteGlossaryEntry(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["glossary"] });
    },
  });
}
