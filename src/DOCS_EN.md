# Fiction Translator v2.0 — React Frontend Documentation

## Overview

The React frontend runs inside Tauri's webview and provides a modern SaaS-style interface for managing translation projects and editing translations. Built with React 18, Vite, TypeScript, and Tailwind CSS, it communicates with the Python sidecar backend via JSON-RPC over Tauri IPC.

## Why This Architecture?

### Why React + Vite (not Next.js or other)?

- **Tauri webview runs a local SPA** — No server-side rendering needed or possible
- **Vite provides instant HMR** — Sub-second refresh during development
- **React ecosystem maturity** — Excellent component libraries (Radix UI primitives)
- **TypeScript-first** — Type safety from API boundary to UI components

### Why Zustand (not Redux or Context)?

- **Minimal boilerplate** — A store is just a function with `create()`
- **No providers needed** — Import and use anywhere, no wrapping required
- **Perfect for local UI state** — Selected segment, theme, pipeline status
- **React Query handles server state** — Zustand only manages UI state (separation of concerns)

### Why React Query (not raw fetch or SWR)?

- **Automatic caching and revalidation** — Smart cache invalidation on mutations
- **Mutations with optimistic updates** — Instant UI feedback, rollback on error
- **Query invalidation on mutations** — After creating a project, list refreshes automatically
- **Loading/error states built in** — `isLoading`, `isError`, `isPending` out of the box
- **Background refetching** — Stale data updates in the background

### Why CSS Variables + Tailwind (not CSS-in-JS)?

- **CSS variables enable theme switching** — Dark/light mode with zero JS overhead
- **Tailwind provides utility-first styling** — Fast iteration, consistent spacing
- **No runtime CSS-in-JS overhead** — All styles are static, compiled at build time
- **Linear/Vercel aesthetic** — Achieved through careful variable design in `globals.css`

### Why Connected Text (not segment-by-segment)?

- **Users are translating fiction** — They need to see continuous prose, not isolated segments
- **Segment-level editing is hidden** — Click to highlight, double-click to edit inline
- **Matches professional translator workflow** — Context matters; you translate in paragraphs, not fragments
- **Smooth reading experience** — The editor feels like reading a book, not a spreadsheet

---

## Directory Structure

```
src/
├── main.tsx                    # React entry point (ReactDOM.render)
├── App.tsx                     # Router + React Query provider
├── api/                        # Backend communication
│   ├── tauri-bridge.ts         # Tauri invoke wrapper + event listeners
│   └── types.ts                # TypeScript interfaces matching Python schema
├── stores/                     # Zustand state (UI-only)
│   ├── app-store.ts            # Theme, sidecar status, command bar
│   ├── editor-store.ts         # Active/editing segment, segment map
│   └── pipeline-store.ts       # Translation progress (isRunning, stage, progress)
├── hooks/                      # React Query hooks (server state)
│   ├── useProject.ts           # Project CRUD queries/mutations
│   ├── useChapter.ts           # Chapter CRUD + editor data
│   ├── useGlossary.ts          # Glossary CRUD
│   ├── usePersonas.ts          # Persona CRUD
│   ├── useTranslation.ts       # Translation trigger mutation
│   ├── useProgress.ts          # Pipeline event listener
│   ├── useToast.ts             # Toast notification state management
│   └── useTheme.ts             # Theme management (dark/light/system)
├── pages/                      # Route pages
│   ├── ProjectsPage.tsx        # Dashboard (project list + create)
│   ├── ProjectPage.tsx         # Project detail (chapters/glossary/personas tabs)
│   ├── EditorPage.tsx          # Side-by-side editor with progress overlay
│   └── SettingsPage.tsx        # API keys, theme, defaults
├── components/
│   ├── layout/                 # App shell, sidebar, command bar
│   │   ├── AppShell.tsx        # Container with sidebar + main
│   │   ├── Sidebar.tsx         # Left navigation + recent projects
│   │   └── CommandBar.tsx      # Cmd+K command palette
│   ├── editor/                 # Connected text view, inline editor
│   │   ├── SideBySideEditor.tsx         # Layout with scroll sync
│   │   ├── ConnectedTextView.tsx        # Segment-to-span renderer
│   │   ├── InlineEditor.tsx             # Floating textarea editor
│   │   ├── RetranslateDialog.tsx        # Re-translate segment with guidance
│   │   ├── CoTReasoningPanel.tsx        # Chain-of-thought display
│   │   └── SegmentHighlighter.tsx       # HOC for segment interaction
│   ├── project/                # Project cards, chapter list
│   │   ├── ProjectCard.tsx              # Project grid item
│   │   └── ChapterList.tsx              # Chapter table with stats
│   ├── translation/            # Translate button, progress overlay
│   │   ├── TranslateButton.tsx          # Trigger translation
│   │   ├── ProgressOverlay.tsx          # Modal with pipeline stages
│   │   └── PipelineStageIndicator.tsx   # Individual stage status
│   ├── knowledge/              # Glossary panel, persona panel
│   │   ├── GlossaryPanel.tsx            # Term management UI
│   │   ├── PersonaPanel.tsx             # Character management UI
│   │   └── PersonaSummaryCard.tsx       # Persona card for grid display
│   └── ui/                     # Shared primitives (Button, Input, Textarea, Select, Label, Dialog, Toast, ConfirmDialog)
│       ├── Button.tsx
│       ├── Input.tsx
│       ├── Textarea.tsx
│       ├── Select.tsx
│       ├── Label.tsx
│       ├── Dialog.tsx
│       ├── ConfirmDialog.tsx
│       ├── Toast.tsx
│       └── ...
├── lib/                        # Utilities
│   ├── cn.ts                   # Tailwind merge (clsx + twMerge)
│   ├── constants.ts            # Languages, providers, pipeline stages
│   └── formatters.ts           # Date, time, text formatting
└── styles/
    └── globals.css             # CSS variables, theme, base styles
```

