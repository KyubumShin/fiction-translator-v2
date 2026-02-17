import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useProjects, useCreateProject, useDeleteProject } from "@/hooks/useProject";
import { Button } from "@/components/ui/Button";
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Select } from "@/components/ui/Select";
import { Label } from "@/components/ui/Label";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ProjectCard } from "@/components/project/ProjectCard";
import type { Project } from "@/api/types";

export function ProjectsPage() {
  const { t } = useTranslation("projects");
  const navigate = useNavigate();
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [deletingProject, setDeletingProject] = useState<Project | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    source_language: "ko",
    target_language: "en",
    genre: "",
  });

  const languages = [
    { code: "en", name: "English" },
    { code: "ko", name: "Korean" },
    { code: "ja", name: "Japanese" },
    { code: "zh", name: "Chinese" },
    { code: "es", name: "Spanish" },
    { code: "fr", name: "French" },
    { code: "de", name: "German" },
    { code: "pt", name: "Portuguese" },
    { code: "ru", name: "Russian" },
    { code: "vi", name: "Vietnamese" },
    { code: "th", name: "Thai" },
    { code: "id", name: "Indonesian" },
  ];

  const handleCreate = async () => {
    if (!formData.name) return;

    const result = await createProject.mutateAsync({
      name: formData.name,
      description: formData.description || undefined,
      source_language: formData.source_language,
      target_language: formData.target_language,
      genre: formData.genre || undefined,
    });

    setIsDialogOpen(false);
    setFormData({ name: "", description: "", source_language: "ko", target_language: "en", genre: "" });
    navigate(`/project/${(result as any).id}`);
  };

  const handleConfirmDelete = async () => {
    if (!deletingProject) return;
    await deleteProject.mutateAsync(deletingProject.id);
    setDeletingProject(null);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">{t("loading")}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Button variant="primary" onClick={() => setIsDialogOpen(true)}>
          {t("newProject")}
        </Button>
      </div>

      {!projects || projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center mb-6">
            <svg
              className="w-12 h-12 text-primary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold mb-2">{t("empty.title")}</h2>
          <p className="text-muted-foreground mb-6 max-w-md">
            {t("empty.description")}
          </p>
          <Button variant="primary" onClick={() => setIsDialogOpen(true)}>
            {t("empty.action")}
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onClick={() => navigate(`/project/${project.id}`)}
              onDelete={() => setDeletingProject(project)}
            />
          ))}
        </div>
      )}

      <Dialog open={isDialogOpen} onClose={() => setIsDialogOpen(false)}>
        <DialogHeader>
          <DialogTitle>{t("createDialog.title")}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <div className="space-y-4">
            <div>
              <Label>{t("createDialog.projectName")}</Label>
              <Input
                placeholder={t("createDialog.projectNamePlaceholder")}
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                autoFocus
              />
            </div>

            <div>
              <Label>{t("createDialog.description")}</Label>
              <Textarea
                placeholder={t("createDialog.descriptionPlaceholder")}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>{t("createDialog.sourceLanguage")}</Label>
                <Select
                  value={formData.source_language}
                  onChange={(e) => setFormData({ ...formData, source_language: e.target.value })}
                >
                  {languages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <Label>{t("createDialog.targetLanguage")}</Label>
                <Select
                  value={formData.target_language}
                  onChange={(e) => setFormData({ ...formData, target_language: e.target.value })}
                >
                  {languages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name}
                    </option>
                  ))}
                </Select>
              </div>
            </div>

            <div>
              <Label>{t("createDialog.genre")}</Label>
              <Input
                placeholder={t("createDialog.genrePlaceholder")}
                value={formData.genre}
                onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
              />
            </div>
          </div>
        </DialogContent>
        <DialogFooter>
          <Button variant="secondary" size="sm" onClick={() => setIsDialogOpen(false)}>
            {t("common:cancel")}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleCreate}
            disabled={!formData.name}
          >
            {t("createDialog.createButton")}
          </Button>
        </DialogFooter>
      </Dialog>

      <ConfirmDialog
        open={deletingProject !== null}
        onClose={() => setDeletingProject(null)}
        onConfirm={handleConfirmDelete}
        title={t("deleteDialog.title")}
        message={t("deleteDialog.message", { name: deletingProject?.name })}
        confirmLabel={t("deleteDialog.confirm")}
        loadingLabel={t("deleteDialog.loading")}
        variant="destructive"
      />
    </div>
  );
}
