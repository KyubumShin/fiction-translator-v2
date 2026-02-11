import { useState, useCallback } from "react";

interface ToastState {
  message: string;
  type: "info" | "success" | "error";
}

export function useToast() {
  const [toast, setToast] = useState<ToastState | null>(null);

  const showToast = useCallback((message: string, type: "info" | "success" | "error" = "info") => {
    setToast({ message, type });
  }, []);

  const hideToast = useCallback(() => {
    setToast(null);
  }, []);

  return { toast, showToast, hideToast };
}
