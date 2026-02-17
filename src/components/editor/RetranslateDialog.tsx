import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";

interface RetranslateDialogProps {
  open: boolean;
  onClose: () => void;
  sourceText: string;
  currentTranslation: string;
  onRetranslate: (userGuide: string) => Promise<void>;
}

export function RetranslateDialog({
  open,
  onClose,
  sourceText,
  currentTranslation,
  onRetranslate,
}: RetranslateDialogProps) {
  const { t } = useTranslation("editor");
  const [userGuide, setUserGuide] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    setIsLoading(true);
    try {
      await onRetranslate(userGuide);
      setUserGuide("");
      onClose();
    } catch (err) {
      console.error("Re-translation failed:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setUserGuide("");
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose}>
      <DialogHeader>
        <DialogTitle>{t("retranslateDialog.title")}</DialogTitle>
      </DialogHeader>
      <DialogContent className="space-y-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t("retranslateDialog.sourceText")}
          </label>
          <div className="mt-1 p-3 bg-muted/50 rounded-lg text-sm leading-relaxed max-h-32 overflow-auto whitespace-pre-wrap">
            {sourceText}
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t("retranslateDialog.currentTranslation")}
          </label>
          <div className="mt-1 p-3 bg-muted/50 rounded-lg text-sm leading-relaxed max-h-32 overflow-auto whitespace-pre-wrap">
            {currentTranslation}
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t("retranslateDialog.translationGuide")}
          </label>
          <Textarea
            className="mt-1 min-h-[100px] resize-none"
            value={userGuide}
            onChange={(e) => setUserGuide(e.target.value)}
            placeholder={t("retranslateDialog.guidePlaceholder")}
            disabled={isLoading}
          />
        </div>
      </DialogContent>
      <DialogFooter>
        <Button variant="secondary" size="sm" onClick={handleClose} disabled={isLoading}>
          {t("common:cancel")}
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={handleSubmit}
          disabled={isLoading || !userGuide.trim()}
        >
          {isLoading ? t("retranslateDialog.retranslating") : t("retranslateDialog.retranslate")}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
