import { useState, Fragment } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useChapter, useEditorData } from "@/hooks/useChapter";
import { useProgress } from "@/hooks/useProgress";
import { SideBySideEditor } from "@/components/editor/SideBySideEditor";
import { RetranslateDialog } from "@/components/editor/RetranslateDialog";
import { CoTReasoningPanel } from "@/components/editor/CoTReasoningPanel";
import { ProgressOverlay } from "@/components/translation/ProgressOverlay";
import { TranslateButton } from "@/components/translation/TranslateButton";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Toast } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { LANGUAGES, type LanguageCode } from "@/lib/constants";
import { api } from "@/api/tauri-bridge";
import { useEditorStore } from "@/stores/editor-store";
import { cn } from "@/lib/cn";

export function EditorPage() {
  const { chapterId } = useParams<{ chapterId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const id = chapterId ? parseInt(chapterId) : null;

  const [targetLanguage, setTargetLanguage] = useState<LanguageCode>("en");
  const [exporting, setExporting] = useState(false);
  const [retranslateSegmentId, setRetranslateSegmentId] = useState<number | null>(null);
  const { toast, showToast, hideToast } = useToast();

  const useCoT = useEditorStore((s) => s.useCoT);
  const setUseCoT = useEditorStore((s) => s.setUseCoT);

  const { data: chapter, isLoading: chapterLoading } = useChapter(id);
  const { data: editorData, isLoading: editorLoading } = useEditorData(id, targetLanguage);
  const { isRunning } = useProgress();

  const isLoading = chapterLoading || editorLoading;

  const handleSegmentEdit = async (segmentId: number, newText: string) => {
    try {
      await api.updateSegmentTranslation(segmentId, newText, targetLanguage);
      // Refetch editor data after edit
      queryClient.invalidateQueries({ queryKey: ["editor-data", id] });
    } catch (err) {
      console.error("Failed to update segment:", err);
    }
  };

  const handleExport = async () => {
    if (!id) return;
    setExporting(true);
    try {
      const result = await api.exportChapterTxt(id, targetLanguage);
      showToast(`Exported to: ${result.path}`, "success");
    } catch (err) {
      console.error("Export failed:", err);
      showToast("Export failed. Please try again.", "error");
    } finally {
      setExporting(false);
    }
  };

  const handleRetranslate = (segmentId: number) => {
    setRetranslateSegmentId(segmentId);
  };

  const handleRetranslateSubmit = async (userGuide: string) => {
    if (retranslateSegmentId === null) return;
    await api.retranslateSegments([retranslateSegmentId], targetLanguage, userGuide);
    queryClient.invalidateQueries({ queryKey: ["editor-data", id] });
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-muted-foreground">Loading chapter...</div>
      </div>
    );
  }

  if (!chapter) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-muted-foreground">Chapter not found</div>
      </div>
    );
  }

  const sourceText = editorData?.source_connected_text || chapter.source_content || "";
  const translatedText = editorData?.translated_connected_text || chapter.translated_content || "";
  const segmentMap = editorData?.segment_map || [];

  // Find segment data for the retranslate dialog
  const retranslateSegment = retranslateSegmentId !== null
    ? segmentMap.find((s) => s.segment_id === retranslateSegmentId)
    : null;
  const retranslateSourceText = retranslateSegment
    ? sourceText.slice(retranslateSegment.source_start, retranslateSegment.source_end)
    : "";
  const retranslateCurrentTranslation = retranslateSegment
    ? translatedText.slice(retranslateSegment.translated_start, retranslateSegment.translated_end)
    : "";

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Top Bar */}
      <div className="border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => navigate(`/project/${chapter.project_id}`)}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back
            </button>
            <div className="w-px h-5 bg-border" />
            <h1 className="text-lg font-semibold">{chapter.title}</h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Language Selector */}
            <Select
              className="h-9 w-auto"
              value={targetLanguage}
              onChange={(e) => setTargetLanguage(e.target.value as LanguageCode)}
            >
              {Object.entries(LANGUAGES).map(([code, name]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </Select>

            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>CoT</span>
              <button
                role="switch"
                aria-checked={useCoT}
                onClick={() => setUseCoT(!useCoT)}
                className={cn(
                  "relative inline-flex h-5 w-9 items-center rounded-full transition-colors",
                  useCoT ? "bg-primary" : "bg-muted-foreground/30"
                )}
              >
                <span
                  className={cn(
                    "inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform",
                    useCoT ? "translate-x-[18px]" : "translate-x-[2px]"
                  )}
                />
              </button>
            </label>

            <TranslateButton
              chapterId={id!}
              targetLanguage={targetLanguage}
              useCot={useCoT}
              disabled={!sourceText}
            />

            <Button
              variant="secondary"
              size="sm"
              onClick={handleExport}
              disabled={!translatedText || exporting}
            >
              {exporting ? "Exporting..." : "Export"}
            </Button>
          </div>
        </div>
      </div>

      {/* Main Editor */}
      {segmentMap.length > 0 ? (
        <>
          <SideBySideEditor
            sourceText={sourceText}
            translatedText={translatedText}
            segmentMap={segmentMap}
            onSegmentEdit={handleSegmentEdit}
            onSegmentRetranslate={handleRetranslate}
          />
          <CoTReasoningPanel chapterId={id!} />
        </>
      ) : (
        <div className="flex-1 flex overflow-hidden">
          {/* Source text preview */}
          <div className="flex-1 overflow-auto p-8">
            <h2 className="text-xs font-semibold text-muted-foreground mb-6 uppercase tracking-wide">
              Source Text
            </h2>
            {sourceText ? (
              <div className="prose prose-slate dark:prose-invert max-w-none">
                <div className="leading-relaxed text-[15px]" style={{ lineHeight: "1.8" }}>
                  {sourceText.split(/\n\s*\n/).map((para, i) => (
                    <p key={i} className="mb-4">
                      {para.split('\n').map((line, j, arr) => (
                        <Fragment key={j}>
                          {line}
                          {j < arr.length - 1 && <br />}
                        </Fragment>
                      ))}
                    </p>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center text-muted-foreground">
                <p>No source content. Add source text to this chapter first.</p>
              </div>
            )}
          </div>

          {/* Right side: placeholder */}
          <div className="flex-1 border-l border-border flex items-center justify-center bg-card/30">
            <div className="text-center max-w-xs">
              <p className="text-muted-foreground text-sm">
                Click "Translate" to generate the translation for this chapter.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Progress Overlay */}
      {isRunning && <ProgressOverlay />}

      {/* Re-translate Dialog */}
      <RetranslateDialog
        open={retranslateSegmentId !== null}
        onClose={() => setRetranslateSegmentId(null)}
        sourceText={retranslateSourceText}
        currentTranslation={retranslateCurrentTranslation}
        onRetranslate={handleRetranslateSubmit}
      />

      {/* Toast Notifications */}
      {toast && <Toast message={toast.message} type={toast.type} onClose={hideToast} />}
    </div>
  );
}