---

## API Layer (`api/`)

### `tauri-bridge.ts`

**Purpose:** Bridge between React and Python sidecar via Tauri IPC.

#### `rpc<T>(method: string, params?: Record<string, unknown>): Promise<T>`

Generic JSON-RPC call wrapper.

```typescript
const result = await rpc<Project>("project.get", { project_id: 1 });
```

#### `onPipelineProgress(callback: (progress: PipelineProgress) => void): Promise<UnlistenFn>`

Listen for pipeline progress events from the sidecar.

```typescript
const unlisten = await onPipelineProgress((p) => {
  console.log(`Stage: ${p.stage}, Progress: ${p.progress}, Message: ${p.message}`);
});
// Later: unlisten()
```

#### `onSidecarStatus(callback: (status: { connected: boolean; error?: string }) => void): Promise<UnlistenFn>`

Listen for sidecar connection status changes.

#### `api` object

Convenience methods wrapping `rpc()`:

**Health:**
- `healthCheck()` → `{ status: string, version: string }`

**Config:**
- `setApiKeys(keys: Record<string, string>)` — Store LLM API keys
- `getApiKeys()` → `Record<string, boolean>` — Check which keys exist (not values)
- `testProvider(provider: string)` → `{ success: boolean, error?: string }`

**Projects:**
- `listProjects()` → `Project[]`
- `createProject(data)` → `Project`
- `getProject(projectId: number)` → `Project`
- `updateProject(projectId: number, data)` → `Project`
- `deleteProject(projectId: number)` → `void`

**Chapters:**
- `listChapters(projectId: number)` → `Chapter[]`
- `createChapter(data)` → `Chapter`
- `getChapter(chapterId: number)` → `Chapter`
- `updateChapter(chapterId: number, data)` → `Chapter`
- `deleteChapter(chapterId: number)` → `void`
- `getEditorData(chapterId: number, targetLanguage: string)` → `EditorData`

**Glossary:**
- `listGlossary(projectId: number)` → `GlossaryEntry[]`
- `createGlossaryEntry(data)` → `GlossaryEntry`
- `updateGlossaryEntry(entryId: number, data)` → `GlossaryEntry`
- `deleteGlossaryEntry(entryId: number)` → `void`

**Personas:**
- `listPersonas(projectId: number)` → `Persona[]`
- `createPersona(data)` → `Persona`
- `updatePersona(personaId: number, data)` → `Persona`
- `deletePersona(personaId: number)` → `void`

**Pipeline:**
- `translateChapter(chapterId: number, targetLanguage: string)` → Triggers translation
- `cancelPipeline()` → Cancels active pipeline

---

### `types.ts`

TypeScript interfaces matching the Python backend schema.

**Core Domain Types:**

```typescript
interface Project {
  id: number;
  name: string;
  description: string | null;
  source_language: string;
  target_language: string;
  genre: string | null;
  pipeline_type: string;
  llm_provider: string;
  created_at: string;
  updated_at: string;
  chapter_count?: number;
}

interface Chapter {
  id: number;
  project_id: number;
  title: string;
  order: number;
  source_content: string | null;
  translated_content: string | null;
  translation_stale: boolean;
  created_at: string;
  updated_at: string;
  segment_count?: number;
  translated_count?: number;
}

interface Segment {
  id: number;
  chapter_id: number;
  order: number;
  source_text: string;
  speaker: string | null;
  segment_type: string;
  source_start_offset: number | null;
  source_end_offset: number | null;
}

interface Translation {
  id: number;
  segment_id: number;
  target_language: string;
  translated_text: string;
  status: "pending" | "translating" | "translated" | "reviewed" | "approved";
  manually_edited: boolean;
  translated_start_offset: number | null;
  translated_end_offset: number | null;
  batch_id: number | null;
}

interface GlossaryEntry {
  id: number;
  project_id: number;
  source_term: string;
  translated_term: string;
  term_type: string;
  notes: string | null;
  context: string | null;
  auto_detected: boolean;
}

interface Persona {
  id: number;
  project_id: number;
  name: string;
  aliases: string[] | null;
  personality: string | null;
  speech_style: string | null;
  formality_level: number;
  age_group: string | null;
  appearance_count: number;
  auto_detected: boolean;
}
```

