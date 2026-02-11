import React from "react";
import { cn } from "@/lib/cn";

interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

export function Label({ className, children, ...props }: LabelProps) {
  return (
    <label
      className={cn("block text-sm font-medium mb-1.5", className)}
      {...props}
    >
      {children}
    </label>
  );
}
