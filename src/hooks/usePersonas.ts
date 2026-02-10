import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/tauri-bridge";
import type { Persona } from "@/api/types";

export function usePersonas(projectId: number | null) {
  return useQuery({
    queryKey: ["personas", projectId],
    queryFn: () => api.listPersonas(projectId!) as Promise<Persona[]>,
    enabled: projectId !== null,
  });
}

export function useCreatePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { project_id: number; name: string; [key: string]: unknown }) =>
      api.createPersona(data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["personas", vars.project_id] });
    },
  });
}

export function useUpdatePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: number } & Record<string, unknown>) =>
      api.updatePersona(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });
}

export function useDeletePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api.deletePersona(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });
}