**Editor Data Structure:**

```typescript
interface EditorData {
  source_connected_text: string;        // Continuous source text
  translated_connected_text: string;    // Continuous translated text
  segment_map: SegmentMapEntry[];       // Offset mapping
}

interface SegmentMapEntry {
  segment_id: number;
  source_start: number;      // Character offset in source text
  source_end: number;
  translated_start: number;  // Character offset in translated text
  translated_end: number;
  type: string;              // "dialogue" | "narration"
  speaker: string | null;
  batch_id: number | null;
}
```

**Pipeline Types:**

```typescript
interface PipelineProgress {
  stage: string;      // Current pipeline stage key
  progress: number;   // 0.0 to 1.0
  message: string;    // Human-readable status
}

interface PipelineRun {
  id: number;
  chapter_id: number;
  target_language: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  stats: Record<string, unknown> | null;
}
```

---

## State Management (`stores/`)

### `app-store.ts`

**Purpose:** Application-wide UI state (theme, sidecar, command bar).

```typescript
interface AppState {
  sidecarConnected: boolean;
  setSidecarConnected: (connected: boolean) => void;
  theme: "light" | "dark" | "system";
  setTheme: (theme: "light" | "dark" | "system") => void;
  commandBarOpen: boolean;
  setCommandBarOpen: (open: boolean) => void;
  toggleCommandBar: () => void;
}
```

**Usage:**

```typescript
const { theme, setTheme, commandBarOpen, toggleCommandBar } = useAppStore();
```

**Implementation Notes:**
- `setTheme()` applies `data-theme` attribute to `<html>` immediately
- `sidecarConnected` is updated via `onSidecarStatus()` event listener

---

### `editor-store.ts`

**Purpose:** Editor-specific UI state (active segment, editing mode, segment map).

```typescript
interface EditorState {
  activeSegmentId: number | null;         // Highlighted segment
  setActiveSegment: (id: number | null) => void;
  editingSegmentId: number | null;        // Currently editing segment
  setEditingSegment: (id: number | null) => void;
  editText: string;                       // Text in inline editor
  setEditText: (text: string) => void;
  segmentMap: SegmentMapEntry[];          // Cached segment map
  setSegmentMap: (map: SegmentMapEntry[]) => void;
  showReasoning: boolean;                 // CoT panel visibility
  toggleReasoning: () => void;
}
```

**Usage:**

```typescript
const { activeSegmentId, setActiveSegment } = useEditorStore();
```

---

### `pipeline-store.ts`

**Purpose:** Translation pipeline progress tracking.

```typescript
interface PipelineState {
  isRunning: boolean;
  currentStage: string | null;
  progress: number;        // 0.0 to 1.0
  message: string;
  setProgress: (stage: string, progress: number, message: string) => void;
  start: () => void;
  finish: () => void;
  reset: () => void;
}
```

**Usage:**

```typescript
const { isRunning, currentStage, progress, message } = usePipelineStore();
```

**Flow:**
1. `TranslateButton` calls `start()` before mutation
2. `useProgress` hook listens to `onPipelineProgress()` events
3. Events call `setProgress()` to update store
4. `ProgressOverlay` reads store and displays modal
5. On completion, `finish()` is called

---

## Hooks (`hooks/`)

### `useProject.ts`

**Queries:**

```typescript
useProjects() → { data: Project[], isLoading, error }
useProject(id: number | null) → { data: Project, isLoading, error }
```

**Mutations:**

```typescript
useCreateProject() → { mutate, mutateAsync, isPending }
  // mutate({ name, source_language?, target_language?, genre?, description? })

useUpdateProject() → { mutate, mutateAsync, isPending }
  // mutate({ id, ...data })

useDeleteProject() → { mutate, mutateAsync, isPending }
  // mutate(id)
```

**Cache Invalidation:**
- `createProject` → Invalidates `["projects"]`
- `updateProject` → Invalidates `["projects"]` and `["project", id]`
- `deleteProject` → Invalidates `["projects"]`

---

### `useChapter.ts`

**Queries:**

```typescript
useChapters(projectId: number | null) → { data: Chapter[], isLoading, error }
useChapter(id: number | null) → { data: Chapter, isLoading, error }
useEditorData(chapterId: number | null, targetLanguage: string) → { data: EditorData, isLoading, error }
```

**Mutations:**

```typescript
useCreateChapter() → { mutate, mutateAsync, isPending }
  // mutate({ project_id, title, source_content? })

useUpdateChapter() → { mutate, mutateAsync, isPending }
  // mutate({ id, ...data })

useDeleteChapter() → { mutate, mutateAsync, isPending }
  // mutate(id)
```

