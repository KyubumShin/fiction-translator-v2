import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
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
] as const;

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
  const { t } = useTranslation("knowledge");
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

  const isEditing = relationship !== null && relationship.id > 0;
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
        <DialogTitle>{isEditing ? t("relationshipDialog.editTitle") : t("relationshipDialog.addTitle")}</DialogTitle>
      </DialogHeader>
      <DialogContent>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>{t("relationshipDialog.character1")}</Label>
              <Select
                value={String(personaId1)}
                onChange={(e) => setPersonaId1(Number(e.target.value))}
                disabled={isEditing}
              >
                <option value="0">{t("relationshipDialog.select")}</option>
                {personas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label>{t("relationshipDialog.character2")}</Label>
              <Select
                value={String(personaId2)}
                onChange={(e) => setPersonaId2(Number(e.target.value))}
                disabled={isEditing}
              >
                <option value="0">{t("relationshipDialog.select")}</option>
                {personas.filter((p) => p.id !== personaId1).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {personaId1 > 0 && personaId2 > 0 && personaId1 === personaId2 && (
            <p className="text-sm text-destructive">{t("relationshipDialog.differentCharacters")}</p>
          )}

          <div>
            <Label>{t("relationshipDialog.relationshipType")}</Label>
            <Select value={type} onChange={(e) => setType(e.target.value)}>
              {RELATIONSHIP_TYPES.map((rt) => (
                <option key={rt} value={rt}>
                  {t(`relationshipDialog.${rt}` as any)}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <Label>{t("relationshipDialog.description")}</Label>
            <Textarea
              placeholder={t("relationshipDialog.descriptionPlaceholder")}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div>
            <Label>{t("relationshipDialog.intimacyLevel")}: {intimacy}</Label>
            <input
              type="range"
              min="1"
              max="10"
              value={intimacy}
              onChange={(e) => setIntimacy(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>{t("relationshipDialog.distant")}</span>
              <span>{t("relationshipDialog.veryClose")}</span>
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
            {t("common:delete")}
          </Button>
        )}
        <div className="flex-1" />
        <Button variant="secondary" size="sm" onClick={onClose}>
          {t("common:cancel")}
        </Button>
        <Button variant="primary" size="sm" onClick={handleSave} disabled={!canSave}>
          {isEditing ? t("common:update") : t("common:add")}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
