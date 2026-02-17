import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useGlossary, useCreateGlossaryEntry, useUpdateGlossaryEntry, useDeleteGlossaryEntry } from "@/hooks/useGlossary";
import type { GlossaryEntry } from "@/api/types";
import { cn } from "@/lib/cn";

interface GlossaryPanelProps {
  projectId: number;
}

const TERM_TYPE_KEYS = ["all", "general", "name", "place", "item", "skill", "organization"] as const;

export function GlossaryPanel({ projectId }: GlossaryPanelProps) {
  const { t } = useTranslation("knowledge");
  const { data: entries, isLoading } = useGlossary(projectId);
  const createEntry = useCreateGlossaryEntry();
  const updateEntry = useUpdateGlossaryEntry();
  const deleteEntry = useDeleteGlossaryEntry();

  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [filterType, setFilterType] = useState<string>("all");

  const [formData, setFormData] = useState({
    source_term: "",
    translated_term: "",
    term_type: "general",
    notes: "",
  });

  const getTermTypeLabel = (type: string) => {
    const key = type as keyof typeof t;
    return t(`glossaryPanel.${key}` as any) || type.charAt(0).toUpperCase() + type.slice(1);
  };

  const handleSubmit = async () => {
    if (!formData.source_term || !formData.translated_term) return;

    if (editingId) {
      await updateEntry.mutateAsync({
        id: editingId,
        ...formData,
      });
      setEditingId(null);
    } else {
      await createEntry.mutateAsync({
        project_id: projectId,
        ...formData,
      });
    }

    setFormData({ source_term: "", translated_term: "", term_type: "general", notes: "" });
    setIsAdding(false);
  };

  const handleEdit = (entry: GlossaryEntry) => {
    setFormData({
      source_term: entry.source_term,
      translated_term: entry.translated_term,
      term_type: entry.term_type || "general",
      notes: entry.notes || "",
    });
    setEditingId(entry.id);
    setIsAdding(true);
  };

  const handleCancel = () => {
    setFormData({ source_term: "", translated_term: "", term_type: "general", notes: "" });
    setEditingId(null);
    setIsAdding(false);
  };

  const filteredEntries = entries?.filter(
    (e) => filterType === "all" || e.term_type === filterType
  ) || [];

  if (isLoading) {
    return <div className="p-4 text-muted-foreground">{t("glossaryPanel.loading")}</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h2 className="text-lg font-semibold">{t("glossaryPanel.title")}</h2>
        {!isAdding && (
          <Button variant="primary" size="sm" onClick={() => setIsAdding(true)}>
            {t("glossaryPanel.addTerm")}
          </Button>
        )}
      </div>

      {isAdding && (
        <div className="p-4 border-b border-border bg-accent/5 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Input
              placeholder={t("glossaryPanel.sourceTerm")}
              value={formData.source_term}
              onChange={(e) => setFormData({ ...formData, source_term: e.target.value })}
            />
            <Input
              placeholder={t("glossaryPanel.translatedTerm")}
              value={formData.translated_term}
              onChange={(e) => setFormData({ ...formData, translated_term: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Select
              value={formData.term_type}
              onChange={(e) => setFormData({ ...formData, term_type: e.target.value })}
            >
              {TERM_TYPE_KEYS.filter(t => t !== "all").map((type) => (
                <option key={type} value={type}>
                  {getTermTypeLabel(type)}
                </option>
              ))}
            </Select>
            <Input
              placeholder={t("glossaryPanel.notesOptional")}
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
            />
          </div>
          <div className="flex gap-2">
            <Button variant="primary" size="sm" onClick={handleSubmit}>
              {editingId ? t("common:update") : t("common:add")}
            </Button>
            <Button variant="secondary" size="sm" onClick={handleCancel}>
              {t("common:cancel")}
            </Button>
          </div>
        </div>
      )}

      <div className="p-4 border-b border-border">
        <div className="flex gap-2 flex-wrap">
          {TERM_TYPE_KEYS.map((type) => (
            <button
              key={type}
              className={cn(
                "px-3 py-1 rounded-md text-sm font-medium transition-colors",
                filterType === type
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              )}
              onClick={() => setFilterType(type)}
            >
              {getTermTypeLabel(type)}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {filteredEntries.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            {filterType === "all" ? t("glossaryPanel.empty") : t("glossaryPanel.emptyFiltered", { type: getTermTypeLabel(filterType) })}
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-accent/30 sticky top-0">
              <tr>
                <th className="text-left p-3 text-sm font-semibold">{t("glossaryPanel.source")}</th>
                <th className="text-left p-3 text-sm font-semibold">{t("glossaryPanel.translation")}</th>
                <th className="text-left p-3 text-sm font-semibold">{t("glossaryPanel.type")}</th>
                <th className="text-left p-3 text-sm font-semibold">{t("glossaryPanel.notes")}</th>
                <th className="text-right p-3 text-sm font-semibold">{t("glossaryPanel.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredEntries.map((entry) => (
                <tr key={entry.id} className="hover:bg-accent/5 transition-colors">
                  <td className="p-3 font-medium">{entry.source_term}</td>
                  <td className="p-3">{entry.translated_term}</td>
                  <td className="p-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-primary/10 text-primary text-xs font-medium">
                      {entry.term_type}
                    </span>
                    {entry.auto_detected && (
                      <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-medium">
                        {t("glossaryPanel.auto")}
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-sm text-muted-foreground">{entry.notes || "-"}</td>
                  <td className="p-3 text-right">
                    <div className="flex gap-1 justify-end">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(entry)}>
                        {t("common:edit")}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteEntry.mutate(entry.id)}
                      >
                        {t("common:delete")}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