**Cache Invalidation:**
- `createChapter` → Invalidates `["chapters", projectId]`
- `updateChapter` → Invalidates `["chapter", id]` and `["chapters"]`
- `deleteChapter` → Invalidates `["chapters"]`

---

### `useGlossary.ts`

**Queries:**

```typescript
useGlossary(projectId: number | null) → { data: GlossaryEntry[], isLoading, error }
```

**Mutations:**

```typescript
useCreateGlossaryEntry() → { mutate, mutateAsync, isPending }
  // mutate({ project_id, source_term, translated_term, term_type?, notes? })

useUpdateGlossaryEntry() → { mutate, mutateAsync, isPending }
  // mutate({ id, ...data })

useDeleteGlossaryEntry() → { mutate, mutateAsync, isPending }
  // mutate(id)
```

---

### `usePersonas.ts`

**Queries:**

```typescript
usePersonas(projectId: number | null) → { data: Persona[], isLoading, error }
```

**Mutations:**

```typescript
useCreatePersona() → { mutate, mutateAsync, isPending }
  // mutate({ project_id, name, ...data })

useUpdatePersona() → { mutate, mutateAsync, isPending }
  // mutate({ id, ...data })

useDeletePersona() → { mutate, mutateAsync, isPending }
  // mutate(id)
```

---

### `useTranslation.ts`

**Mutation:**

```typescript
useTranslateChapter() → { mutate, mutateAsync, isPending }
  // mutate({ chapterId, targetLanguage })
```

**Cache Invalidation:**
- Invalidates `["chapter", chapterId]`
- Invalidates `["editor-data", chapterId]`

---

### `useProgress.ts`

**Purpose:** Subscribes to pipeline progress events and updates `usePipelineStore`.

```typescript
useProgress() → PipelineState
```

**Implementation:**

```typescript
export function useProgress() {
  const setProgress = usePipelineStore((s) => s.setProgress);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    onPipelineProgress((p) => {
      setProgress(p.stage, p.progress, p.message);
    }).then((fn) => { unlisten = fn; });
    return () => { unlisten?.(); };
  }, [setProgress]);

  return usePipelineStore();
}
```

---

### `useTheme.ts`

**Purpose:** Applies theme to document root and responds to system theme changes.

```typescript
useTheme() → { theme: "light" | "dark" | "system", setTheme: (theme) => void }
```

**Implementation:**

```typescript
export function useTheme() {
  const { theme, setTheme } = useAppStore();

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.classList.toggle("dark", prefersDark);
    } else {
      root.classList.toggle("dark", theme === "dark");
    }
  }, [theme]);

  return { theme, setTheme };
}
```

---

### `useToast.ts`

**Purpose:** Manages toast notification state for showing success/error/info messages.

```typescript
useToast() → { toast: ToastState | null, showToast: (message: string, type: ToastType) => void, hideToast: () => void }
```

**Types:**

```typescript
type ToastType = "info" | "success" | "error";

interface ToastState {
  message: string;
  type: ToastType;
}
```

**Usage:**

```typescript
const { toast, showToast, hideToast } = useToast();

// Show a toast
showToast("Settings saved!", "success");
showToast("Connection failed", "error");

// Render toast
{toast && <Toast message={toast.message} type={toast.type} onClose={hideToast} />}
```

**Note:** Replaces browser `alert()` calls which don't work reliably in Tauri's WebView.

---

## Pages (`pages/`)

### `ProjectsPage.tsx`

**Purpose:** Dashboard showing all projects with create dialog.

**State:**
- `useProjects()` — Fetch all projects
- `useCreateProject()` — Create mutation
- Local state: dialog open, form data

**Layout:**
- Header with "New Project" button
- Empty state if no projects
- Grid of `ProjectCard` components
- Create dialog with name, description, source/target language, genre

**Navigation:**
- Click card → Navigate to `/project/:id`
- After create → Navigate to new project

---

### `ProjectPage.tsx`

**Purpose:** Project detail with tabs for chapters, glossary, personas.

**State:**
- `useProject(projectId)` — Fetch project
- `useCreateChapter()` — Create chapter mutation
- `useUpdateProject()` — Update project mutation
- `useDeleteProject()` — Delete project mutation
- Local state: active tab, dialogs

**Layout:**
- Breadcrumb back to projects
- Project header with name, languages, genre, description
- Edit/Delete buttons
- Tab bar: Chapters | Glossary | Personas
- Tab content area

**Tabs:**
1. **Chapters:** `ChapterList` component with "Add Chapter" button
2. **Glossary:** `GlossaryPanel` component
3. **Personas:** `PersonaPanel` component

---

### `EditorPage.tsx`

**Purpose:** Side-by-side editor with translation controls.

