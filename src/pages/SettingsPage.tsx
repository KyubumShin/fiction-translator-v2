import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "@/stores/app-store";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export function SettingsPage() {
  const navigate = useNavigate();
  const { theme, setTheme } = useAppStore();

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

  const handleTestConnection = async (provider: string) => {
    // TODO: Implement API test connection
    alert(`Testing ${provider} connection... (Not implemented yet)`);
  };

  const handleSaveKeys = () => {
    // TODO: Implement API key storage
    alert("API keys saved! (Not fully implemented yet)");
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
              <label className="block text-sm font-medium mb-2">Theme</label>
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
              <label className="block text-sm font-medium mb-2">Google Gemini API Key</label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    type={showKeys.gemini ? "text" : "password"}
                    placeholder="Enter your Gemini API key"
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
                  disabled={!apiKeys.gemini}
                >
                  Test
                </Button>
              </div>
            </div>

            {/* Claude */}
            <div>
              <label className="block text-sm font-medium mb-2">Anthropic Claude API Key</label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    type={showKeys.claude ? "text" : "password"}
                    placeholder="Enter your Claude API key"
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
                  disabled={!apiKeys.claude}
                >
                  Test
                </Button>
              </div>
            </div>

            {/* OpenAI */}
            <div>
              <label className="block text-sm font-medium mb-2">OpenAI API Key</label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    type={showKeys.openai ? "text" : "password"}
                    placeholder="Enter your OpenAI API key"
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
                  disabled={!apiKeys.openai}
                >
                  Test
                </Button>
              </div>
            </div>

            <div className="pt-2">
              <Button variant="primary" onClick={handleSaveKeys}>
                Save API Keys
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
              <label className="block text-sm font-medium mb-2">Default Source Language</label>
              <select
                className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={defaultLanguages.source}
                onChange={(e) => setDefaultLanguages({ ...defaultLanguages, source: e.target.value })}
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Default Target Language</label>
              <select
                className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={defaultLanguages.target}
                onChange={(e) => setDefaultLanguages({ ...defaultLanguages, target: e.target.value })}
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
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
    </div>
  );
}
