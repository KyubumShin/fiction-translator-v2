import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import { usePersonas, useCreatePersona, useUpdatePersona, useDeletePersona } from "@/hooks/usePersonas";
import { PersonaSummaryCard } from "./PersonaSummaryCard";
import type { Persona } from "@/api/types";
import { languageName } from "@/lib/formatters";

interface PersonaPanelProps {
  projectId: number;
  sourceLanguage?: string;
}

export function PersonaPanel({ projectId, sourceLanguage }: PersonaPanelProps) {
  const { data: personas, isLoading } = usePersonas(projectId);
  const createPersona = useCreatePersona();
  const updatePersona = useUpdatePersona();
  const deletePersona = useDeletePersona();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingPersona, setEditingPersona] = useState<Persona | null>(null);
  const [deletingPersonaId, setDeletingPersonaId] = useState<number | null>(null);

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
    return <div className="p-4 text-muted-foreground">Loading personas...</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h2 className="text-lg font-semibold">Character Personas</h2>
        <Button variant="primary" size="sm" onClick={handleAdd}>
          + Add Persona
        </Button>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {!personas || personas.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <p>No personas yet.</p>
            <p className="text-sm mt-1">Add character personas to improve translation consistency.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {personas.map((persona) => (
              <PersonaSummaryCard
                key={persona.id}
                persona={persona}
                onEdit={() => handleEdit(persona)}
                onDelete={() => handleDeleteRequest(persona.id)}
              />
            ))}
          </div>
        )}
      </div>

      <Dialog open={isDialogOpen} onClose={() => setIsDialogOpen(false)}>
        <DialogHeader>
          <DialogTitle>{editingPersona ? "Edit Persona" : "Add Persona"}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <div className="space-y-4">
            {sourceLanguage && (
              <div className="px-3 py-2 rounded-lg bg-primary/5 border border-primary/20 text-sm text-primary">
                Write persona details in <span className="font-semibold">{languageName(sourceLanguage)}</span> (source language) for best translation results.
              </div>
            )}
            <div>
              <label className="block text-sm font-medium mb-1.5">Name *</label>
              <Input
                placeholder="Character name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5">Aliases</label>
              <Input
                placeholder="Comma-separated aliases"
                value={formData.aliases}
                onChange={(e) => setFormData({ ...formData, aliases: e.target.value })}
              />
              <p className="text-xs text-muted-foreground mt-1">e.g., "Hero, The Chosen One"</p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5">Personality</label>
              <textarea
                className="flex min-h-[80px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                placeholder="Describe personality traits..."
                value={formData.personality}
                onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5">Speech Style</label>
              <Input
                placeholder="e.g., formal, casual, rough"
                value={formData.speech_style}
                onChange={(e) => setFormData({ ...formData, speech_style: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5">
                Formality Level: {formData.formality_level}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={formData.formality_level}
                onChange={(e) => setFormData({ ...formData, formality_level: parseInt(e.target.value) })}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>Very Casual</span>
                <span>Very Formal</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5">Age Group</label>
              <select
                className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={formData.age_group}
                onChange={(e) => setFormData({ ...formData, age_group: e.target.value })}
              >
                <option value="">Not specified</option>
                <option value="child">Child</option>
                <option value="teen">Teen</option>
                <option value="young_adult">Young Adult</option>
                <option value="adult">Adult</option>
                <option value="middle_aged">Middle Aged</option>
                <option value="elderly">Elderly</option>
              </select>
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
              Delete
            </Button>
          )}
          <div className="flex-1" />
          <Button variant="secondary" size="sm" onClick={() => setIsDialogOpen(false)}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={handleSubmit}>
            {editingPersona ? "Update" : "Add"}
          </Button>
        </DialogFooter>
      </Dialog>

      <Dialog open={deletingPersonaId !== null} onClose={() => setDeletingPersonaId(null)}>
        <DialogHeader>
          <DialogTitle>Delete Persona</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete this persona? This action cannot be undone.
          </p>
        </DialogContent>
        <DialogFooter>
          <Button variant="secondary" size="sm" onClick={() => setDeletingPersonaId(null)}>
            Cancel
          </Button>
          <Button variant="destructive" size="sm" onClick={handleDeleteConfirm}>
            Delete
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