**State:**
- `useChapter(chapterId)` — Fetch chapter metadata
- `useEditorData(chapterId, targetLanguage)` — Fetch editor data
- `useProgress()` — Pipeline progress
- Local state: target language selector

**Layout:**
- Top bar with:
  - Back to project button
  - Chapter title
  - Target language selector
  - Translate button
  - Export button
- Main area: `SideBySideEditor` component
- Bottom panel: `CoTReasoningPanel` component
- Overlay: `ProgressOverlay` (when `isRunning`)

**Flow:**
1. Load chapter and editor data
2. User selects target language
3. User clicks "Translate"
4. `TranslateButton` triggers `useTranslateChapter` mutation
5. `ProgressOverlay` appears with pipeline stages
6. `useProgress` hook updates store from events
7. On completion, editor data re-fetches automatically

---

### `SettingsPage.tsx`

**Purpose:** Configuration for API keys, theme, default languages.

**State:**
- `useAppStore()` — Theme
- Local state: API keys, show/hide toggles, default provider, default languages

**Sections:**
1. **Appearance:** Light/Dark/System theme selector
2. **LLM API Keys:** Gemini, Claude, OpenAI (masked input with show/hide/test buttons)
3. **Default LLM Provider:** Gemini | Claude | OpenAI
4. **Default Languages:** Source and target language selectors
5. **About:** Version info

**Note:** Uses toast notifications for feedback (save success, connection test results). API keys are stored via Tauri IPC to the Python sidecar backend.

---

## Editor Components (`components/editor/`)

### `SideBySideEditor.tsx`

**Purpose:** Two-pane layout with synchronized scrolling and segment highlighting.

**Props:**

```typescript
interface SideBySideEditorProps {
  sourceText: string;
  translatedText: string;
  segmentMap: SegmentMapEntry[];
  onSegmentEdit?: (segmentId: number, newText: string) => void;
  onSegmentRetranslate?: (segmentId: number) => void;
}
```

**Features:**
- **Synchronized scrolling:** Scroll one pane, the other follows proportionally
- **Two panes:** Source (left) and Translation (right)
- **Segment highlighting:** Uses `SegmentHighlighter` HOC
- **Connected text views:** Both panes use `ConnectedTextView`

**Implementation Details:**

```typescript
// Scroll sync logic
const handleSourceScroll = () => {
  if (isTranslatedScrolling) return;
  isSourceScrolling = true;
  const scrollPercentage = sourceEl.scrollTop / (sourceEl.scrollHeight - sourceEl.clientHeight);
  translatedEl.scrollTop = scrollPercentage * (translatedEl.scrollHeight - translatedEl.clientHeight);
  setTimeout(() => { isSourceScrolling = false; }, 100);
};
```

**Layout:**

```
┌────────────────────┬────────────────────┐
│ Source Text        │ Translation        │
│                    │                    │
│ Segments rendered  │ Segments rendered  │
│ as continuous text │ as continuous text │
│                    │                    │
│ (read-only)        │ (editable)         │
└────────────────────┴────────────────────┘
```

---

### `ConnectedTextView.tsx`

**Purpose:** Render continuous text with clickable segment spans.

**Props:**

```typescript
interface ConnectedTextViewProps {
  text: string;
  sourceText?: string;
  segmentMap: SegmentMapEntry[];
  side: "source" | "translated";
  activeSegmentId: number | null;
  onSegmentClick: (segmentId: number) => void;
  onSegmentDoubleClick?: (segmentId: number) => void;
  onSegmentEdit?: (segmentId: number, newText: string) => void;
  onSegmentRetranslate?: (segmentId: number) => void;
}
```

**How It Works:**

1. **Build segments from map:**
   ```typescript
   const segments = useMemo(() => {
     const result = [];
     segmentMap.forEach((entry) => {
       const start = side === "source" ? entry.source_start : entry.translated_start;
       const end = side === "source" ? entry.source_end : entry.translated_end;
       const segmentText = text.slice(start, end);
       result.push({ id: entry.segment_id, text: segmentText, start, end, type: entry.type, speaker: entry.speaker });
     });
     return result;
   }, [text, segmentMap, side]);
   ```

2. **Render as inline spans:**
   ```tsx
   {segments.map((segment) => (
     <span
       key={segment.id}
       data-segment-id={segment.id}
       onClick={() => handleClick(segment.id)}
       onDoubleClick={(e) => handleDoubleClick(segment.id, e)}
       className={cn(
         "segment cursor-pointer transition-all duration-150 rounded-sm",
         activeSegmentId === segment.id && "segment-active",
         segment.type === "dialogue" && "segment-dialogue"
       )}
     >
       {segment.text}
     </span>
   ))}
   ```

3. **Interaction:**
   - **Single click:** Highlight segment on both sides
   - **Double click (translated side only):** Open `InlineEditor`

**CSS Classes:**
- `.segment` — Base class for all segments
- `.segment-active` — Highlighted segment (yellow background)
- `.segment-dialogue` — Dialogue segments (italic)

