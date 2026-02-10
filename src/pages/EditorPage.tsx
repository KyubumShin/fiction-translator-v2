import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useChapter, useEditorData } from "@/hooks/useChapter";
import { useProgress } from "@/hooks/useProgress";
import { SideBySideEditor } from "@/components/editor/SideBySideEditor";
import { CoTReasoningPanel } from "@/components/editor/CoTReasoningPanel";
import { ProgressOverlay } from "@/components/translation/ProgressOverlay";
import { TranslateButton } from "@/components/translation/TranslateButton";
import { Button } from "@/components/ui/Button";
import { LANGUAGES, type LanguageCode } from "@/lib/constants";

export function EditorPage() {
  const { chapterId } = useParams<{ chapterId: string }>();
  const navigate = useNavigate();
  const id = chapterId ? parseInt(chapterId) : null;

  const [targetLanguage, setTargetLanguage] = useState<LanguageCode>("en");

  const { data: chapter, isLoading: chapterLoading } = useChapter(id);
  const { data: editorData, isLoading: editorLoading } = useEditorData(id, targetLanguage);
  const { isRunning } = useProgress();

  const isLoading = chapterLoading || editorLoading;

  const handleSegmentEdit = (segmentId: number, newText: string) => {
    // TODO: Implement segment update API call
    console.log("Edit segment", segmentId, newText);
  };

  const handleExport = () => {
    // TODO: Implement export functionality
    console.log("Export chapter");
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
            <select
              value={targetLanguage}
              onChange={(e) => setTargetLanguage(e.target.value as LanguageCode)}
              className="h-9 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {Object.entries(LANGUAGES).map(([code, name]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </select>

            <TranslateButton
              chapterId={id!}
              targetLanguage={targetLanguage}
              disabled={!sourceText}
            />

            <Button
              variant="secondary"
              size="sm"
              onClick={handleExport}
              disabled={!translatedText}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Export
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
          />
          <CoTReasoningPanel chapterId={id!} />
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <p className="text-muted-foreground mb-4">
              No translation data yet. Click "Translate" to begin processing this chapter.
            </p>
            {!sourceText && (
              <p className="text-sm text-muted-foreground">
                Note: This chapter has no source content.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Progress Overlay */}
      {isRunning && <ProgressOverlay />}
    </div>
  );
}
