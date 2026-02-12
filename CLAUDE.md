# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fiction Translator v2 is a **Tauri v2 desktop app** for LLM-powered fiction translation with Chain-of-Thought reasoning. It has three layers:

1. **React frontend** (`src/`) — TypeScript, Vite, TailwindCSS, Zustand, TanStack React Query
2. **Rust shell** (`src-tauri/`) — Tauri v2, manages the Python sidecar lifecycle
3. **Python sidecar** (`sidecar/`) — LangGraph pipeline, SQLAlchemy 2.0, SQLite DB at `~/.fiction-translator/data.db`

Communication: Frontend → Tauri `invoke("rpc_call")` → Rust forwards JSON-RPC 2.0 over stdin/stdout → Python sidecar.

## Environment

- **Node.js** 20 / npm
- **Python** 3.11 (managed via **uv**)
- **Rust** stable (Tauri v2)
- **Package managers**: npm (frontend), uv (sidecar), cargo (Rust)

## Build & Dev Commands

```bash
# Full app with hot-reload (Tauri + Vite + Python sidecar)
npm run tauri dev

# Frontend only (no Tauri shell, no sidecar)
npm run dev                        # Vite dev server on localhost:1420

# TypeScript type check
npx tsc --noEmit

# Python sidecar setup (first time)
cd sidecar && uv sync --extra dev

# Python lint
cd sidecar && ruff check src/

# Python tests
cd sidecar && pytest

# Production build (builds PyInstaller binary + Tauri bundle)
npm run tauri build
```

## Architecture

### IPC Flow

All data flows through JSON-RPC 2.0:
- **Request**: `src/api/tauri-bridge.ts` → `rpc("method.name", params)` → Tauri `invoke("rpc_call")` → Rust `sidecar.rs` writes to Python stdin
- **Response**: Python stdout → Rust reads line → returns to frontend
- **Notifications** (streaming progress): Python writes notification → Rust emits Tauri event (`pipeline:progress`) → frontend listens via `@tauri-apps/api/event`

The `api` object in `src/api/tauri-bridge.ts` is the single source of truth for all available RPC methods.

### Frontend State

- **Server state**: TanStack React Query with query keys like `["projects"]`, `["project", id]`, `["chapters", projectId]`, `["editor-data", chapterId]`. Mutations auto-invalidate related queries.
- **UI state**: Zustand stores (`app-store.ts`, `editor-store.ts`, `pipeline-store.ts`) — ephemeral, no persistence.
- **Path alias**: `@/*` maps to `./src/*`

### LangGraph Translation Pipeline

8-node directed graph in `sidecar/src/fiction_translator/pipeline/graph.py`:

```
load_context → segment → extract_characters → validate
    validate --[pass]--> translate → review
    validate --[fail, <3 attempts]--> segment (retry)
    review --[pass]--> learn_personas → finalize → END
    review --[fail, <2 iterations]--> translate (retry)
```

Each node is in `pipeline/nodes/`. Conditional edges are in `pipeline/edges.py`. Progress callbacks emit JSON-RPC notifications.

### Database

10 SQLAlchemy 2.0 models in `sidecar/src/fiction_translator/db/models.py`: projects, chapters, segments, translations, translation_batches (CoT reasoning), glossary_entries, personas, persona_suggestions, pipeline_runs, exports.

### Python IPC Handlers

25 JSON-RPC method handlers in `sidecar/src/fiction_translator/ipc/handlers.py` under namespaces: `health.*`, `project.*`, `chapter.*`, `glossary.*`, `persona.*`, `pipeline.*`, `segment.*`, `export.*`, `batch.*`, `config.*`.

### Sidecar Lifecycle

- **Dev mode**: Rust runs `python3.11 -m fiction_translator` from source
- **Production**: PyInstaller single-file binary in `src-tauri/binaries/`
- Spawned on app startup in `lib.rs`, killed on window close
- Logs go to stderr (stdout is reserved for IPC)

## Key Patterns

- **React hooks** for data fetching live in `src/hooks/` (e.g., `useProject.ts`, `useChapter.ts`)
- **UI components** follow a `src/components/ui/` base library pattern with HSL CSS variables for theming
- **Routing**: React Router v6 — `/` (projects), `/project/:id`, `/editor/:chapterId`, `/settings`
- **Styling**: TailwindCSS with `cn()` utility (`clsx` + `tailwind-merge`) in `src/lib/cn.ts`
- **LLM providers**: Abstract `LLMProvider` in `sidecar/src/fiction_translator/llm/providers.py` with Gemini/Claude/OpenAI implementations
- **Python line length**: 100 chars (ruff config in `pyproject.toml`)

## CI

PR checks (`.github/workflows/check.yml`): `npx tsc --noEmit` + `ruff check src/` (in sidecar). Build workflow produces `.dmg` (macOS) and `.msi` (Windows).
