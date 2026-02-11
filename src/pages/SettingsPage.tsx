import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "@/stores/app-store";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Label } from "@/components/ui/Label";
import { Toast } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { api } from "@/api/tauri-bridge";

export function SettingsPage() {
  const navigate = useNavigate();
  const { theme, setTheme } = useAppStore();
  const { toast, showToast, hideToast } = useToast();

  const [apiKeys, setApiKeys] = useState({
    gemini: "",
    claude: "",
    openai: "",
  });

  const [showKeys, setShowKeys] = useState({
    gemini: false,
    claude: false,
    openai: false,
  });

  const [keysExist, setKeysExist] = useState({
    gemini: false,
    claude: false,
    openai: false,
  });

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState({
    gemini: false,
    claude: false,
    openai: false,
  });

  const [defaultProvider, setDefaultProvider] = useState<"gemini" | "claude" | "openai">("gemini");
  const [defaultLanguages, setDefaultLanguages] = useState({
    source: "ko",
    target: "en",
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

  const maskKey = (key: string) => {
    if (!key) return "";
    if (key.length <= 8) return "••••••••";
    return `${key.slice(0, 4)}${"•".repeat(Math.min(key.length - 8, 20))}${key.slice(-4)}`;
  };

  useEffect(() => {
    const loadExistingKeys = async () => {
      try {
        const existingKeys = await api.getApiKeys();
        setKeysExist({
          gemini: existingKeys.gemini || false,
          claude: existingKeys.claude || false,
          openai: existingKeys.openai || false,
        });
      } catch (error) {
        console.error("Failed to load existing keys:", error);
      }
    };
    loadExistingKeys();
  }, []);

  const handleTestConnection = async (provider: string) => {
    const providerKey = provider.toLowerCase() as "gemini" | "claude" | "openai";
    setTesting({ ...testing, [providerKey]: true });

    try {
      const result = await api.testProvider(providerKey);
      if (result.success) {
        showToast(`${provider} connection successful!`, "success");
      } else {
        showToast(`${provider} connection failed: ${result.error || "Unknown error"}`, "error");
      }
    } catch (error) {
      showToast(`${provider} connection failed: ${error instanceof Error ? error.message : "Unknown error"}`, "error");
    } finally {
      setTesting({ ...testing, [providerKey]: false });
    }
  };

  const handleSaveKeys = async () => {
    setSaving(true);
    try {
      const keysToSave: Record<string, string> = {};
      if (apiKeys.gemini) keysToSave.gemini = apiKeys.gemini;
      if (apiKeys.claude) keysToSave.claude = apiKeys.claude;
      if (apiKeys.openai) keysToSave.openai = apiKeys.openai;

      await api.setApiKeys(keysToSave);

      // Refresh which keys exist
      const existingKeys = await api.getApiKeys();
      setKeysExist({
        gemini: existingKeys.gemini || false,
        claude: existingKeys.claude || false,
        openai: existingKeys.openai || false,
      });

      // Clear the input fields
      setApiKeys({ gemini: "", claude: "", openai: "" });

      showToast("API keys saved successfully!", "success");
    } catch (error) {
      showToast(`Failed to save API keys: ${error instanceof Error ? error.message : "Unknown error"}`, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="container mx-auto p-8 max-w-4xl">
      <div className="mb-8">
        <button
          className="text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
          onClick={() => navigate("/")}
        >
          ← Back to Projects
        </button>
        <h1 className="text-4xl font-bold mb-2">Settings</h1>
        <p className="text-muted-foreground">Configure your preferences and API keys</p>
      </div>

      <div className="space-y-6">
        {/* Appearance */}
        <div className="border border-border rounded-xl p-6 bg-card">
          <h2 className="text-lg font-semibold mb-4">Appearance</h2>
          <div className="space-y-4">
            <div>
              <Label className="mb-2">Theme</Label>
              <div className="flex gap-2">
                {(["light", "dark", "system"] as const).map((t) => (
                  <Button
                    key={t}
                    variant={theme === t ? "primary" : "secondary"}
                    size="sm"
                    onClick={() => setTheme(t)}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* API Keys */}
        <div className="border border-border rounded-xl p-6 bg-card">
          <h2 className="text-lg font-semibold mb-1">LLM API Keys</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Configure your API keys for translation providers
          </p>

          <div className="space-y-4">
            {/* Gemini */}
            <div>
              <Label className="mb-2">
                Google Gemini API Key
                {keysExist.gemini && <span className="ml-2 text-xs text-green-500">●</span>}
              </Label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    type={showKeys.gemini ? "text" : "password"}
                    placeholder={keysExist.gemini ? "Key configured (enter new to update)" : "Enter your Gemini API key"}
                    value={apiKeys.gemini}
                    onChange={(e) => setApiKeys({ ...apiKeys, gemini: e.target.value })}
                  />
                  {apiKeys.gemini && !showKeys.gemini && (
                    <div className="absolute inset-0 flex items-center px-3 pointer-events-none">
                      <span className="text-muted-foreground">{maskKey(apiKeys.gemini)}</span>
                    </div>
                  )}
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowKeys({ ...showKeys, gemini: !showKeys.gemini })}
                >
                  {showKeys.gemini ? "Hide" : "Show"}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleTestConnection("Gemini")}
                  disabled={!keysExist.gemini || testing.gemini}
                >
                  {testing.gemini ? "Testing..." : "Test"}
                </Button>
              </div>
            </div>

            {/* Claude */}
            <div>
              <Label className="mb-2">
                Anthropic Claude API Key
                {keysExist.claude && <span className="ml-2 text-xs text-green-500">●</span>}
              </Label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    type={showKeys.claude ? "text" : "password"}
                    placeholder={keysExist.claude ? "Key configured (enter new to update)" : "Enter your Claude API key"}
                    value={apiKeys.claude}
                    onChange={(e) => setApiKeys({ ...apiKeys, claude: e.target.value })}
                  />
                  {apiKeys.claude && !showKeys.claude && (
                    <div className="absolute inset-0 flex items-center px-3 pointer-events-none">
                      <span className="text-muted-foreground">{maskKey(apiKeys.claude)}</span>
                    </div>
                  )}
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowKeys({ ...showKeys, claude: !showKeys.claude })}
                >
                  {showKeys.claude ? "Hide" : "Show"}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleTestConnection("Claude")}
                  disabled={!keysExist.claude || testing.claude}
                >
                  {testing.claude ? "Testing..." : "Test"}
                </Button>
              </div>
            </div>

            {/* OpenAI */}
            <div>
              <Label className="mb-2">
                OpenAI API Key
                {keysExist.openai && <span className="ml-2 text-xs text-green-500">●</span>}
              </Label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    type={showKeys.openai ? "text" : "password"}
                    placeholder={keysExist.openai ? "Key configured (enter new to update)" : "Enter your OpenAI API key"}
                    value={apiKeys.openai}
                    onChange={(e) => setApiKeys({ ...apiKeys, openai: e.target.value })}
                  />
                  {apiKeys.openai && !showKeys.openai && (
                    <div className="absolute inset-0 flex items-center px-3 pointer-events-none">
                      <span className="text-muted-foreground">{maskKey(apiKeys.openai)}</span>
                    </div>
                  )}
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowKeys({ ...showKeys, openai: !showKeys.openai })}
                >
                  {showKeys.openai ? "Hide" : "Show"}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleTestConnection("OpenAI")}
                  disabled={!keysExist.openai || testing.openai}
                >
                  {testing.openai ? "Testing..." : "Test"}
                </Button>
              </div>
            </div>

            <div className="pt-2">
              <Button variant="primary" onClick={handleSaveKeys} disabled={saving}>
                {saving ? "Saving..." : "Save API Keys"}
              </Button>
            </div>
          </div>
        </div>

        {/* Default LLM Provider */}
        <div className="border border-border rounded-xl p-6 bg-card">
          <h2 className="text-lg font-semibold mb-4">Default LLM Provider</h2>
          <div className="flex gap-2">
            {(["gemini", "claude", "openai"] as const).map((provider) => (
              <Button
                key={provider}
                variant={defaultProvider === provider ? "primary" : "secondary"}
                size="sm"
                onClick={() => setDefaultProvider(provider)}
              >
                {provider === "gemini" ? "Gemini" : provider === "claude" ? "Claude" : "OpenAI"}
              </Button>
            ))}
          </div>
        </div>

        {/* Default Languages */}
        <div className="border border-border rounded-xl p-6 bg-card">
          <h2 className="text-lg font-semibold mb-4">Default Languages</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="mb-2">Default Source Language</Label>
              <Select
                value={defaultLanguages.source}
                onChange={(e) => setDefaultLanguages({ ...defaultLanguages, source: e.target.value })}
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <Label className="mb-2">Default Target Language</Label>
              <Select
                value={defaultLanguages.target}
                onChange={(e) => setDefaultLanguages({ ...defaultLanguages, target: e.target.value })}
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </div>

        {/* About */}
        <div className="border border-border rounded-xl p-6 bg-card">
          <h2 className="text-lg font-semibold mb-4">About</h2>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-medium">Version</span>
              <span className="text-muted-foreground">2.0.0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-medium">Platform</span>
              <span className="text-muted-foreground">Tauri v2 + React</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-medium">Backend</span>
              <span className="text-muted-foreground">Python + LangGraph</span>
            </div>
          </div>
        </div>
      </div>
      {toast && <Toast message={toast.message} type={toast.type} onClose={hideToast} />}
    </div>
  );
}
