import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/tauri-bridge";

export function useRelationships(projectId: number | null) {
  return useQuery({
    queryKey: ["relationships", projectId],
    queryFn: () => api.listRelationships(projectId!),
    enabled: projectId !== null,
  });
}

export function useCreateRelationship() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      project_id: number;
      persona_id_1: number;
      persona_id_2: number;
      relationship_type?: string;
      description?: string;
      intimacy_level?: number;
    }) => api.createRelationship(data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["relationships", vars.project_id] });
    },
  });
}

export function useUpdateRelationship() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: number } & Record<string, unknown>) =>
      api.updateRelationship(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["relationships"] });
    },
  });
}

export function useDeleteRelationship() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteRelationship(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["relationships"] });
    },
  });
}