---

### `InlineEditor.tsx`

**Purpose:** Floating textarea for editing translated segment text.

**Props:**

```typescript
interface InlineEditorProps {
  segmentId: number;
  initialText: string;
  sourceText?: string;
  position: { top: number; left: number; width: number };
  onSave: (text: string) => void;
  onCancel: () => void;
}
```

**Features:**
- **Auto-focus and select:** On mount, focus textarea and select all text
- **Keyboard shortcuts:**
  - `Cmd/Ctrl+Enter` — Save
  - `Escape` — Cancel
- **Backdrop:** Dim background, click to cancel
- **Source reference:** Shows original source text above the edit area when available
- **Floating position:** Positioned absolutely over the segment

**UI:**
- Textarea with segment text
- Bottom bar with Cancel/Save buttons
- Keyboard hint: "⌘+Enter"

**Implementation:**

```typescript
const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    onSave(text);
  } else if (e.key === "Escape") {
    e.preventDefault();
    onCancel();
  }
};
```

---

### `CoTReasoningPanel.tsx`

**Purpose:** Collapsible panel showing Chain-of-Thought reasoning for active segment's batch.

**Props:**

```typescript
interface CoTReasoningPanelProps {
  chapterId: number;
}
```

**State:**
- Reads `activeSegmentId` and `showReasoning` from `useEditorStore`

**UI:**
- Collapsed by default, shows button with segment ID
- Expands to show:
  - **Situation Summary:** Context of the scene
  - **Character Events:** Key character actions/emotions
  - **Translation Reasoning:** Why specific word choices were made

**Implementation Note:**
- Currently shows placeholder data
- TODO: Fetch reasoning data based on `activeSegmentId`'s `batch_id`

---

### `SegmentHighlighter.tsx`

**Purpose:** Higher-order component providing segment interaction state.

**Pattern:** Render prop component

```typescript
<SegmentHighlighter segmentMap={segmentMap}>
  {({ activeSegmentId, onSegmentClick, onSegmentDoubleClick }) => (
    // Render children with these props
  )}
</SegmentHighlighter>
```

**Note:** This component is referenced but not in the codebase yet (may be implemented inline in `SideBySideEditor`).

---

## Layout Components (`components/layout/`)

### `AppShell.tsx`

**Purpose:** Root layout container with sidebar and main content area.

**Props:**

```typescript
interface AppShellProps {
  children: React.ReactNode;
}
```

**Structure:**

```tsx
<div className="flex h-screen bg-background text-foreground">
  <Sidebar />
  <main className="flex-1 overflow-auto">
    {children}
  </main>
  <CommandBar />
</div>
```

**Hooks:**
- Calls `useTheme()` to initialize theme on mount

---

### `Sidebar.tsx`

**Purpose:** Left navigation panel with logo, nav items, recent projects, sidecar status.

**State:**
- `useLocation()` — Current route for active state
- `useProjects()` — Fetch projects for recent list

**Sections:**
1. **Header:** "Fiction Translator v2.0"
2. **Nav items:** Projects, Settings
3. **Recent projects:** Last 5 projects
4. **Sidecar status:** Green dot + "Sidecar Connected"

**Implementation:**

```typescript
const navItems = [
  { label: "Projects", path: "/", icon: "📁" },
  { label: "Settings", path: "/settings", icon: "⚙️" },
];
```

---

### `CommandBar.tsx`

**Purpose:** Cmd+K command palette for quick navigation.

**State:**
- `useAppStore()` — `commandBarOpen`, `setCommandBarOpen`
- `useProjects()` — Projects for navigation commands
- Local state: search query

**Keyboard Shortcuts:**
- `Cmd/Ctrl+K` — Toggle command bar
- `Escape` — Close

**Commands:**
- "Go to Projects"
- "Go to Settings"
- "Open: [Project Name]" (for each project)

**UI:**
- Modal overlay
- Search input at top
- Filtered command list
- Click command to execute and close

---

## Translation Components (`components/translation/`)

### `TranslateButton.tsx`

**Purpose:** Button to trigger chapter translation.

**Props:**

```typescript
interface TranslateButtonProps {
  chapterId: number;
  targetLanguage: string;
  disabled?: boolean;
}
```

**State:**
- `useTranslateChapter()` — Translation mutation
- `usePipelineStore()` — `isRunning` state

**Behavior:**
- Disabled when `disabled` prop, `isPending`, or `isRunning`
- Shows spinner and "Translating..." when active
- Calls `translate({ chapterId, targetLanguage })` on click

---

### `ProgressOverlay.tsx`

**Purpose:** Full-screen modal showing translation pipeline progress.

**State:**
- `useProgress()` — `isRunning`, `progress`, `currentStage`, `message`

**UI:**
- Title: "Translating Chapter"
- Progress percentage: `Math.round(progress * 100)%`
- Progress bar (animated)
- Pipeline stages list with status indicators
- Cancel button

