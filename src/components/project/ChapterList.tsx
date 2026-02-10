import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
        <p>No chapters yet.</p>
        <p className="text-sm mt-1">Add your first chapter to get started.</p>
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
          <DialogTitle>Delete Chapter</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete <strong>{deletingChapter?.title}</strong>?
            This will permanently remove the chapter and all its segments and translations.
          </p>
        </DialogContent>
        <DialogFooter>
          <Button variant="secondary" size="sm" onClick={() => setDeletingChapter(null)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDeleteConfirm}
            disabled={deleteChapter.isPending}
          >
            {deleteChapter.isPending ? "Deleting..." : "Delete"}
          </Button>
        </DialogFooter>
      </Dialog>
    </>
  );
}
