import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useChapters, useDeleteChapter } from "@/hooks/useChapter";
import { ChapterCard } from "./ChapterCard";
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import type { Chapter } from "@/api/types";

interface ChapterListProps {
  projectId: number;
  onSelectChapter?: (chapterId: number) => void;
}

export function ChapterList({ projectId, onSelectChapter }: ChapterListProps) {
  const { t } = useTranslation("project");
  const navigate = useNavigate();
  const { data: chapters, isLoading } = useChapters(projectId);
  const deleteChapter = useDeleteChapter();
  const [deletingChapter, setDeletingChapter] = useState<Chapter | null>(null);

  const handleTranslate = (chapterId: number) => {
    navigate(`/editor/${chapterId}`);
  };

  const handleEdit = (chapterId: number) => {
    if (onSelectChapter) {
      onSelectChapter(chapterId);
    } else {
      navigate(`/editor/${chapterId}`);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingChapter) return;
    try {
      await deleteChapter.mutateAsync(deletingChapter.id);
    } catch (err) {
      console.error("Failed to delete chapter:", err);
    } finally {
      setDeletingChapter(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-24 bg-card border border-border rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (!chapters || chapters.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p>{t("chapters.empty")}</p>
        <p className="text-sm mt-1">{t("chapters.emptyHint")}</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {chapters.map((chapter) => (
          <ChapterCard
            key={chapter.id}
            chapter={chapter}
            onTranslate={() => handleTranslate(chapter.id)}
            onEdit={() => handleEdit(chapter.id)}
            onDelete={() => setDeletingChapter(chapter)}
          />
        ))}
      </div>

      <Dialog open={deletingChapter !== null} onClose={() => setDeletingChapter(null)}>
        <DialogHeader>
          <DialogTitle>{t("chapters.deleteDialog.title")}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <p
            className="text-sm text-muted-foreground"
            dangerouslySetInnerHTML={{
              __html: t("chapters.deleteDialog.message", { title: deletingChapter?.title }),
            }}
          />
        </DialogContent>
        <DialogFooter>
          <Button variant="secondary" size="sm" onClick={() => setDeletingChapter(null)}>
            {t("common:cancel")}
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDeleteConfirm}
            disabled={deleteChapter.isPending}
          >
            {deleteChapter.isPending ? t("chapters.deleteDialog.loading") : t("chapters.deleteDialog.confirm")}
          </Button>
        </DialogFooter>
      </Dialog>
    </>
  );
}
