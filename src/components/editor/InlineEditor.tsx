import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

interface InlineEditorProps {
  segmentId: number;
  initialText: string;
  position: { top: number; left: number; width: number };
  onSave: (text: string) => void;
  onCancel: () => void;
}

export function InlineEditor({
  segmentId: _segmentId,
  initialText,
  position,
  onSave,
  onCancel,
}: InlineEditorProps) {
  const [text, setText] = useState(initialText);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Auto-focus and select all
    if (textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.select();
    }
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSave(text);
    } else if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
        onClick={onCancel}
      />

      {/* Editor */}
      <div
        className="absolute z-50 bg-card border border-border rounded-lg shadow-2xl overflow-hidden"
        style={{
          top: position.top - 8,
          left: position.left - 8,
          minWidth: Math.max(position.width + 16, 300),
          maxWidth: 600,
        }}
      >
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          className={cn(
            "w-full min-h-[100px] p-4 bg-card text-foreground",
            "resize-none outline-none",
            "font-inherit text-[15px] leading-relaxed"
          )}
          style={{ lineHeight: "1.8" }}
        />
        <div className="flex items-center justify-end gap-2 px-4 py-3 bg-muted/30 border-t border-border">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors rounded"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(text)}
            className="px-3 py-1.5 text-sm bg-primary text-primary-foreground hover:bg-primary/90 transition-colors rounded font-medium"
          >
            Save
          </button>
          <span className="text-xs text-muted-foreground ml-2">
            ⌘+Enter
          </span>
        </div>
      </div>
    </>
  );
}
