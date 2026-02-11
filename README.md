# Fiction Translator v2.0

A native desktop application for translating fiction (novels, web fiction, games) using LLM-powered Chain-of-Thought reasoning. Built as a complete rewrite of v1 (FastAPI+React) into a Tauri native desktop app.

## Overview

Fiction Translator v2.0 provides a professional translation environment with real-time pipeline progress, connected prose editing, and intelligent glossary management. The application uses a multi-stage LangGraph pipeline with Chain-of-Thought reasoning to produce high-quality translations while maintaining character consistency and narrative flow.

## Architecture

The application uses a three-layer architecture:

### 1. Tauri Rust Shell (`src-tauri/`)
Native desktop wrapper responsible for:
- Sidecar process lifecycle management
- IPC routing between frontend and Python backend
- Event forwarding for real-time updates
- Platform-specific capabilities

### 2. React Frontend (`src/`)
Modern SaaS-style UI featuring:
- Connected prose editor with side-by-side source/translation view
- Real-time pipeline progress monitoring
- Inline translation editing
- Glossary and persona management
- Dark/light theme support
- Command palette (Cmd+K)

### 3. Python Sidecar (`sidecar/`)
Business logic layer containing:
- LangGraph 8-node translation pipeline
- SQLite database with SQLAlchemy 2.0
- LLM provider integrations (Gemini, Claude, OpenAI)
- Knowledge base management (glossary, personas)

**IPC Protocol:** JSON-RPC 2.0 over stdin/stdout (newline-delimited JSON) between Rust and Python.

## Key Features

- **One-Click Translation**: Start translation with real-time pipeline progress tracking
- **Connected Prose View**: Continuous text display (not segment-by-segment) for natural reading
- **Chain-of-Thought Translation**: Batch translation with visible reasoning process
- **CoT Toggle**: Enable or disable Chain-of-Thought reasoning per translation for speed vs. quality control
- **Multi-Stage Pipeline**: 8-node LangGraph workflow with validation and review loops
- **Multi-LLM Support**: Google Gemini, Anthropic Claude, OpenAI GPT
- **Glossary Management**: Consistent terminology across translations
- **Character Personas**: Auto-detected character tracking with persona insights
- **Side-by-Side Editor**: Click-to-highlight segment mapping between source and translation
- **Source Text Preview**: View source text in a two-column layout before running translation
- **Paragraph Break Preservation**: Maintains original paragraph and line break structure through the pipeline
- **Smart Quote Normalization**: Automatically converts smart quotes to straight quotes before LLM processing
- **Inline Editing**: Direct translation editing with real-time updates
- **Export Support**: TXT and DOCX export formats
- **Command Palette**: Keyboard-driven navigation (Cmd+K)

## Tech Stack

### Desktop
- Tauri v2 (Rust)

### Frontend
- React 18
- TypeScript
- Vite
- TailwindCSS
- Zustand (UI state)
- TanStack React Query (server state)
- React Router v6
- Lucide React (icons)

### Backend
- Python 3.11+
- LangGraph
- SQLAlchemy 2.0
- SQLite

### LLM Providers
- Google Gemini
- Anthropic Claude
- OpenAI GPT

## Project Structure

