import React from "react";
import { cn } from "@/lib/cn";

interface ToastProps {
  message: string;
  type?: "info" | "success" | "error";
  onClose: () => void;
}

export function Toast({ message, type = "info", onClose }: ToastProps) {
  React.useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div
      className={cn(
        "fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg text-sm font-medium z-50",
        {
          "bg-blue-500 text-white": type === "info",
          "bg-green-500 text-white": type === "success",
          "bg-red-500 text-white": type === "error",
        }
      )}
    >
      {message}
    </div>
  );
}
