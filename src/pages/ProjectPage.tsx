import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useProject, useUpdateProject, useDeleteProject } from "@/hooks/useProject";
import { useCreateChapter } from "@/hooks/useChapter";
import { Button } from "@/components/ui/Button";
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Label } from "@/components/ui/Label";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ChapterList } from "@/components/project/ChapterList";
import { GlossaryPanel } from "@/components/knowledge/GlossaryPanel";
import { PersonaPanel } from "@/components/knowledge/PersonaPanel";
import { languageName } from "@/lib/formatters";
import { cn } from "@/lib/cn";

type Tab = "chapters" | "glossary" | "personas";

export function ProjectPage() {
  const { t } = useTranslation("project");
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id ? parseInt(id) : null;

  const { data: project, isLoading } = useProject(projectId);
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();
  const createChapter = useCreateChapter();

  const [activeTab, setActiveTab] = useState<Tab>("chapters");
  const [isAddChapterOpen, setIsAddChapterOpen] = useState(false);
  const [isEditProjectOpen, setIsEditProjectOpen] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);

  const [chapterForm, setChapterForm] = useState({
    title: "",
    source_content: "",
  });

  const [projectForm, setProjectForm] = useState({
    name: "",
    description: "",
  });

  const handleAddChapter = async () => {
    if (!projectId || !chapterForm.title) return;

    await createChapter.mutateAsync({
      project_id: projectId,
      title: chapterForm.title,
      source_content: chapterForm.source_content || undefined,
    });

    setIsAddChapterOpen(false);
    setChapterForm({ title: "", source_content: "" });
  };

  const handleEditProject = () => {
    if (project) {
      setProjectForm({
        name: project.name,
        description: project.description || "",
      });
      setIsEditProjectOpen(true);
    }
  };

  const handleUpdateProject = async () => {
    if (!projectId) return;

    await updateProject.mutateAsync({
      id: projectId,
      name: projectForm.name,
      description: projectForm.description || null,
    });

    setIsEditProjectOpen(false);
  };

  const handleDeleteProject = () => {
    setIsDeleteConfirmOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!projectId) return;
    await deleteProject.mutateAsync(projectId);
    navigate("/");
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">{t("loading")}</div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-muted-foreground mb-4">{t("notFound")}</div>
        <Button variant="secondary" onClick={() => navigate("/")}>
          {t("common:backToProjects")}
        </Button>
      </div>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "chapters", label: t("tabs.chapters") },
    { id: "glossary", label: t("tabs.glossary") },
    { id: "personas", label: t("tabs.personas") },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border bg-background">
        <div className="container mx-auto px-8 py-6 max-w-7xl">
          <button
            className="text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
            onClick={() => navigate("/")}
          >
            {t("common:backToProjects")}
          </button>

          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h1 className="text-4xl font-bold mb-2">{project.name}</h1>
              <div className="flex items-center gap-3 text-muted-foreground mb-3">
                <span className="font-medium">{languageName(project.source_language)}</span>
                <span>→</span>
                <span className="font-medium">{languageName(project.target_language)}</span>
                {project.genre && (
                  <>
                    <span>•</span>
                    <span>{project.genre}</span>
                  </>
                )}
              </div>
              {project.description && (
                <p className="text-sm text-foreground/80 max-w-2xl">{project.description}</p>
              )}
            </div>

            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={handleEditProject}>
                {t("editProject")}
              </Button>
              <Button variant="destructive" size="sm" onClick={handleDeleteProject}>
                {t("common:delete")}
              </Button>
            </div>
          </div>

          <div className="flex gap-1 mt-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={cn(
                  "px-4 py-2 rounded-t-lg font-medium transition-colors",
                  activeTab === tab.id
                    ? "bg-card text-foreground border-t border-x border-border"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                )}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden bg-card border-t border-border">
        <div className="container mx-auto px-8 py-6 max-w-7xl h-full">
          {activeTab === "chapters" && (
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-semibold">{t("chapters.title")}</h2>
                <Button variant="primary" onClick={() => setIsAddChapterOpen(true)}>
                  {t("chapters.addChapter")}
                </Button>
              </div>
              <div className="flex-1 overflow-auto">
                <ChapterList projectId={projectId!} />
              </div>
            </div>
          )}

          {activeTab === "glossary" && (
            <div className="h-full border border-border rounded-xl overflow-hidden bg-background">
              <GlossaryPanel projectId={projectId!} />
            </div>
          )}

          {activeTab === "personas" && (
            <div className="h-full border border-border rounded-xl overflow-hidden bg-background">
              <PersonaPanel projectId={projectId!} sourceLanguage={project.source_language} />
            </div>
          )}
        </div>
      </div>

      <Dialog open={isAddChapterOpen} onClose={() => setIsAddChapterOpen(false)}>
        <DialogHeader>
          <DialogTitle>{t("chapters.addDialog.title")}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <div className="space-y-4">
            <div>
              <Label>{t("chapters.addDialog.chapterTitle")}</Label>
              <Input
                placeholder={t("chapters.addDialog.chapterTitlePlaceholder")}
                value={chapterForm.title}
                onChange={(e) => setChapterForm({ ...chapterForm, title: e.target.value })}
                autoFocus
              />
            </div>

            <div>
              <Label>{t("chapters.addDialog.sourceContent")}</Label>
              <Textarea
                className="min-h-[200px] font-mono"
                placeholder={t("chapters.addDialog.sourceContentPlaceholder")}
                value={chapterForm.source_content}
                onChange={(e) => setChapterForm({ ...chapterForm, source_content: e.target.value })}
              />
              <p className="text-xs text-muted-foreground mt-1">
                {t("chapters.addDialog.sourceContentHint")}
              </p>
            </div>
          </div>
        </DialogContent>
        <DialogFooter>
          <Button variant="secondary" size="sm" onClick={() => setIsAddChapterOpen(false)}>
            {t("common:cancel")}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleAddChapter}
            disabled={!chapterForm.title}
          >
            {t("chapters.addDialog.addButton")}
          </Button>
        </DialogFooter>
      </Dialog>

      <Dialog open={isEditProjectOpen} onClose={() => setIsEditProjectOpen(false)}>
        <DialogHeader>
          <DialogTitle>{t("editDialog.title")}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <div className="space-y-4">
            <div>
              <Label>{t("editDialog.projectName")}</Label>
              <Input
                placeholder={t("editDialog.projectNamePlaceholder")}
                value={projectForm.name}
                onChange={(e) => setProjectForm({ ...projectForm, name: e.target.value })}
              />
            </div>

            <div>
              <Label>{t("editDialog.description")}</Label>
              <Textarea
                placeholder={t("editDialog.descriptionPlaceholder")}
                value={projectForm.description}
                onChange={(e) => setProjectForm({ ...projectForm, description: e.target.value })}
              />
            </div>
          </div>
        </DialogContent>
        <DialogFooter>
          <Button variant="secondary" size="sm" onClick={() => setIsEditProjectOpen(false)}>
            {t("common:cancel")}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleUpdateProject}
            disabled={!projectForm.name}
          >
            {t("editDialog.saveChanges")}
          </Button>
        </DialogFooter>
      </Dialog>

      <ConfirmDialog
        open={isDeleteConfirmOpen}
        onClose={() => setIsDeleteConfirmOpen(false)}
        onConfirm={handleConfirmDelete}
        title={t("deleteDialog.title")}
        message={t("deleteDialog.message", { name: project?.name })}
        confirmLabel={t("deleteDialog.confirm")}
        loadingLabel={t("deleteDialog.loading")}
        variant="destructive"
      />
    </div>
  );
}