```
fiction-translator-v2/
├── src-tauri/                          # Tauri Rust Shell
│   ├── Cargo.toml                      # Rust dependencies
│   ├── tauri.conf.json                 # App config (window, identifier, plugins)
│   ├── build.rs                        # Tauri build script
│   ├── capabilities/
│   │   └── default.json                # Tauri v2 permissions
│   ├── src/
│   │   ├── main.rs                     # Entry point
│   │   ├── lib.rs                      # App builder, plugin registration, sidecar auto-start
│   │   ├── sidecar.rs                  # Python process lifecycle (start/stop/call)
│   │   ├── ipc.rs                      # JSON-RPC message types, atomic ID generation
│   │   ├── commands.rs                 # Tauri command handlers (rpc_call, sidecar_status)
│   │   ├── state.rs                    # Shared app state (Arc<Mutex<SidecarProcess>>)
│   │   └── events.rs                   # Event structs for streaming progress
│   ├── DOCS_EN.md                      # English documentation
│   └── DOCS_KR.md                      # Korean documentation
│
├── src/                                # React Frontend
│   ├── main.tsx                        # React entry point
│   ├── App.tsx                         # Root component with routing
│   ├── index.css                       # Global styles (CSS variables, Tailwind)
│   ├── api/
│   │   ├── tauri-bridge.ts             # invoke() wrapper + event listeners
│   │   └── types.ts                    # Shared TypeScript interfaces
│   ├── stores/
│   │   ├── app-store.ts                # Global UI state (theme, sidecar status)
│   │   ├── editor-store.ts             # Editor state (active segment, editing)
│   │   └── pipeline-store.ts           # Translation pipeline progress
│   ├── hooks/
│   │   ├── useProject.ts              # Project CRUD queries/mutations
│   │   ├── useChapter.ts             # Chapter CRUD + editor data
│   │   ├── useGlossary.ts            # Glossary CRUD
│   │   ├── usePersonas.ts            # Persona CRUD
│   │   ├── useTranslation.ts         # Translation pipeline trigger
│   │   ├── useProgress.ts            # Real-time progress via Tauri events
│   │   └── useTheme.ts               # Dark/light theme management
│   ├── pages/
│   │   ├── ProjectsPage.tsx           # Dashboard with project grid
│   │   ├── ProjectPage.tsx            # Project detail (chapters/glossary/personas tabs)
│   │   ├── EditorPage.tsx             # Side-by-side translation editor (core)
│   │   └── SettingsPage.tsx           # API keys, theme, preferences
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx           # Main layout wrapper
│   │   │   ├── Sidebar.tsx            # Navigation sidebar
│   │   │   └── CommandBar.tsx         # Cmd+K command palette
│   │   ├── editor/
│   │   │   ├── SideBySideEditor.tsx   # Two-pane editor with synced scroll
│   │   │   ├── ConnectedTextView.tsx  # Prose renderer with invisible segment spans
│   │   │   ├── InlineEditor.tsx       # Floating textarea for editing translations
│   │   │   ├── CoTReasoningPanel.tsx  # Chain-of-Thought reasoning display
│   │   │   └── SegmentHighlighter.tsx # Cross-pane highlight management
│   │   ├── translation/
│   │   │   ├── TranslateButton.tsx    # One-click translate trigger
│   │   │   ├── ProgressOverlay.tsx    # Pipeline progress modal
│   │   │   └── PipelineStageIndicator.tsx  # Individual stage status
│   │   ├── project/
│   │   │   ├── ProjectCard.tsx        # Project grid card
│   │   │   ├── ChapterList.tsx        # Chapter listing
│   │   │   └── ChapterCard.tsx        # Chapter card
│   │   ├── knowledge/
│   │   │   ├── GlossaryPanel.tsx      # Glossary management UI
│   │   │   ├── PersonaPanel.tsx       # Character persona management
│   │   │   └── PersonaSummaryCard.tsx # Persona summary display
│   │   └── ui/
│   │       ├── Button.tsx             # Reusable button component
│   │       ├── Input.tsx              # Reusable input component
│   │       ├── Dialog.tsx             # Modal dialog component
│   │       └── Toast.tsx              # Toast notification component
│   ├── lib/
│   │   ├── cn.ts                      # Tailwind class merger utility
│   │   ├── constants.ts              # App constants
│   │   └── formatters.ts            # Date/number formatters
│   ├── DOCS_EN.md                    # English documentation
│   └── DOCS_KR.md                    # Korean documentation
│
├── sidecar/                           # Python Sidecar (LangGraph)
│   ├── pyproject.toml                 # Python dependencies and project config
│   └── src/fiction_translator/
│       ├── main.py                    # Entry point: init DB + start JSON-RPC server
│       ├── ipc/
│       │   ├── protocol.py            # JSON-RPC message schemas and parser
│       │   ├── server.py              # Async stdin/stdout JSON-RPC server
│       │   └── handlers.py            # 25 method handlers routing to services
│       ├── db/
│       │   ├── models.py              # 10 SQLAlchemy 2.0 models
│       │   └── session.py             # Engine, session factory, init_db()
│       ├── services/
│       │   ├── project_service.py     # Project CRUD
│       │   ├── chapter_service.py     # Chapter CRUD + get_editor_data()
│       │   ├── glossary_service.py    # Glossary CRUD + bulk import
│       │   ├── persona_service.py     # Persona CRUD + suggestion handling
│       │   └── export_service.py      # TXT/DOCX export
│       ├── pipeline/
│       │   ├── state.py               # TranslationState TypedDict
│       │   ├── graph.py               # LangGraph StateGraph definition
│       │   ├── edges.py               # Conditional routing (validation gate, review loop)
│       │   ├── callbacks.py           # Progress notification emitter
│       │   └── nodes/
│       │       ├── segmenter.py       # Text segmentation (rule-based + LLM)
│       │       ├── character_extractor.py  # Speaker detection (regex + LLM)
│       │       ├── validator.py       # Segmentation quality validator
│       │       ├── translator.py      # CoT batch translator
│       │       ├── reviewer.py        # Translation quality reviewer
│       │       └── persona_learner.py # Character insight extraction
│       ├── llm/
│       │   ├── providers.py           # LLMProvider ABC + Gemini/Claude/OpenAI
│       │   └── prompts/
│       │       ├── cot_translation.py      # CoT translation prompt builder
│       │       ├── text_utils.py           # Smart quote normalization utility
│       │       ├── segmentation.py         # Segmentation prompt
│       │       ├── character_extraction.py # Character extraction prompt
│       │       ├── validation.py           # Validation prompt
│       │       ├── review.py               # Review prompt
│       │       └── persona_analysis.py     # Persona analysis prompt
│   ├── tests/                             # Unit tests
│   │   ├── test_text_utils.py             # Quote normalization tests
│   │   └── test_paragraph_breaks.py       # Paragraph break tests
│       ├── DOCS_EN.md                 # English documentation
│       └── DOCS_KR.md                 # Korean documentation
│
├── .github/workflows/
│   ├── build.yml                      # CI/CD: Build macOS + Windows + release
│   └── check.yml                      # PR checks: TypeScript + Python lint
│
├── index.html                         # HTML entry point
├── package.json                       # Node.js dependencies
├── vite.config.ts                     # Vite bundler config
├── tsconfig.json                      # TypeScript config
├── tailwind.config.ts                 # Tailwind CSS config
└── postcss.config.js                  # PostCSS config
```

