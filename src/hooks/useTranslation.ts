import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/tauri-bridge";

export function useTranslateChapter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ chapterId, targetLanguage, useCot = true }: {
      chapterId: number;
      targetLanguage: string;
      useCot?: boolean;
    }) =>
      api.translateChapter(chapterId, targetLanguage, useCot),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["chapter", vars.chapterId] });
      qc.invalidateQueries({ queryKey: ["editor-data", vars.chapterId] });
    },
  });
}
