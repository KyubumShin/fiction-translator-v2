import { useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Select } from "@/components/ui/Select";
import { Label } from "@/components/ui/Label";
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import { usePersonas, useCreatePersona, useUpdatePersona, useDeletePersona } from "@/hooks/usePersonas";
import { PersonaSummaryCard } from "./PersonaSummaryCard";
import type { Persona } from "@/api/types";
import { languageName } from "@/lib/formatters";
import { RelationshipGraph } from "./RelationshipGraph";

interface PersonaPanelProps {
  projectId: number;
  sourceLanguage?: string;
}

export function PersonaPanel({ projectId, sourceLanguage }: PersonaPanelProps) {
  const { t } = useTranslation("knowledge");
  const { data: personas, isLoading } = usePersonas(projectId);
  const createPersona = useCreatePersona();
  const updatePersona = useUpdatePersona();
  const deletePersona = useDeletePersona();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingPersona, setEditingPersona] = useState<Persona | null>(null);
  const [deletingPersonaId, setDeletingPersonaId] = useState<number | null>(null);
  const [view, setView] = useState<"list" | "graph">("list");

  const [formData, setFormData] = useState({
    name: "",
    aliases: "",
    personality: "",
    speech_style: "",
    formality_level: 5,
    age_group: "",
  });

  const handleEdit = (persona: Persona) => {
    setEditingPersona(persona);
    setFormData({
      name: persona.name,
      aliases: persona.aliases?.join(", ") || "",
      personality: persona.personality || "",
      speech_style: persona.speech_style || "",
      formality_level: persona.formality_level,
      age_group: persona.age_group || "",
    });
    setIsDialogOpen(true);
  };

  const handleAdd = () => {
    setEditingPersona(null);
    setFormData({
      name: "",
      aliases: "",
      personality: "",
      speech_style: "",
      formality_level: 5,
      age_group: "",
    });
    setIsDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.name) return;

    const data = {
      name: formData.name,
      aliases: formData.aliases ? formData.aliases.split(",").map(s => s.trim()).filter(Boolean) : [],
      personality: formData.personality || null,
      speech_style: formData.speech_style || null,
      formality_level: formData.formality_level,
      age_group: formData.age_group || null,
    };

    if (editingPersona) {
      await updatePersona.mutateAsync({ id: editingPersona.id, ...data });
    } else {
      await createPersona.mutateAsync({ project_id: projectId, ...data });
    }

    setIsDialogOpen(false);
  };

  const handleDeleteRequest = (id: number) => {
    setDeletingPersonaId(id);
  };

  const handleDeleteConfirm = async () => {
    if (deletingPersonaId === null) return;
    try {
      await deletePersona.mutateAsync(deletingPersonaId);
      setIsDialogOpen(false);
    } catch (err) {
      console.error("Failed to delete persona:", err);
    } finally {
      setDeletingPersonaId(null);
    }
  };

  if (isLoading) {
    return <div className="p-4 text-muted-foreground">{t("personaPanel.loading")}</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">{t("personaPanel.title")}</h2>
          <div className="flex items-center gap-1 rounded-lg bg-secondary p-0.5">
            <button
              onClick={() => setView("list")}
              className={cn(
                "px-3 py-1 rounded-md text-sm font-medium transition-colors",
                view === "list"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {t("personaPanel.list")}
            </button>
            <button
              onClick={() => setView("graph")}
              className={cn(
                "px-3 py-1 rounded-md text-sm font-medium transition-colors",
                view === "graph"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {t("personaPanel.graph")}
            </button>
          </div>
        </div>
        <Button variant="primary" size="sm" onClick={handleAdd}>
          {t("personaPanel.addPersona")}
        </Button>
      </div>

      {view === "list" ? (
        <div className="flex-1 overflow-auto p-4">
          {!personas || personas.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p>{t("personaPanel.empty")}</p>
              <p className="text-sm mt-1">{t("personaPanel.emptyHint")}</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {personas.map((persona) => (
                <PersonaSummaryCard
                  key={persona.id}
                  persona={persona}
                  onEdit={() => handleEdit(persona)}
                  onDelete={() => handleDeleteRequest(persona.id)}
                  onShowGraph={() => setView("graph")}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        <RelationshipGraph
          projectId={projectId}
          personas={personas ?? []}
          onEditPersona={handleEdit}
        />
      )}

      <Dialog open={isDialogOpen} onClose={() => setIsDialogOpen(false)}>
        <DialogHeader>
          <DialogTitle>{editingPersona ? t("personaPanel.editPersona") : t("personaPanel.addPersonaTitle")}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <div className="space-y-4">
            {sourceLanguage && (
              <div
                className="px-3 py-2 rounded-lg bg-primary/5 border border-primary/20 text-sm text-primary"
                dangerouslySetInnerHTML={{
                  __html: t("personaPanel.sourceLanguageHint", { language: languageName(sourceLanguage) }),
                }}
              />
            )}
            <div>
              <Label>{t("personaPanel.name")}</Label>
              <Input
                placeholder={t("personaPanel.namePlaceholder")}
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div>
              <Label>{t("personaPanel.aliases")}</Label>
              <Input
                placeholder={t("personaPanel.aliasesPlaceholder")}
                value={formData.aliases}
                onChange={(e) => setFormData({ ...formData, aliases: e.target.value })}
              />
              <p className="text-xs text-muted-foreground mt-1">{t("personaPanel.aliasesHint")}</p>
            </div>

            <div>
              <Label>{t("personaPanel.personality")}</Label>
              <Textarea
                placeholder={t("personaPanel.personalityPlaceholder")}
                value={formData.personality}
                onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
              />
            </div>

            <div>
              <Label>{t("personaPanel.speechStyle")}</Label>
              <Input
                placeholder={t("personaPanel.speechStylePlaceholder")}
                value={formData.speech_style}
                onChange={(e) => setFormData({ ...formData, speech_style: e.target.value })}
              />
            </div>

            <div>
              <Label>
                {t("personaPanel.formalityLevel")}: {formData.formality_level}
              </Label>
              <input
                type="range"
                min="1"
                max="10"
                value={formData.formality_level}
                onChange={(e) => setFormData({ ...formData, formality_level: parseInt(e.target.value) })}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>{t("personaPanel.veryCasual")}</span>
                <span>{t("personaPanel.veryFormal")}</span>
              </div>
            </div>

            <div>
              <Label>{t("personaPanel.ageGroup")}</Label>
              <Select
                value={formData.age_group}
                onChange={(e) => setFormData({ ...formData, age_group: e.target.value })}
              >
                <option value="">{t("personaPanel.notSpecified")}</option>
                <option value="child">{t("personaPanel.child")}</option>
                <option value="teen">{t("personaPanel.teen")}</option>
                <option value="young_adult">{t("personaPanel.youngAdult")}</option>
                <option value="adult">{t("personaPanel.adult")}</option>
                <option value="middle_aged">{t("personaPanel.middleAged")}</option>
                <option value="elderly">{t("personaPanel.elderly")}</option>
              </Select>
            </div>
          </div>
        </DialogContent>
        <DialogFooter>
          {editingPersona && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => handleDeleteRequest(editingPersona.id)}
            >
              {t("common:delete")}
            </Button>
          )}
          <div className="flex-1" />
          <Button variant="secondary" size="sm" onClick={() => setIsDialogOpen(false)}>
            {t("common:cancel")}
          </Button>
          <Button variant="primary" size="sm" onClick={handleSubmit}>
            {editingPersona ? t("common:update") : t("common:add")}
          </Button>
        </DialogFooter>
      </Dialog>

      <Dialog open={deletingPersonaId !== null} onClose={() => setDeletingPersonaId(null)}>
        <DialogHeader>
          <DialogTitle>{t("personaPanel.deletePersona")}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <p className="text-sm text-muted-foreground">
            {t("personaPanel.deleteConfirm")}
          </p>
        </DialogContent>
        <DialogFooter>
          <Button variant="secondary" size="sm" onClick={() => setDeletingPersonaId(null)}>
            {t("common:cancel")}
          </Button>
          <Button variant="destructive" size="sm" onClick={handleDeleteConfirm}>
            {t("common:delete")}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