**Stage Status Logic:**

```typescript
const getStageStatus = (stageKey: string): "completed" | "active" | "pending" => {
  if (!currentStage) return "pending";
  const currentIndex = PIPELINE_STAGES.findIndex(s => s.key === currentStage);
  const stageIndex = PIPELINE_STAGES.findIndex(s => s.key === stageKey);
  if (stageIndex < currentIndex) return "completed";
  if (stageIndex === currentIndex) return "active";
  return "pending";
};
```

---

### `PipelineStageIndicator.tsx`

**Purpose:** Individual stage status indicator with icon and label.

**Props:**

```typescript
interface PipelineStageIndicatorProps {
  label: string;
  status: "completed" | "active" | "pending";
  detail?: string;  // Optional sub-message
}
```

**UI:**
- ✓ Completed (green)
- ● Active (blue, pulsing)
- ○ Pending (gray)
- Label and optional detail message

**Note:** This component is referenced but not in the codebase yet.

---

## Utilities (`lib/`)

### `constants.ts`

**Languages:**

```typescript
export const LANGUAGES = {
  ko: "Korean",
  ja: "Japanese",
  zh: "Chinese",
  en: "English",
  es: "Spanish",
  fr: "French",
  de: "German",
  pt: "Portuguese",
  ru: "Russian",
  vi: "Vietnamese",
  th: "Thai",
  id: "Indonesian",
} as const;

export type LanguageCode = keyof typeof LANGUAGES;
```

**LLM Providers:**

```typescript
export const LLM_PROVIDERS = {
  gemini: { name: "Google Gemini", model: "gemini-2.0-flash" },
  claude: { name: "Anthropic Claude", model: "claude-sonnet-4-5-20250929" },
  openai: { name: "OpenAI GPT", model: "gpt-4o" },
} as const;
```

**Genre Options:**

```typescript
export const GENRE_OPTIONS = [
  "fantasy", "romance", "thriller", "litrpg", "horror",
  "comedy", "sci-fi", "mystery", "drama", "action",
] as const;
```

**Pipeline Stages:**

```typescript
export const PIPELINE_STAGES = [
  { key: "load_context", label: "Loading Context" },
  { key: "segmentation", label: "Segmentation" },
  { key: "character_extraction", label: "Character Extraction" },
  { key: "validation", label: "Validation" },
  { key: "translation", label: "Translation" },
  { key: "review", label: "Review" },
  { key: "persona_learning", label: "Persona Learning" },
  { key: "finalize", label: "Finalizing" },
] as const;
```

---

### `formatters.ts`

**Date Formatting:**

```typescript
formatDate(dateStr: string | null): string
  // → "Jan 15, 2024"

formatRelativeTime(dateStr: string | null): string
  // → "5m ago" | "3h ago" | "2d ago" | "Jan 15, 2024"
```

**Text Utilities:**

```typescript
truncate(str: string, maxLen: number): string
  // → "This is a long text..." (if exceeds maxLen)

languageName(code: string): string
  // → "Korean" (from code "ko")
```

---

### `cn.ts`

**Purpose:** Utility for merging Tailwind classes with proper precedence.

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Usage:**

```typescript
<div className={cn("base-class", isActive && "active-class", className)} />
```

---

## Data Flow

### Page Navigation Flow

```
/ (ProjectsPage)
  → Click project card
    → /project/:id (ProjectPage)
      → Click chapter row
        → /editor/:chapterId (EditorPage)
```

### Translation Flow

```
1. User clicks "Translate" button
2. TranslateButton calls usePipelineStore.start()
3. TranslateButton.onClick → useTranslateChapter.mutate({ chapterId, targetLanguage })
4. Mutation calls api.translateChapter() → rpc("pipeline.translate_chapter", { ... })
5. Tauri invoke sends to Python sidecar
6. Sidecar starts pipeline, emits events via Tauri event system
7. Meanwhile: onPipelineProgress() event listener in useProgress hook
8. Each event updates usePipelineStore.setProgress(stage, progress, message)
9. ProgressOverlay reads pipeline store, shows real-time updates
10. Pipeline completes → React Query invalidates editor data
11. EditorPage automatically re-fetches with new translation
```

### Editor Interaction Flow

```
1. User clicks text in ConnectedTextView
2. ConnectedTextView identifies segment from character offset and segment map
3. onSegmentClick(segmentId) → useEditorStore.setActiveSegment(segmentId)
4. Both panes highlight via CSS class on matching <span data-segment-id={...}>
5. User double-clicks (translated side only)
6. ConnectedTextView calculates position, calls onSegmentDoubleClick(segmentId)
7. InlineEditor appears at segment position
8. User edits text, presses Cmd+Enter
9. onSave(newText) → onSegmentEdit(segmentId, newText)
10. API call updates segment (TODO: implement backend endpoint)
11. Editor data refetches, text updates
```

