import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/Button";
import { useTranslateChapter } from "@/hooks/useTranslation";
import { usePipelineStore } from "@/stores/pipeline-store";

interface TranslateButtonProps {
  chapterId: number;
  targetLanguage: string;
  useCot?: boolean;
  disabled?: boolean;
}

export function TranslateButton({ chapterId, targetLanguage, useCot = true, disabled }: TranslateButtonProps) {
  const { t } = useTranslation("pipeline");
  const { mutate: translate, isPending } = useTranslateChapter();
  const isRunning = usePipelineStore((s) => s.isRunning);

  const handleClick = () => {
    translate({ chapterId, targetLanguage, useCot });
  };

  return (
    <Button
      variant="primary"
      size="sm"
      onClick={handleClick}
      disabled={disabled || isPending || isRunning}
    >
      {(isPending || isRunning) && (
        <svg className="w-4 h-4 mr-2 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {(isPending || isRunning) ? t("translateButton.translating") : t("translateButton.translate")}
    </Button>
  );
}
