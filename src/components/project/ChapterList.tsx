import { useNavigate } from "react-router-dom";
import { useChapters } from "@/hooks/useChapter";
import { ChapterCard } from "./ChapterCard";

interface ChapterListProps {
  projectId: number;
  onSelectChapter?: (chapterId: number) => void;
}

export function ChapterList({ projectId, onSelectChapter }: ChapterListProps) {
  const navigate = useNavigate();
  const { data: chapters, isLoading } = useChapters(projectId);

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
    <div className="space-y-3">
      {chapters.map((chapter) => (
        <ChapterCard
          key={chapter.id}
          chapter={chapter}
          onTranslate={() => handleTranslate(chapter.id)}
          onEdit={() => handleEdit(chapter.id)}
        />
      ))}
    </div>
  );
}
