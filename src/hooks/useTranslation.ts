import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/tauri-bridge";

export function useTranslateChapter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ chapterId, targetLanguage }: { chapterId: number; targetLanguage: string }) =>
      api.translateChapter(chapterId, targetLanguage),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["chapter", vars.chapterId] });
      qc.invalidateQueries({ queryKey: ["editor-data", vars.chapterId] });
    },
  });
}
