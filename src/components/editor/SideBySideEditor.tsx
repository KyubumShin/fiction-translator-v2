import { useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { ConnectedTextView } from "./ConnectedTextView";
import { SegmentHighlighter } from "./SegmentHighlighter";
import type { SegmentMapEntry } from "@/api/types";

interface SideBySideEditorProps {
  sourceText: string;
  translatedText: string;
  segmentMap: SegmentMapEntry[];
  onSegmentEdit?: (segmentId: number, newText: string) => void;
  onSegmentRetranslate?: (segmentId: number) => void;
}

export function SideBySideEditor({
  sourceText,
  translatedText,
  segmentMap,
  onSegmentEdit,
  onSegmentRetranslate,
}: SideBySideEditorProps) {
  const { t } = useTranslation("editor");
  const sourceRef = useRef<HTMLDivElement>(null);
  const translatedRef = useRef<HTMLDivElement>(null);

  // Synchronized scrolling
  useEffect(() => {
    const sourceEl = sourceRef.current;
    const translatedEl = translatedRef.current;
    if (!sourceEl || !translatedEl) return;

    let isSourceScrolling = false;
    let isTranslatedScrolling = false;

    const handleSourceScroll = () => {
      if (isTranslatedScrolling) return;
      isSourceScrolling = true;

      const scrollPercentage = sourceEl.scrollTop / (sourceEl.scrollHeight - sourceEl.clientHeight);
      translatedEl.scrollTop = scrollPercentage * (translatedEl.scrollHeight - translatedEl.clientHeight);

      setTimeout(() => { isSourceScrolling = false; }, 100);
    };

    const handleTranslatedScroll = () => {
      if (isSourceScrolling) return;
      isTranslatedScrolling = true;

      const scrollPercentage = translatedEl.scrollTop / (translatedEl.scrollHeight - translatedEl.clientHeight);
      sourceEl.scrollTop = scrollPercentage * (sourceEl.scrollHeight - sourceEl.clientHeight);

      setTimeout(() => { isTranslatedScrolling = false; }, 100);
    };

    sourceEl.addEventListener("scroll", handleSourceScroll);
    translatedEl.addEventListener("scroll", handleTranslatedScroll);

    return () => {
      sourceEl.removeEventListener("scroll", handleSourceScroll);
      translatedEl.removeEventListener("scroll", handleTranslatedScroll);
    };
  }, []);

  return (
    <div className="flex-1 grid grid-cols-2 divide-x divide-border overflow-hidden">
      <SegmentHighlighter segmentMap={segmentMap}>
        {({ activeSegmentId, onSegmentClick, onSegmentDoubleClick }) => (
          <>
            {/* Source Pane */}
            <div ref={sourceRef} className="overflow-auto p-8">
              <h2 className="text-xs font-semibold text-muted-foreground mb-6 uppercase tracking-wide">
                {t("sourceText")}
              </h2>
              <ConnectedTextView
                text={sourceText}
                segmentMap={segmentMap}
                side="source"
                activeSegmentId={activeSegmentId}
                onSegmentClick={onSegmentClick}
              />
            </div>

            {/* Translated Pane */}
            <div ref={translatedRef} className="overflow-auto p-8 bg-card/30">
              <h2 className="text-xs font-semibold text-muted-foreground mb-6 uppercase tracking-wide">
                {t("translation")}
              </h2>
              <ConnectedTextView
                text={translatedText}
                sourceText={sourceText}
                segmentMap={segmentMap}
                side="translated"
                activeSegmentId={activeSegmentId}
                onSegmentClick={onSegmentClick}
                onSegmentDoubleClick={onSegmentDoubleClick}
                onSegmentEdit={onSegmentEdit}
                onSegmentRetranslate={onSegmentRetranslate}
              />
            </div>
          </>
        )}
      </SegmentHighlighter>
    </div>
  );
}
