import { useState } from "react";
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";

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
        <DialogTitle>Re-translate Segment</DialogTitle>
      </DialogHeader>
      <DialogContent className="space-y-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Source Text
          </label>
          <div className="mt-1 p-3 bg-muted/50 rounded-lg text-sm leading-relaxed max-h-32 overflow-auto">
            {sourceText}
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Current Translation
          </label>
          <div className="mt-1 p-3 bg-muted/50 rounded-lg text-sm leading-relaxed max-h-32 overflow-auto">
            {currentTranslation}
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Translation Guide
          </label>
          <textarea
            value={userGuide}
            onChange={(e) => setUserGuide(e.target.value)}
            placeholder='Write instructions to guide the re-translation, e.g., "Use a more formal tone" or "The character is being sarcastic"'
            className="mt-1 w-full min-h-[100px] p-3 bg-background border border-input rounded-lg text-sm resize-none outline-none focus:ring-2 focus:ring-ring"
            disabled={isLoading}
          />
        </div>
      </DialogContent>
      <DialogFooter>
        <Button variant="secondary" size="sm" onClick={handleClose} disabled={isLoading}>
          Cancel
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={handleSubmit}
          disabled={isLoading || !userGuide.trim()}
        >
          {isLoading ? "Re-translating..." : "Re-translate"}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
