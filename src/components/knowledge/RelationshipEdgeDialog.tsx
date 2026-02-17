import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import type { CharacterRelationship, Persona } from "@/api/types";

const RELATIONSHIP_TYPES = [
  "acquaintance",
  "friend",
  "rival",
  "family",
  "romantic",
  "mentor",
  "subordinate",
  "enemy",
  "ally",
];

interface RelationshipEdgeDialogProps {
  open: boolean;
  onClose: () => void;
  relationship: CharacterRelationship | null;
  personas: Persona[];
  onSave: (data: {
    persona_id_1: number;
    persona_id_2: number;
    relationship_type: string;
    description: string;
    intimacy_level: number;
  }) => void;
  onDelete?: (id: number) => void;
}

export function RelationshipEdgeDialog({
  open,
  onClose,
  relationship,
  personas,
  onSave,
  onDelete,
}: RelationshipEdgeDialogProps) {
  const [personaId1, setPersonaId1] = useState<number>(0);
  const [personaId2, setPersonaId2] = useState<number>(0);
  const [type, setType] = useState("acquaintance");
  const [description, setDescription] = useState("");
  const [intimacy, setIntimacy] = useState(5);

  useEffect(() => {
    if (relationship) {
      setPersonaId1(relationship.persona_id_1);
      setPersonaId2(relationship.persona_id_2);
      setType(relationship.relationship_type);
      setDescription(relationship.description ?? "");
      setIntimacy(relationship.intimacy_level);
    } else {
      setPersonaId1(personas[0]?.id ?? 0);
      setPersonaId2(personas[1]?.id ?? 0);
      setType("acquaintance");
      setDescription("");
      setIntimacy(5);
    }
  }, [relationship, personas]);

  const isEditing = relationship !== null;
  const canSave = personaId1 > 0 && personaId2 > 0 && personaId1 !== personaId2;

  const handleSave = () => {
    if (!canSave) return;
    onSave({
      persona_id_1: personaId1,
      persona_id_2: personaId2,
      relationship_type: type,
      description,
      intimacy_level: intimacy,
    });
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogHeader>
        <DialogTitle>{isEditing ? "Edit Relationship" : "Add Relationship"}</DialogTitle>
      </DialogHeader>
      <DialogContent>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Character 1</Label>
              <Select
                value={String(personaId1)}
                onChange={(e) => setPersonaId1(Number(e.target.value))}
                disabled={isEditing}
              >
                <option value="0">Select...</option>
                {personas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label>Character 2</Label>
              <Select
                value={String(personaId2)}
                onChange={(e) => setPersonaId2(Number(e.target.value))}
                disabled={isEditing}
              >
                <option value="0">Select...</option>
                {personas.filter((p) => p.id !== personaId1).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {personaId1 > 0 && personaId2 > 0 && personaId1 === personaId2 && (
            <p className="text-sm text-destructive">Characters must be different.</p>
          )}

          <div>
            <Label>Relationship Type</Label>
            <Select value={type} onChange={(e) => setType(e.target.value)}>
              {RELATIONSHIP_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <Label>Description</Label>
            <Textarea
              placeholder="Describe the relationship..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div>
            <Label>Intimacy Level: {intimacy}</Label>
            <input
              type="range"
              min="1"
              max="10"
              value={intimacy}
              onChange={(e) => setIntimacy(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>Distant</span>
              <span>Very Close</span>
            </div>
          </div>
        </div>
      </DialogContent>
      <DialogFooter>
        {isEditing && onDelete && (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onDelete(relationship!.id)}
          >
            Delete
          </Button>
        )}
        <div className="flex-1" />
        <Button variant="secondary" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" size="sm" onClick={handleSave} disabled={!canSave}>
          {isEditing ? "Update" : "Add"}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