### Theme Flow

```
1. useTheme hook reads theme from app-store
2. useEffect watches theme changes
3. If theme === "system":
   - Check window.matchMedia("(prefers-color-scheme: dark)")
   - Apply .dark class to <html> based on system preference
4. If theme === "dark" or "light":
   - Apply .dark class directly (true for dark, false for light)
5. CSS variables in globals.css respond to .dark class
6. All components re-render with new colors
```

### Query Invalidation Flow

**After creating a project:**
```
useCreateProject.mutate() → api.createProject()
  → onSuccess: queryClient.invalidateQueries({ queryKey: ["projects"] })
    → useProjects() refetches automatically
      → ProjectsPage shows new project
```

**After translating a chapter:**
```
useTranslateChapter.mutate() → api.translateChapter()
  → onSuccess: queryClient.invalidateQueries({ queryKey: ["chapter", chapterId] })
             queryClient.invalidateQueries({ queryKey: ["editor-data", chapterId] })
    → useChapter() and useEditorData() refetch automatically
      → EditorPage shows updated translation
```

---

## Styling System

### CSS Variables

Located in `src/styles/globals.css`:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222 47% 11%;
  --primary: 222 47% 11%;
  --primary-foreground: 210 40% 98%;
  --card: 0 0% 100%;
  --border: 214 32% 91%;
  --input: 214 32% 91%;
  --ring: 222 84% 5%;
  --muted: 210 40% 96%;
  --muted-foreground: 215 16% 47%;
  --accent: 210 40% 96%;
  --accent-foreground: 222 47% 11%;
  /* ... */
}

.dark {
  --background: 222 47% 11%;
  --foreground: 210 40% 98%;
  --primary: 210 40% 98%;
  --primary-foreground: 222 47% 11%;
  --card: 222 47% 15%;
  --border: 217 33% 17%;
  /* ... */
}
```

### Tailwind Configuration

Colors use CSS variables via `hsl()`:

```js
// tailwind.config.js
colors: {
  background: "hsl(var(--background))",
  foreground: "hsl(var(--foreground))",
  primary: {
    DEFAULT: "hsl(var(--primary))",
    foreground: "hsl(var(--primary-foreground))",
  },
  // ...
}
```

### Component Classes

**Segment highlighting:**

```css
.segment {
  @apply cursor-pointer transition-all duration-150 rounded-sm;
}

.segment-active {
  @apply bg-yellow-200/30 dark:bg-yellow-900/30;
}

.segment-dialogue {
  @apply italic;
}
```

---

## Performance Considerations

### React Query Stale Time

```typescript
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30000 } },  // 30 seconds
});
```

Data is considered fresh for 30 seconds, preventing unnecessary refetches.

### Scroll Sync Debouncing

```typescript
setTimeout(() => { isSourceScrolling = false; }, 100);
```

Prevents scroll event ping-pong between panes.

### Segment Map Memoization

```typescript
const segments = useMemo(() => {
  // Build segments from map
}, [text, segmentMap, side]);
```

Only recomputes when text or map changes.

### Event Listener Cleanup

```typescript
useEffect(() => {
  let unlisten: (() => void) | null = null;
  onPipelineProgress((p) => { /* ... */ }).then((fn) => { unlisten = fn; });
  return () => { unlisten?.(); };
}, [setProgress]);
```

Prevents memory leaks from Tauri event listeners.

---

## Development Workflow

### Running the App

```bash
npm run tauri dev
```

Starts Vite dev server + Tauri window with hot reload.

### Building

```bash
npm run tauri build
```

Produces optimized production bundle + native executable.

### Type Checking

```bash
npm run typecheck
```

Runs TypeScript compiler in check mode.

---

## Future Enhancements

### Not Yet Implemented

1. **CoT reasoning data:** Currently shows placeholder, needs batch_id query to fetch real reasoning
2. **SegmentHighlighter component:** Referenced but may be implemented inline in `SideBySideEditor`
3. **PipelineStageIndicator component:** Referenced but not found in codebase

### Recently Implemented

1. **Segment editing:** Inline editor with source text reference and re-translate with guidance
2. **Export functionality:** Export translated content from EditorPage
3. **API key storage:** Keys stored via Tauri IPC, with connection testing per provider
4. **Shared UI components:** Extracted Textarea, Select, Label, ConfirmDialog as reusable forwardRef components
5. **Toast notifications:** Replaced browser `alert()` with in-app toast system (useToast hook + Toast component)
6. **ConfirmDialog:** Replaced browser `confirm()` with async-aware dialog component
7. **All page/panel components:** ProjectCard, ChapterList, GlossaryPanel, PersonaPanel, PersonaSummaryCard all implemented

### Recommended Next Steps

1. Fetch CoT reasoning from database based on batch_id
2. Add batch operations (translate multiple chapters)
3. Add translation memory/cache for repeated phrases
4. Implement collaborative editing features