## Development Setup

### Prerequisites

- Node.js 18+
- Python 3.11+
- Rust toolchain (for Tauri development)

### Installation

1. **Frontend Dependencies**
   ```bash
   npm install
   ```

2. **Python Sidecar**
   ```bash
   cd sidecar
   pip install -e .
   ```

### Development Commands

- **Development Mode** (with Tauri hot-reload)
  ```bash
  npm run tauri dev
  ```

- **Frontend Only** (for UI development without Tauri)
  ```bash
  npm run dev
  ```

- **Production Build**
  ```bash
  npm run tauri build
  ```

## Database

The application uses SQLite for data persistence.

**Location:** `~/.fiction-translator/data.db`

**Schema:** 10 tables
- `projects` - Translation projects
- `chapters` - Chapter content and metadata
- `segments` - Text segments with boundaries
- `translations` - Translated segment text
- `translation_batches` - Batch translation metadata
- `glossary_entries` - Terminology glossary
- `personas` - Character personas and traits
- `persona_suggestions` - Auto-detected persona suggestions
- `pipeline_runs` - Translation pipeline execution logs
- `exports` - Export history

**Initialization:** Database is auto-created on first launch with all required tables and indexes.

## LangGraph Translation Pipeline

The translation pipeline consists of 8 nodes with conditional routing:

```
Load Context
    ↓
Segmenter (text segmentation with rule-based + LLM)
    ↓
Character Extractor (speaker detection via regex + LLM)
    ↓
Validator (segmentation quality check)
    ├─ PASS → Continue
    └─ FAIL → Retry Segmenter (max 2 attempts)
    ↓
CoT Translator (batch translation with Chain-of-Thought)
    ↓
Reviewer (translation quality assessment)
    ├─ PASS → Continue
    └─ FAIL → Retry Translator (max 2 attempts)
    ↓
Persona Learner (character insight extraction)
    ↓
Finalize (save results to database)
```

**Pipeline Features:**
- Real-time progress notifications
- Automatic retry with exponential backoff
- Quality gates at segmentation and translation stages
- Chain-of-Thought reasoning preservation
- Character persona learning
- Smart quote normalization before LLM processing
- Segment ID fallback matching for robust LLM response handling

## Supported Languages

**Source and Target Languages:**
- Korean
- Japanese
- Chinese
- English
- Spanish
- French
- German
- Portuguese
- Russian
- Vietnamese
- Thai
- Indonesian

The target language is configurable per translation run, allowing flexible language pair combinations.

## Documentation

Each architectural layer includes bilingual documentation:

### Tauri Rust Shell
- `src-tauri/DOCS_EN.md` - English documentation
- `src-tauri/DOCS_KR.md` - Korean documentation

### React Frontend
- `src/DOCS_EN.md` - English documentation
- `src/DOCS_KR.md` - Korean documentation

### Python Sidecar
- `sidecar/DOCS_EN.md` - English documentation
- `sidecar/DOCS_KR.md` - Korean documentation

## License

MIT
