import React from "react";
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from "./Dialog";
import { Button } from "./Button";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  message: string;
  confirmLabel?: string;
  loadingLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive";
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  loadingLabel = "Deleting...",
  cancelLabel = "Cancel",
  variant = "destructive",
}: ConfirmDialogProps) {
  const [loading, setLoading] = React.useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
      onClose();
    } catch {
      // Error handling is the caller's responsibility
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
      </DialogHeader>
      <DialogContent>
        <p className="text-sm text-muted-foreground">{message}</p>
      </DialogContent>
      <DialogFooter>
        <Button variant="secondary" size="sm" onClick={onClose} disabled={loading}>
          {cancelLabel}
        </Button>
        <Button
          variant={variant}
          size="sm"
          onClick={handleConfirm}
          disabled={loading}
        >
          {loading ? loadingLabel : confirmLabel}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
