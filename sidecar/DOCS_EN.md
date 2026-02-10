# Fiction Translator v2.0 — Python Sidecar Documentation

## Overview

The Python sidecar is the backend engine of Fiction Translator v2.0. It runs as a separate process alongside the Tauri application, handling all translation logic, LLM interactions, and data persistence. The sidecar communicates with the Tauri frontend via JSON-RPC 2.0 over stdin/stdout.

**Key responsibilities:**
- Process translation requests through a LangGraph-based pipeline
- Manage SQLite database for projects, chapters, segments, and personas
- Provide LLM provider abstraction (Gemini, Claude, OpenAI)
- Stream progress updates to the frontend during translation
- Export translated content to various formats (TXT, DOCX)

## Why This Architecture?

### Why a Python Sidecar (not embedded)?

**Reason 1: Python-native ecosystem**
- LangGraph and modern LLM SDKs are Python-first
- Direct access to `httpx`, `sqlalchemy`, `python-docx` without FFI overhead
- Faster iteration: `python -m fiction_translator` runs standalone during development

**Reason 2: Crash isolation**
- Sidecar crashes don't kill the Tauri app
- Tauri can restart the sidecar on failure
- Clear separation: Rust owns UI/IPC, Python owns AI/data

**Reason 3: Deployment simplicity**
- PyInstaller bundles the entire sidecar into a single binary (`fiction-translator-sidecar`)
- Tauri's `sidecar` config automatically spawns it on app launch
- Users never see "install Python" prompts

### Why JSON-RPC 2.0 over stdin/stdout?

**Reason 1: Native Tauri support**
- Tauri has built-in sidecar management with stdin/stdout pipes
- No HTTP server = no port conflicts, no firewall prompts
- Works identically on macOS, Windows, Linux

**Reason 2: Simplicity**
- Line-based framing: one JSON object per line
- Request ID matching for async responses
- Notifications (progress updates) don't need responses

**Reason 3: Bidirectional**
- Tauri → Python: method calls (requests)
- Python → Tauri: progress updates (notifications)
- Both share the same pipe, avoiding coordination issues

### Why SQLAlchemy + SQLite?

**Reason 1: Single-file database**
- `~/.fiction-translator/data.db` contains all user data
- No server process, no configuration
- Easy backup: just copy the file

**Reason 2: Type safety with SQLAlchemy 2.0**
- `Mapped[int]` types catch errors at development time
- Relationship tracking prevents orphaned data
- Migrations are straightforward with Alembic (future)

**Reason 3: Python is the single source of truth**
- Tauri never touches the DB directly
- All CRUD goes through service functions
- Easier to maintain consistency and add features

### Why LangGraph?

**Reason 1: State management**
- `TranslationState` TypedDict flows through the entire pipeline
- Nodes return partial updates, LangGraph merges them automatically
- Easy to track progress (`validation_attempts`, `review_iteration`)

**Reason 2: Conditional edges**
- Validation gate: re-segment up to 3 times on failure
- Review loop: re-translate flagged segments up to 2 times
- Declarative flow is easier to understand than imperative loops

**Reason 3: Progress tracking**
- Nodes call `notify(callback, stage, pct, message)` to stream progress
- LangGraph handles async execution without blocking
- Future: add checkpointing for resume-on-crash

**Reason 4: Extensibility**
- Adding a new node (e.g., "tone_adjuster") is just adding a function + edge
- Swapping translation strategies (CoT vs streaming) is a node replacement
- Easy to A/B test different pipeline configurations

## Directory Structure

```
sidecar/
├── pyproject.toml              # Project metadata, dependencies (Poetry or pip)
├── build.py                    # PyInstaller build script for binary distribution
└── src/fiction_translator/
    ├── main.py                 # Entry point: initializes DB, starts IPC server
    ├── __main__.py             # Entry point for `python -m fiction_translator`
    ├── ipc/                    # JSON-RPC communication layer
    │   ├── protocol.py         # Message types (Request, Response, Notification, Error)
    │   ├── server.py           # Async server loop (stdin → handler → stdout)
    │   └── handlers.py         # 29 method handlers (project.*, chapter.*, pipeline.*, etc.)
    ├── db/                     # Database layer (SQLAlchemy 2.0)
    │   ├── models.py           # 10 tables: Project, Chapter, Segment, Translation, etc.
    │   └── session.py          # Engine creation, session factory, init_db()
    ├── services/               # Business logic (CRUD + domain operations)
    │   ├── project_service.py  # list/create/update/delete projects
    │   ├── chapter_service.py  # chapters + get_editor_data (connected text view)
    │   ├── glossary_service.py # terminology management
    │   ├── persona_service.py  # character voice profiles
    │   └── export_service.py   # TXT/DOCX export
    ├── pipeline/               # LangGraph translation pipeline
    │   ├── graph.py            # Pipeline definition: nodes, edges, run_translation_pipeline()
    │   ├── state.py            # TranslationState TypedDict (shared state across nodes)
    │   ├── edges.py            # Conditional edge functions (should_re_segment, should_re_translate)
    │   ├── callbacks.py        # Progress notification helpers
    │   └── nodes/              # Pipeline node implementations
    │       ├── segmenter.py    # Split text into translatable segments with offsets
    │       ├── character_extractor.py  # Detect speakers/characters (regex + LLM)
    │       ├── validator.py    # Check segmentation quality (7 validation rules)
    │       ├── translator.py   # CoT batch translation with glossary/persona context
    │       ├── reviewer.py     # Quality check, flag segments for re-translation
    │       └── persona_learner.py  # Extract character insights from translations
    └── llm/                    # LLM provider abstraction
        ├── providers.py        # Unified interface: GeminiProvider, ClaudeProvider, OpenAIProvider
        └── prompts/            # Prompt builders for each pipeline stage
            ├── segmentation.py
            ├── character_extraction.py
            ├── validation.py
            ├── cot_translation.py
            ├── review.py
            └── persona_analysis.py
```

## Module Documentation

### 1. IPC Layer (`ipc/`)

#### `protocol.py` — Message Types

Defines JSON-RPC 2.0 data structures:

**`JsonRpcRequest`**
- `method: str` — RPC method name (e.g., `"project.list"`)
- `params: dict | list | None` — Named or positional parameters
- `id: int | str | None` — Request ID for matching responses (None = notification)
- `jsonrpc: str` — Always `"2.0"`
- Methods: `to_json()`, `from_dict(data)`

**`JsonRpcResponse`**
- `id: int | str | None` — Matches the request ID
- `result: Any` — Successful result (mutually exclusive with `error`)
- `error: JsonRpcError | None` — Error details (mutually exclusive with `result`)
- `jsonrpc: str` — Always `"2.0"`
- Method: `to_json()`

**`JsonRpcNotification`**
- Same as `JsonRpcRequest` but always has `id=None`
- Used for push events (e.g., progress updates)
- No response expected
- Method: `to_json()`

**`JsonRpcError`**
- `code: int` — Standard error codes (see constants below)
- `message: str` — Human-readable error description
- `data: Any` — Optional additional context

**Standard error codes:**
```python
PARSE_ERROR = -32700       # Invalid JSON
INVALID_REQUEST = -32600   # Missing required fields
METHOD_NOT_FOUND = -32601  # Unknown method
INVALID_PARAMS = -32602    # Wrong parameter types
INTERNAL_ERROR = -32603    # Handler exception
```

**`parse_message(raw: str) -> JsonRpcRequest | None`**
- Parse a raw JSON string into a `JsonRpcRequest`
- Returns `None` on parse failure (caller sends PARSE_ERROR response)

#### `server.py` — Server Loop

**`JsonRpcServer`**

Main async server class that manages the RPC lifecycle.

**Constructor: `__init__()`**
- Initializes empty handler registry
- Creates write lock for thread-safe stdout access

**Methods:**

**`register(method: str, handler: Callable[..., Awaitable[Any]])`**
- Register a single method handler
- Handler signature: `async def handler(**params) -> dict`

**`register_all(handlers: dict[str, Callable])`**
- Bulk register multiple handlers
- Called during startup from `handlers.get_all_handlers()`

**`async send_notification(method: str, params: dict | None = None)`**
- Push a notification to Tauri (e.g., progress updates)
- Writes a `JsonRpcNotification` to stdout
- Non-blocking, no response expected

**`async run()`**
- Main event loop:
  1. Connect stdin to `asyncio.StreamReader`
  2. Read lines in a loop
  3. Parse each line → `JsonRpcRequest`
  4. Dispatch to handler → get `JsonRpcResponse`
  5. Write response to stdout
  6. Handle cancellation and errors
- Exits when stdin closes (Tauri process exit)

**`stop()`**
- Signal the server to stop
- Sets `_running = False`

**Internal methods:**

**`async _handle_request(request: JsonRpcRequest) -> JsonRpcResponse | None`**
- Route request to the registered handler
- If `request.id is None`, treat as notification (no response)
- Catch handler exceptions → return `INTERNAL_ERROR` response
- Return `METHOD_NOT_FOUND` if no handler registered

**`async _write(message: str)`**
- Write a newline-terminated message to stdout
- Thread-safe with `asyncio.Lock`
- Flushes immediately (critical for IPC responsiveness)

**Flow diagram:**
```
stdin → readline → parse JSON → _handle_request → handler(**params)
                                      ↓
                                 JsonRpcResponse → _write → stdout

send_notification → JsonRpcNotification → _write → stdout (parallel)
```

#### `handlers.py` — Method Router

Registers 29 RPC methods organized by domain. Each handler:
1. Opens a DB session with `get_db()`
2. Calls a service function
3. Closes the session
4. Returns a dict (auto-serialized to JSON)

**Global state:**

**`_api_keys: dict[str, str]`**
- In-memory API key storage
- Keys: `"gemini"`, `"claude"`, `"openai"`, `"google"`, `"anthropic"`
- Populated by `config.set_keys` from Tauri's secure keychain

**`_server: JsonRpcServer | None`**
- Reference to the server for sending notifications
- Set via `set_server(server)` during startup

**Helper:**

**`async send_progress(stage: str, progress: float, message: str = "")`**
- Send `pipeline.progress` notification to Tauri
- Called by pipeline nodes via callback

**Health methods:**

**`async health_check() -> dict`**
- Returns `{"status": "ok", "version": "2.0.0"}`
- Used by Tauri to verify sidecar is alive

**Config methods:**

**`async config_set_keys(**keys: str) -> dict`**
- Store API keys in `_api_keys` (in-memory only)
- Params: `gemini="...", claude="...", openai="..."`
- Returns `{"stored": ["gemini", "claude"]}`

**`async config_get_keys() -> dict`**
- Returns which providers have keys configured
- Example: `{"gemini": true, "claude": false, "openai": true}`

**`async config_test_provider(provider: str) -> dict`**
- Test if an LLM provider is working
- Sends "Say 'hello' in one word" to the LLM
- Returns `{"success": true, "response": "Hello"}` or `{"success": false, "error": "..."}`

**Project methods:**

**`async project_list() -> list[dict]`**
- Returns all projects with chapter counts
- Ordered by `updated_at DESC`

**`async project_create(name: str, source_language: str = "ko", target_language: str = "en", **kwargs) -> dict`**
- Create a new project
- Optional kwargs: `description`, `genre`, `style_settings`, `pipeline_type`, `llm_provider`
- Returns project dict with `id`, `created_at`, etc.

**`async project_get(project_id: int) -> dict`**
- Get a single project by ID
- Raises `ValueError` if not found

**`async project_update(project_id: int, **kwargs) -> dict`**
- Update project fields
- Accepted kwargs: any field except `id`
- Returns updated project dict

**`async project_delete(project_id: int) -> dict`**
- Delete project and all related data (cascades to chapters, segments, translations)
- Returns `{"deleted": true, "id": project_id}`

**Chapter methods:**

**`async chapter_list(project_id: int) -> list[dict]`**
- List chapters in a project
- Includes `segment_count` and `translated_count` statistics
- Ordered by `order` field

**`async chapter_create(project_id: int, title: str, source_content: str = "", **kwargs) -> dict`**
- Create a new chapter
- Optional kwargs: `file_path`
- Auto-assigns next `order` number
- Returns chapter dict

**`async chapter_get(chapter_id: int) -> dict`**
- Get a single chapter by ID

**`async chapter_update(chapter_id: int, **kwargs) -> dict`**
- Update chapter fields
- Returns updated chapter dict

**`async chapter_delete(chapter_id: int) -> dict`**
- Delete chapter and all segments/translations (cascades)
- Returns `{"deleted": true, "id": chapter_id}`

**`async chapter_get_editor_data(chapter_id: int, target_language: str = "en") -> dict`**
- Get connected text view for the editor
- Returns:
  - `source_connected_text`: Full source text as prose
  - `translated_connected_text`: Full translation as prose
  - `segment_map`: Array of offset mappings for click-to-highlight
- Each segment_map entry:
  ```python
  {
      "segment_id": int,
      "source_start": int, "source_end": int,
      "translated_start": int, "translated_end": int,
      "type": str,  # narrative, dialogue, action, thought
      "speaker": str | None,
      "batch_id": int | None
  }
  ```

**Glossary methods:**

**`async glossary_list(project_id: int) -> list[dict]`**
- List all glossary entries for a project
- Ordered by `source_term`

**`async glossary_create(project_id: int, source_term: str, translated_term: str, **kwargs) -> dict`**
- Create glossary entry
- Optional kwargs: `term_type`, `notes`, `context`, `auto_detected`
- Returns entry dict

**`async glossary_update(entry_id: int, **kwargs) -> dict`**
- Update glossary entry fields

**`async glossary_delete(entry_id: int) -> dict`**
- Delete glossary entry
- Returns `{"deleted": true, "id": entry_id}`

**Persona methods:**

**`async persona_list(project_id: int) -> list[dict]`**
- List personas ordered by `appearance_count DESC`
- Returns persona dicts with all fields

**`async persona_create(project_id: int, name: str, **kwargs) -> dict`**
- Create character persona
- Optional kwargs: `aliases`, `personality`, `speech_style`, `formality_level`, `age_group`, `example_dialogues`, `notes`, `auto_detected`, `detection_confidence`, `source_chapter_id`
- Returns persona dict

**`async persona_update(persona_id: int, **kwargs) -> dict`**
- Update persona fields

**`async persona_delete(persona_id: int) -> dict`**
- Delete persona and all suggestions (cascades)
- Returns `{"deleted": true, "id": persona_id}`

**Pipeline methods:**

**`async pipeline_translate_chapter(chapter_id: int, target_language: str = "en", **kwargs) -> dict`**
- Start the translation pipeline
- Runs `run_translation_pipeline()` from `graph.py`
- Sends progress notifications via `send_progress` callback
- Returns:
  ```python
  {
      "success": true,
      "pipeline_run_id": int,
      "connected_translated_text": str,
      "segment_map": list[dict],
      "persona_suggestions": list[dict],
      "stats": {
          "segments": int,
          "batches": int,
          "total_tokens": int,
          "persona_suggestions": int,
          "review_iterations": int,
          "validation_attempts": int
      }
  }
  ```

**`async pipeline_cancel() -> dict`**
- Cancel running pipeline (TODO: not yet implemented)
- Returns `{"cancelled": true}`

**Export methods:**

**`async export_chapter_txt_handler(chapter_id: int, target_language: str = "en") -> dict`**
- Export chapter as plain text file
- Calls `export_service.export_chapter_txt()`
- Returns `{"path": str, "format": "txt", "size": int}`

**`async export_chapter_docx_handler(chapter_id: int, target_language: str = "en") -> dict`**
- Export chapter as DOCX file
- Calls `export_service.export_chapter_docx()`
- Returns `{"path": str, "format": "docx"}`

**Segment methods:**

**`async segment_update_translation(segment_id: int, translated_text: str, target_language: str = "en") -> dict`**
- Update a segment's translation text directly
- Sets `manually_edited = True` to protect from re-translation
- Raises `ValueError` if translation not found
- Returns `{"updated": true, "segment_id": int}`

**Batch methods:**

**`async batch_get_reasoning(batch_id: int) -> dict`**
- Get Chain-of-Thought reasoning data for a translation batch
- Returns batch details if found: `{"found": true, "id": int, "situation_summary": str, "character_events": dict, "full_cot_json": dict, "segment_ids": list, "review_feedback": dict, "review_iteration": int}`
- Returns `{"found": false}` if batch not found

**Method registry:**

**`get_all_handlers() -> dict[str, Any]`**
- Returns dict mapping method names to handler functions
- Called by `JsonRpcServer.run()` during startup
- 29 methods total organized by domain:
  - Health: `health.check`
  - Config: `config.set_keys`, `config.get_keys`, `config.test_provider`
  - Projects: `project.list`, `project.create`, `project.get`, `project.update`, `project.delete`
  - Chapters: `chapter.list`, `chapter.create`, `chapter.get`, `chapter.update`, `chapter.delete`, `chapter.get_editor_data`
  - Glossary: `glossary.list`, `glossary.create`, `glossary.update`, `glossary.delete`
  - Personas: `persona.list`, `persona.create`, `persona.update`, `persona.delete`
  - Pipeline: `pipeline.translate_chapter`, `pipeline.cancel`
  - Segments: `segment.update_translation`
  - Batches: `batch.get_reasoning`
  - Export: `export.chapter_txt`, `export.chapter_docx`

### 2. Database Layer (`db/`)

#### `models.py` — 10 Tables

All models inherit from `Base(DeclarativeBase)` and use SQLAlchemy 2.0 `Mapped` types for type safety.

**Enums:**

**`TranslationStatus(str, enum.Enum)`**
- `PENDING`: Not yet translated
- `TRANSLATING`: Translation in progress
- `TRANSLATED`: Translation complete
- `REVIEWED`: Passed quality review
- `APPROVED`: User approved

**`PipelineStatus(str, enum.Enum)`**
- `PENDING`: Pipeline not started
- `RUNNING`: Pipeline in progress
- `COMPLETED`: Pipeline finished successfully
- `FAILED`: Pipeline encountered error
- `CANCELLED`: User cancelled

**Tables:**

**1. `Project`**

A translation project (e.g., a novel).

Fields:
- `id: int` (PK)
- `name: str(255)` — Project title
- `description: str | None` (Text) — Optional description
- `source_language: str(10)` — Default `"ko"` (Korean)
- `target_language: str(10) | None` — Default `"en"` (English)
- `genre: str(50) | None` — e.g., "fantasy", "romance"
- `style_settings: dict | None` (JSON) — Custom translation style preferences
- `pipeline_type: str(30)` — Default `"cot_batch"` (Chain-of-Thought batch)
- `llm_provider: str(20)` — Default `"gemini"` (`"claude"`, `"openai"`)
- `created_at: datetime` — Auto-set on insert
- `updated_at: datetime` — Auto-updated on change

Relationships:
- `chapters: List[Chapter]` — One-to-many (cascade delete)
- `glossary_entries: List[GlossaryEntry]` — One-to-many (cascade delete)
- `personas: List[Persona]` — One-to-many (cascade delete)
- `exports: List[Export]` — One-to-many (cascade delete)

**2. `Chapter`**

A chapter within a project.

Fields:
- `id: int` (PK)
- `project_id: int` (FK → `projects.id`, cascade delete)
- `title: str(255)` — Chapter title
- `order: int` — Display order (default 0)
- `source_content: str | None` (Text) — Original text
- `file_path: str(512) | None` — Optional file import path
- `translated_content: str | None` (Text) — Cached connected prose for export
- `translation_stale: bool` — Default `True`; set `False` after finalize
- `created_at: datetime`
- `updated_at: datetime`

Relationships:
- `project: Project` — Many-to-one
- `segments: List[Segment]` — One-to-many (cascade delete)
- `translation_batches: List[TranslationBatch]` — One-to-many (cascade delete)
- `pipeline_runs: List[PipelineRun]` — One-to-many (cascade delete)
- `exports: List[Export]` — One-to-many (cascade delete)
- `personas_last_seen: List[Persona]` — Personas last seen in this chapter

**3. `Segment`**

A translatable unit (sentence, paragraph, dialogue line).

Fields:
- `id: int` (PK)
- `chapter_id: int` (FK → `chapters.id`, cascade delete)
- `order: int` — Segment sequence number
- `source_text: str` (Text, required) — Original segment text
- `source_start_offset: int | None` — Character offset in `chapter.source_content`
- `source_end_offset: int | None` — End offset
- `translated_text: str | None` (Text) — **Legacy field** (v1 compatibility)
- `status: TranslationStatus` — Default `PENDING` (**legacy**)
- `speaker: str(100) | None` — Detected speaker for dialogue
- `segment_type: str(50)` — Default `"narrative"` (`"dialogue"`, `"action"`, `"thought"`)
- `extra_data: dict | None` (JSON) — Extensible metadata
- `created_at: datetime`
- `updated_at: datetime`

Indexes:
- `ix_segments_chapter_order` on `(chapter_id, order)`

Relationships:
- `chapter: Chapter` — Many-to-one
- `translations: List[Translation]` — One-to-many (cascade delete)

**4. `Translation`**

Per-language translation for each segment (v2.0 multi-language support).

Fields:
- `id: int` (PK)
- `segment_id: int` (FK → `segments.id`, cascade delete)
- `target_language: str(10)` — e.g., `"en"`, `"ja"`, `"zh"`
- `translated_text: str | None` (Text) — Translated segment
- `translated_start_offset: int | None` — Offset in connected translated text
- `translated_end_offset: int | None` — End offset
- `manually_edited: bool` — Default `False`; protect from re-translation if `True`
- `status: TranslationStatus` — Default `PENDING`
- `batch_id: int | None` (FK → `translation_batches.id`, set null on delete)
- `created_at: datetime`
- `updated_at: datetime`

Constraints:
- Unique: `(segment_id, target_language)`

Indexes:
- `ix_translations_segment_lang` on `(segment_id, target_language)`

Relationships:
- `segment: Segment` — Many-to-one
- `batch: TranslationBatch | None` — Many-to-one

**5. `TranslationBatch`**

Stores batch CoT reasoning and review feedback.

Fields:
- `id: int` (PK)
- `chapter_id: int` (FK → `chapters.id`, cascade delete)
- `target_language: str(10)` — Target language
- `batch_order: int` — Sequence number within chapter
- `situation_summary: str | None` (Text) — LLM's context summary
- `character_events: dict | None` (JSON) — Character actions/emotions
- `full_cot_json: dict | None` (JSON) — Complete CoT reasoning
- `segment_ids: list | None` (JSON) — Array of segment IDs in this batch
- `review_feedback: dict | None` (JSON) — Reviewer agent feedback
- `review_iteration: int` — Default 0; incremented on re-translation
- `created_at: datetime`

Relationships:
- `chapter: Chapter` — Many-to-one
- `translations: List[Translation]` — One-to-many
- `persona_suggestions: List[PersonaSuggestion]` — One-to-many

**6. `GlossaryEntry`**

Terminology glossary for consistent translation.

Fields:
- `id: int` (PK)
- `project_id: int` (FK → `projects.id`, cascade delete)
- `source_term: str(255)` — Original term
- `translated_term: str(255)` — Preferred translation
- `term_type: str(50)` — Default `"general"` (`"name"`, `"place"`, `"item"`, etc.)
- `notes: str | None` (Text) — Usage notes
- `context: str | None` (Text) — Example context
- `auto_detected: bool` — Default `False`; `True` if discovered by pipeline
- `created_at: datetime`

Indexes:
- `ix_glossary_project_term` on `(project_id, source_term)`

Relationships:
- `project: Project` — Many-to-one

**7. `Persona`**

Character persona for consistent voice in dialogue translation.

Fields:
- `id: int` (PK)
- `project_id: int` (FK → `projects.id`, cascade delete)
- `name: str(255)` — Character name
- `aliases: list | None` (JSON) — Alternative names
- `personality: str | None` (Text) — Personality description
- `speech_style: str | None` (Text) — How they speak
- `formality_level: int` — Default 3 (1=very casual, 5=very formal)
- `age_group: str(50) | None` — e.g., `"child"`, `"adult"`, `"elderly"`
- `example_dialogues: list | None` (JSON) — Sample lines
- `notes: str | None` (Text) — Additional context
- `auto_detected: bool` — Default `False`
- `detection_confidence: float | None` — LLM confidence score
- `source_chapter_id: int | None` (FK → `chapters.id`, set null on delete) — First appearance
- `appearance_count: int` — Default 0; incremented on each appearance
- `last_seen_chapter_id: int | None` (FK → `chapters.id`, set null on delete) — Latest appearance
- `created_at: datetime`
- `updated_at: datetime`

Relationships:
- `project: Project` — Many-to-one
- `suggestions: List[PersonaSuggestion]` — One-to-many (cascade delete)
- `source_chapter: Chapter | None` — Many-to-one
- `last_seen_chapter: Chapter | None` — Many-to-one

**8. `PersonaSuggestion`**

LLM-suggested persona updates awaiting approval.

Fields:
- `id: int` (PK)
- `persona_id: int` (FK → `personas.id`, cascade delete)
- `field_name: str(50)` — Field to update (e.g., `"personality"`, `"speech_style"`)
- `suggested_value: str | None` (Text) — Proposed new value
- `confidence: float | None` — LLM confidence (0.0-1.0)
- `source_batch_id: int | None` (FK → `translation_batches.id`, set null on delete)
- `status: str(20)` — Default `"pending"` (`"approved"`, `"rejected"`)
- `created_at: datetime`

Relationships:
- `persona: Persona` — Many-to-one
- `source_batch: TranslationBatch | None` — Many-to-one

**9. `PipelineRun`**

Audit trail for pipeline executions.

Fields:
- `id: int` (PK)
- `chapter_id: int` (FK → `chapters.id`, cascade delete)
- `target_language: str(10)` — Target language
- `status: PipelineStatus` — Default `PENDING`
- `started_at: datetime | None` — Pipeline start time
- `completed_at: datetime | None` — Pipeline end time
- `error_message: str | None` (Text) — Error details if failed
- `config: dict | None` (JSON) — Pipeline configuration snapshot
- `stats: dict | None` (JSON) — Execution statistics:
  ```python
  {
      "segments": int,
      "batches": int,
      "total_tokens": int,
      "persona_suggestions": int,
      "review_iterations": int,
      "validation_attempts": int
  }
  ```
- `created_at: datetime`

Indexes:
- `ix_pipeline_runs_chapter_status` on `(chapter_id, status)`

Relationships:
- `chapter: Chapter` — Many-to-one

**10. `Export`**

Tracks exported files.

Fields:
- `id: int` (PK)
- `chapter_id: int` (FK → `chapters.id`, cascade delete)
- `project_id: int` (FK → `projects.id`, cascade delete)
- `format: str(10)` — e.g., `"txt"`, `"docx"`
- `file_path: str(512)` — Full path to exported file
- `created_at: datetime`

Indexes:
- `ix_exports_chapter_format` on `(chapter_id, format)`

Relationships:
- `chapter: Chapter` — Many-to-one
- `project: Project` — Many-to-one

#### `session.py` — Connection Management

**`get_db_path() -> str`**
- Returns path to SQLite database file
- Default: `~/.fiction-translator/data.db`
- Creates parent directory if missing
- Override with env var `FT_DATABASE_PATH`

**`get_engine() -> Engine`**
- Get or create the global SQLAlchemy engine
- Singleton pattern (cached in `_engine`)
- Connection args: `check_same_thread=False` (allow multi-thread access)
- `echo=False` (disable SQL logging)

**`get_session_factory() -> sessionmaker`**
- Get or create the session factory
- Singleton pattern (cached in `_SessionLocal`)
- Config: `autocommit=False, autoflush=False`

**`get_db() -> Session`**
- Create a new database session
- **Caller must close** the session after use
- Pattern:
  ```python
  db = get_db()
  try:
      # ... query/modify ...
  finally:
      db.close()
  ```

**`init_db()`**
- Create all tables if they don't exist
- Called once during `main()` startup
- Uses `Base.metadata.create_all()`

### 3. Services Layer (`services/`)

Service functions provide business logic on top of raw ORM queries.

#### `project_service.py`

**`list_projects(db: Session) -> list[dict]`**
- List all projects with chapter counts
- Ordered by `updated_at DESC`
- Returns:
  ```python
  [{
      "id": int,
      "name": str,
      "description": str | None,
      "source_language": str,
      "target_language": str,
      "genre": str | None,
      "pipeline_type": str,
      "llm_provider": str,
      "created_at": str (ISO),
      "updated_at": str (ISO),
      "chapter_count": int
  }]
  ```

**`create_project(db: Session, name: str, source_language: str = "ko", target_language: str = "en", **kwargs) -> dict`**
- Create a new project
- Optional kwargs: `description`, `genre`, `style_settings`, `pipeline_type`, `llm_provider`
- Commits and returns project dict

**`get_project(db: Session, project_id: int) -> dict`**
- Get a single project
- Raises `ValueError` if not found
- Returns project dict

**`update_project(db: Session, project_id: int, **kwargs) -> dict`**
- Update project fields (except `id`)
- Commits and returns updated dict

**`delete_project(db: Session, project_id: int) -> dict`**
- Delete project (cascades to all chapters/segments/translations/glossary/personas)
- Commits and returns `{"deleted": True, "id": project_id}`

**`_project_to_dict(p: Project) -> dict`**
- Convert `Project` model to dict
- ISO-format datetime fields

#### `chapter_service.py`

**`list_chapters(db: Session, project_id: int) -> list[dict]`**
- List chapters in a project
- Includes `segment_count` and `translated_count` (non-pending translations)
- Ordered by `order`

**`create_chapter(db: Session, project_id: int, title: str, source_content: str = "", **kwargs) -> dict`**
- Create a new chapter
- Auto-assigns next `order` number
- Optional kwargs: `file_path`
- Commits and returns chapter dict

**`get_chapter(db: Session, chapter_id: int) -> dict`**
- Get a single chapter
- Raises `ValueError` if not found

**`update_chapter(db: Session, chapter_id: int, **kwargs) -> dict`**
- Update chapter fields
- Commits and returns updated dict

**`delete_chapter(db: Session, chapter_id: int) -> dict`**
- Delete chapter (cascades to segments/translations)
- Returns `{"deleted": True, "id": chapter_id}`

**`get_editor_data(db: Session, chapter_id: int, target_language: str = "en") -> dict`**
- Build connected text view for editor
- Joins segments with translations
- Computes character offsets for click-to-highlight
- Returns:
  ```python
  {
      "source_connected_text": str,
      "translated_connected_text": str,
      "segment_map": [
          {
              "segment_id": int,
              "source_start": int, "source_end": int,
              "translated_start": int, "translated_end": int,
              "type": str,
              "speaker": str | None,
              "batch_id": int | None
          }
      ]
  }
  ```
- If no segments, returns `source_connected_text` from `chapter.source_content`

**`_chapter_to_dict(ch: Chapter) -> dict`**
- Convert `Chapter` model to dict
- ISO-format datetime fields

#### `glossary_service.py`

**`list_glossary(db: Session, project_id: int) -> list[dict]`**
- List glossary entries ordered by `source_term`

**`create_glossary_entry(db: Session, project_id: int, source_term: str, translated_term: str, **kwargs) -> dict`**
- Create glossary entry
- Optional kwargs: `term_type`, `notes`, `context`, `auto_detected`
- Commits and returns entry dict

**`get_glossary_entry(db: Session, entry_id: int) -> dict`**
- Get a single entry
- Raises `ValueError` if not found

**`update_glossary_entry(db: Session, entry_id: int, **kwargs) -> dict`**
- Update entry fields
- Commits and returns updated dict

**`delete_glossary_entry(db: Session, entry_id: int) -> dict`**
- Delete entry
- Returns `{"deleted": True, "id": entry_id}`

**`get_glossary_map(db: Session, project_id: int) -> dict[str, str]`**
- Get glossary as `{source_term: translated_term}` mapping
- Used by translation prompts

**`bulk_import(db: Session, project_id: int, entries: list[dict]) -> dict`**
- Import multiple entries
- Each entry: `{"source_term": str, "translated_term": str, ...}`
- Returns `{"imported": count}`

**`_entry_to_dict(e: GlossaryEntry) -> dict`**
- Convert model to dict

#### `persona_service.py`

**`list_personas(db: Session, project_id: int) -> list[dict]`**
- List personas ordered by `appearance_count DESC`

**`create_persona(db: Session, project_id: int, name: str, **kwargs) -> dict`**
- Create persona
- Optional kwargs: `aliases`, `personality`, `speech_style`, `formality_level`, `age_group`, `example_dialogues`, `notes`, `auto_detected`, `detection_confidence`, `source_chapter_id`
- Commits and returns persona dict

**`get_persona(db: Session, persona_id: int) -> dict`**
- Get a single persona

**`update_persona(db: Session, persona_id: int, **kwargs) -> dict`**
- Update persona fields

**`delete_persona(db: Session, persona_id: int) -> dict`**
- Delete persona and all suggestions (cascades)

**`get_personas_context(db: Session, project_id: int) -> str`**
- Generate markdown persona context for translation prompts
- Format:
  ```markdown
  ## Character Voice Guide

  ### Alice (also: Ally)
  - Personality: Brave, curious
  - Speech style: Direct, informal
  - Formality: casual
  - Age group: young adult
  ```

**`list_suggestions(db: Session, persona_id: int) -> list[dict]`**
- List pending suggestions for a persona

**`apply_suggestion(db: Session, suggestion_id: int, approve: bool = True) -> dict`**
- Approve or reject a suggestion
- If approved, updates the persona field
- Handles list fields (aliases, example_dialogues) by appending
- Handles string fields by appending with "; " separator
- Commits and returns `{"id": suggestion_id, "status": "approved"/"rejected"}`

**`increment_appearance(db: Session, persona_id: int, chapter_id: int)`**
- Increment `appearance_count`
- Update `last_seen_chapter_id`
- Commits

**`_persona_to_dict(p: Persona) -> dict`**
- Convert model to dict

#### `export_service.py`

**`export_chapter_txt(db: Session, chapter_id: int, target_language: str = "en") -> dict`**
- Export chapter as plain text
- Joins segments with translations
- Saves to `~/.fiction-translator/exports/{title}_{lang}_{timestamp}.txt`
- Records export in `Export` table
- Returns `{"path": str, "format": "txt", "size": int}`

**`export_chapter_docx(db: Session, chapter_id: int, target_language: str = "en") -> dict`**
- Export chapter as DOCX (requires `python-docx`)
- Adds chapter title as heading
- Formats dialogue with speaker labels
- Saves to `~/.fiction-translator/exports/{title}_{lang}_{timestamp}.docx`
- Records export
- Returns `{"path": str, "format": "docx"}`

**`list_exports(db: Session, project_id: int) -> list[dict]`**
- List exports ordered by `created_at DESC`

**`delete_export(db: Session, export_id: int) -> dict`**
- Delete export record
- Optionally deletes physical file
- Returns `{"deleted": True, "id": export_id, "file_deleted": bool}`

### 4. Pipeline Layer (`pipeline/`)

#### `state.py` — Pipeline State

Defines TypedDicts for LangGraph state management. All use `total=False` so nodes can return partial updates.

**`SegmentData(TypedDict, total=False)`**
- `id: int | None` — DB ID once saved
- `order: int` — Sequence number
- `text: str` — Segment text
- `type: str` — `"narrative"`, `"dialogue"`, `"action"`, `"thought"`
- `speaker: str | None` — Speaker name for dialogue
- `source_start_offset: int` — Character offset in source
- `source_end_offset: int` — End offset

**`TranslatedSegment(TypedDict, total=False)`**
- `segment_id: int` — Order/ID
- `order: int` — Sequence number
- `source_text: str` — Original text
- `translated_text: str` — Translation
- `type: str` — Segment type
- `speaker: str | None`
- `translated_start_offset: int` — Offset in connected translation
- `translated_end_offset: int`
- `batch_id: int | None` — Associated batch

**`BatchData(TypedDict, total=False)`**
- `batch_order: int` — Batch sequence
- `segment_ids: list[int]` — IDs in this batch
- `situation_summary: str` — CoT context summary
- `character_events: list[dict]` — Character actions/emotions
- `translations: list[dict]` — `[{"segment_id": int, "text": str}]`
- `review_feedback: list[dict] | None` — Reviewer comments
- `review_iteration: int` — Re-translation count

**`TranslationState(TypedDict, total=False)`**

Full pipeline state (50+ fields organized by category):

**Input:**
- `chapter_id: int`
- `project_id: int`
- `source_text: str`
- `source_language: str`
- `target_language: str`
- `llm_provider: str`
- `api_keys: dict[str, str]`

**Context (loaded from DB):**
- `glossary: dict[str, str]` — Term mappings
- `personas_context: str` — Markdown persona guide
- `style_context: str` — Style preferences
- `existing_personas: list[dict]` — Known personas

**Segmentation:**
- `segments: list[SegmentData]`

**Character extraction:**
- `detected_characters: list[dict]`

**Validation:**
- `validation_passed: bool`
- `validation_errors: list[str]`
- `validation_attempts: int`

**Translation:**
- `batches: list[BatchData]`
- `translated_segments: list[TranslatedSegment]`

**Review:**
- `review_passed: bool`
- `review_feedback: list[dict]`
- `review_iteration: int`
- `flagged_segments: list[int]` — IDs needing re-translation

**Persona learning:**
- `persona_suggestions: list[dict]`

**Output:**
- `connected_translated_text: str` — Final prose
- `segment_map: list[dict]` — Offset mappings

**Pipeline metadata:**
- `pipeline_run_id: int | None`
- `progress_callback: Any` — Async callable
- `error: str | None`
- `total_tokens: int`
- `total_cost: float`

#### `graph.py` — Pipeline Definition

**`build_translation_graph() -> StateGraph`**

Constructs the LangGraph pipeline. Nodes and edges define the workflow.

**Pipeline flow:**
```
load_context → segment → extract_characters → validate
    ↓ validation_passed?
    YES → translate
    NO, attempts < 3 → segment (retry)
    NO, attempts >= 3 → translate (proceed anyway)

translate → review
    ↓ review_passed?
    YES → learn_personas
    NO, iteration < 2 → translate (re-translate flagged)
    NO, iteration >= 2 → learn_personas (proceed)

learn_personas → finalize → END
```

**Nodes:**

**`async load_context_node(state: TranslationState) -> dict`**
- Load glossary, personas, and settings from DB
- Returns `{"glossary": dict, "personas_context": str, "existing_personas": list}`

**`segmenter_node(state: TranslationState) -> dict`**
- Implemented in `nodes/segmenter.py`
- Returns `{"segments": list[SegmentData]}`

**`character_extractor_node(state: TranslationState) -> dict`**
- Implemented in `nodes/character_extractor.py`
- Returns `{"detected_characters": list[dict]}`

**`validator_node(state: TranslationState) -> dict`**
- Implemented in `nodes/validator.py`
- Returns `{"validation_passed": bool, "validation_errors": list, "validation_attempts": int}`

**`translator_node(state: TranslationState) -> dict`**
- Implemented in `nodes/translator.py`
- Returns `{"batches": list[BatchData], "translated_segments": list[TranslatedSegment]}`

**`reviewer_node(state: TranslationState) -> dict`**
- Implemented in `nodes/reviewer.py`
- Returns `{"review_passed": bool, "review_feedback": list, "review_iteration": int, "flagged_segments": list}`

**`persona_learner_node(state: TranslationState) -> dict`**
- Implemented in `nodes/persona_learner.py`
- Returns `{"persona_suggestions": list[dict]}`

**`async finalize_node(state: TranslationState) -> dict`**
- Join translated segments into connected prose
- Compute translated offsets for segment_map
- Persist to DB:
  - Save connected text to `chapter.translated_content`
  - Clear old segments/translations for this chapter
  - Save new segments with offsets
  - Save translations with offsets
  - Save batches
  - Save persona suggestions
  - Commit
- Returns `{"connected_translated_text": str, "segment_map": list[dict]}`

**Edges:**

Linear edges:
- `load_context → segment`
- `segment → extract_characters`
- `extract_characters → validate`
- `translate → review`
- `learn_personas → finalize`
- `finalize → END`

Conditional edges (defined in `edges.py`):
- `validate → should_re_segment → {"translate", "segment"}`
- `review → should_re_translate → {"learn", "translate"}`

**`get_translation_graph() -> CompiledGraph`**
- Returns compiled graph singleton (cached in `_compiled_graph`)
- Lazy initialization on first call

**`async run_translation_pipeline(db, chapter_id: int, target_language: str = "en", api_keys: dict | None = None, progress_callback=None, **kwargs) -> dict`**

High-level entry point for translation.

**Steps:**
1. Load chapter and project from DB
2. Create `PipelineRun` record with status `RUNNING`
3. Build initial state with input params
4. Invoke graph with `await graph.ainvoke(initial_state)`
5. On success:
   - Update `PipelineRun` to `COMPLETED`
   - Save stats
   - Return result
6. On failure:
   - Update `PipelineRun` to `FAILED`
   - Save error message
   - Re-raise exception

**Returns:**
```python
{
    "success": True,
    "pipeline_run_id": int,
    "connected_translated_text": str,
    "segment_map": list[dict],
    "persona_suggestions": list[dict],
    "stats": {
        "segments": int,
        "batches": int,
        "total_tokens": int,
        "persona_suggestions": int,
        "review_iterations": int,
        "validation_attempts": int
    }
}
```

#### `edges.py` — Conditional Routing

**`should_re_segment(state: TranslationState) -> str`**
- Called after validation
- Returns `"translate"` if validation passed OR max attempts reached (3)
- Returns `"segment"` if validation failed and attempts < 3

**`should_re_translate(state: TranslationState) -> str`**
- Called after review
- Returns `"learn"` if review passed OR max iterations reached (2)
- Returns `"translate"` if review flagged segments and iterations < 2

#### `callbacks.py` — Progress Helpers

**`PIPELINE_STAGES: list[str]`**
- `["load_context", "segmentation", "character_extraction", "validation", "translation", "review", "persona_learning", "finalize"]`

**`stage_progress(stage: str) -> float`**
- Get overall progress (0.0-1.0) for a given stage
- Example: `"validation"` → 0.5 (halfway through 8 stages)

**`async notify(callback: Any, stage: str, pct: float, message: str) -> None`**
- Safely invoke progress callback if present
- Swallows callback exceptions to prevent pipeline breakage

#### `nodes/` — Pipeline Node Implementations

**`segmenter.py`**

**`async segmenter_node(state: TranslationState) -> dict`**

Segments source text into translatable units with character offsets.

**Approach:**
1. **Rule-based segmentation** (always runs):
   - Split on paragraph boundaries (double newline)
   - Detect dialogue with language-specific regex patterns
   - Extract speakers from dialogue markers
   - Compute character offsets for each segment

2. **LLM refinement** (optional, for texts < 10,000 chars):
   - Send text to LLM with segmentation prompt
   - Parse JSON response into segments
   - Locate each segment's text in source to compute offsets

**Language support:**
- Korean: `"..."`, `「...」` dialogue markers; speaker patterns like `"라고 Alice"`, `Alice가 말했다`
- Japanese: `「...」`, `『...』` brackets; speaker patterns like `」とAlice`, `Aliceは言った`
- Chinese: `"..."` quotes; speaker patterns like `"Alice说`, `Alice说："`
- English: `"..."`, `'...'` quotes; speaker patterns like `said Alice`, `Alice said:`

**Segment types:**
- `narrative`: Default prose
- `dialogue`: Quoted speech
- `action`: Not currently auto-detected (future)
- `thought`: Internal monologue in parentheses or single quotes

**Returns:**
```python
{
    "segments": [
        {
            "id": None,
            "order": 0,
            "text": "She walked into the room.",
            "type": "narrative",
            "speaker": None,
            "source_start_offset": 0,
            "source_end_offset": 27
        },
        {
            "id": None,
            "order": 1,
            "text": "\"Hello,\" she said softly.",
            "type": "dialogue",
            "speaker": "she",
            "source_start_offset": 28,
            "source_end_offset": 53
        }
    ]
}
```

**`character_extractor.py`**

**`async character_extractor_node(state: TranslationState) -> dict`**

Extracts characters using regex + optional LLM analysis.

**Approach:**
1. **Pattern-based extraction**:
   - Scan dialogue segments for speaker names
   - Use segment's `speaker` field if already set
   - Apply language-specific speaker detection patterns
   - Count occurrences in `Counter`

2. **LLM-based extraction** (optional, if API keys available):
   - Concatenate all segment texts (cap at 8000 chars)
   - Send to LLM with character extraction prompt
   - Parse JSON: `{"characters": [{"name": str, "role": str, "personality_hints": str, ...}]}`
   - Merge with regex results (LLM takes precedence)

3. **Merge with existing personas**:
   - Match detected names against DB personas by name or alias
   - Add `persona_id` and `canonical_name` if matched

**Returns:**
```python
{
    "detected_characters": [
        {
            "name": "Alice",
            "aliases": ["Ally"],
            "role": "main",
            "speaking_lines": 15,
            "personality_hints": "Curious, brave",
            "speech_style_hints": "Direct, informal",
            "source": "llm",
            "persona_id": 42,
            "canonical_name": "Alice"
        }
    ]
}
```

**`validator.py`**

**`async validator_node(state: TranslationState) -> dict`**

Validates segmentation quality with 7 checks.

**Validation rules:**
1. **Non-empty**: Must have at least one segment
2. **No empty segments**: Every segment has non-empty text
3. **No oversized segments**: Max 10,000 chars per segment
4. **Valid offsets**: Non-negative, end >= start, monotonically increasing
5. **Coverage**: Segments cover at least 80% of source text
6. **Valid types**: Type in `{"narrative", "dialogue", "action", "thought"}`
7. **Speaker detection** (warning only): Dialogue segments should ideally have speakers

**Returns:**
```python
{
    "validation_passed": True,
    "validation_errors": [],
    "validation_attempts": 1
}
```

If validation fails, pipeline loops back to `segmenter_node` (up to 3 attempts).

**`translator.py`**

**`async translator_node(state: TranslationState) -> dict`**

Translates segments in batches using Chain-of-Thought reasoning.

**Batch grouping:**
- Max 20,000 chars per batch
- Max 10 segments per batch
- Keep dialogue exchanges together when possible

**Translation process:**
1. Decide which segments to translate:
   - Full translation: all segments
   - Re-translation loop: only `flagged_segments`
2. Group segments into batches
3. For each batch:
   - Build CoT translation prompt with glossary, personas, style context
   - Include review feedback if re-translating
   - Send to LLM via `generate_json()`
   - Parse CoT response:
     ```python
     {
         "situation_summary": str,
         "character_events": [{"character": str, "emotion": str, "action": str}],
         "translations": [{"segment_id": int, "text": str}]
     }
     ```
   - Create `TranslatedSegment` entries
   - Store `BatchData`

**On re-translation:**
- Merge new translations with previous translations
- Only replace the flagged segments
- Preserve all other segments from previous iteration

**Returns:**
```python
{
    "batches": [BatchData, ...],
    "translated_segments": [TranslatedSegment, ...],
    "total_tokens": int,
    "total_cost": float
}
```

**`reviewer.py`**

**`async reviewer_node(state: TranslationState) -> dict`**

Reviews translations for quality and flags segments for re-translation.

**Review process:**
1. Build source/translation pairs
2. Chunk pairs (max 30 per LLM call to avoid token limits)
3. For each chunk:
   - Send review prompt with pairs, glossary, personas
   - Parse JSON response:
     ```python
     {
         "overall_passed": bool,
         "segment_reviews": [
             {
                 "segment_id": int,
                 "verdict": "pass" | "flag",
                 "issue": str,
                 "suggestion": str
             }
         ]
     }
     ```
4. Collect all flagged segment IDs
5. Build feedback list for flagged segments

**Returns:**
```python
{
    "review_passed": True,  # False if any segments flagged
    "review_feedback": [
        {
            "segment_id": 5,
            "issue": "Missed glossary term",
            "suggestion": "Use 'magic sword' instead of 'sword'"
        }
    ],
    "review_iteration": 1,
    "flagged_segments": [5, 12]
}
```

If `review_passed=False` and `review_iteration < 2`, pipeline loops back to `translator_node`.

**`persona_learner.py`**

**`async persona_learner_node(state: TranslationState) -> dict`**

Extracts character insights from translations for persona updates.

**Learning process:**
1. Join translated segments into connected text
2. Send to LLM with persona analysis prompt
3. Parse JSON response:
   ```python
   {
       "persona_updates": [
           {
               "name": str,
               "field": str,  # "personality", "speech_style", "formality_level", "aliases"
               "value": str,
               "confidence": float,
               "evidence": str
           }
       ]
   }
   ```
4. Filter suggestions:
   - Valid fields only
   - Confidence >= 0.3
   - Match to existing persona if possible

**Returns:**
```python
{
    "persona_suggestions": [
        {
            "name": "Alice",
            "persona_id": 42,
            "field": "speech_style",
            "value": "Uses short sentences, avoids contractions",
            "confidence": 0.85,
            "evidence": "Observed across 12 dialogue segments"
        }
    ]
}
```

Suggestions are saved to `PersonaSuggestion` table in `finalize_node` for user review.

### 5. LLM Layer (`llm/`)

#### `providers.py` — Provider Abstraction

**`LLMResponse` (dataclass)**
- `text: str` — Generated text
- `model: str` — Model ID used
- `usage: dict` — Token counts (`{"prompt_tokens": int, "completion_tokens": int}`)
- `raw_response: Any | None` — Full API response for debugging

**`LLMProvider` (ABC)**

Abstract base class for LLM providers.

**`async generate(prompt: str, system_prompt: str | None = None, temperature: float = 0.3, max_tokens: int = 4096) -> LLMResponse`**
- Generate text completion
- Must be implemented by subclasses

**`async generate_json(prompt: str, system_prompt: str | None = None, temperature: float = 0.2, max_tokens: int = 4096) -> dict`**
- Generate and parse JSON response
- Appends "Respond with valid JSON only." to system prompt
- Strips markdown code blocks (````json ... ````)
- Raises `ValueError` if JSON parsing fails

**`is_available() -> bool`**
- Check if provider is configured (has API key)
- Must be implemented by subclasses

**`GeminiProvider(LLMProvider)`**

Google Gemini API provider.

**Constructor: `__init__(api_key: str, model: str = "gemini-2.0-flash")`**
- Default model: `gemini-2.0-flash` (fast, cheap)
- Alternative: `gemini-1.5-pro` (more capable)

**`async generate(...) -> LLMResponse`**
- Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}`
- Request format:
  ```python
  {
      "contents": [{"parts": [{"text": system_prompt}, {"text": prompt}]}],
      "generationConfig": {
          "temperature": float,
          "topP": 0.9,
          "maxOutputTokens": int
      }
  }
  ```
- Parses response: `data["candidates"][0]["content"]["parts"][0]["text"]`
- Extracts usage from `usageMetadata`

**`ClaudeProvider(LLMProvider)`**

Anthropic Claude API provider.

**Constructor: `__init__(api_key: str, model: str = "claude-sonnet-4-5-20250929")`**
- Default model: `claude-sonnet-4-5-20250929`
- Alternative: `claude-opus-4` (most capable)

**`async generate(...) -> LLMResponse`**
- Endpoint: `POST https://api.anthropic.com/v1/messages`
- Headers: `x-api-key`, `anthropic-version: 2023-06-01`
- Request format:
  ```python
  {
      "model": str,
      "max_tokens": int,
      "temperature": float,
      "messages": [{"role": "user", "content": prompt}],
      "system": system_prompt  # optional
  }
  ```
- Parses response: `data["content"][0]["text"]`

**`OpenAIProvider(LLMProvider)`**

OpenAI GPT API provider.

**Constructor: `__init__(api_key: str, model: str = "gpt-4o")`**
- Default model: `gpt-4o` (GPT-4 Omni)
- Alternative: `gpt-4-turbo`, `gpt-3.5-turbo`

**`async generate(...) -> LLMResponse`**
- Endpoint: `POST https://api.openai.com/v1/chat/completions`
- Headers: `Authorization: Bearer {api_key}`
- Request format:
  ```python
  {
      "model": str,
      "messages": [
          {"role": "system", "content": system_prompt},  # optional
          {"role": "user", "content": prompt}
      ],
      "temperature": float,
      "max_tokens": int
  }
  ```
- Parses response: `data["choices"][0]["message"]["content"]`

**Factory functions:**

**`get_llm_provider(provider_name: str = "gemini", api_keys: dict[str, str] | None = None, model: str | None = None) -> LLMProvider`**
- Create LLM provider instance
- `provider_name`: `"gemini"`, `"claude"`, `"openai"`
- `api_keys`: Maps provider names to API keys
  - Accepts aliases: `"google"` → `"gemini"`, `"anthropic"` → `"claude"`
- `model`: Optional model override
- Raises `ValueError` if provider unknown or API key missing

**`get_available_providers(api_keys: dict[str, str]) -> list[str]`**
- Return list of providers that have API keys configured
- Example: `["gemini", "openai"]`

**Provider registry:**
```python
PROVIDERS = {
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
}
```

#### `prompts/` — Prompt Builders

Each prompt builder constructs the system and user prompts for a specific pipeline stage. These are referenced by the pipeline nodes but the actual implementation details would be in separate files:

- `segmentation.py` — `build_segmentation_prompt()`
- `character_extraction.py` — `build_character_extraction_prompt()`
- `validation.py` — (Not needed; validation is deterministic)
- `cot_translation.py` — `build_cot_translation_prompt()`
- `review.py` — `build_review_prompt()`
- `persona_analysis.py` — `build_persona_analysis_prompt()`

## Data Flow

### Translation Pipeline Flow (End-to-End)

```
User clicks "Translate" in React UI
    ↓
api.translateChapter(chapterId, targetLanguage)
    ↓
Tauri invoke("rpc_call", {method: "pipeline.translate_chapter", params: {chapter_id: 123, target_language: "en"}})
    ↓
Rust sidecar.call("pipeline.translate_chapter", params)
    ↓
Python stdin receives JSON-RPC request
    ↓
JsonRpcServer parses request
    ↓
Dispatcher calls pipeline_translate_chapter(chapter_id=123, target_language="en")
    ↓
Handler opens DB session, calls run_translation_pipeline()
    ↓
run_translation_pipeline():
    1. Create PipelineRun record (status=RUNNING)
    2. Build initial state
    3. Invoke LangGraph:

       load_context:
           - Load glossary from DB
           - Load personas from DB
           - Return {"glossary": {...}, "personas_context": "...", "existing_personas": [...]}

       segment:
           - Rule-based: split on paragraphs, detect dialogue
           - Optional LLM refinement
           - Compute character offsets
           - Return {"segments": [...]}

       extract_characters:
           - Regex: extract speakers from dialogue
           - Optional LLM: deeper character analysis
           - Merge with existing personas
           - Return {"detected_characters": [...]}

       validate:
           - Check 7 validation rules
           - Return {"validation_passed": bool, "validation_errors": [...], "validation_attempts": 1}
           - If failed and attempts < 3 → loop to segment
           - Else → proceed to translate

       translate:
           - Group segments into batches (max 10 segments, 20k chars)
           - For each batch:
               * Build CoT prompt with glossary, personas, style
               * Call LLM generate_json()
               * Parse {"situation_summary": "...", "character_events": [...], "translations": [...]}
               * Create TranslatedSegment entries
           - Return {"batches": [...], "translated_segments": [...]}
           - Send progress notifications: await send_progress("translation", 0.5, "Translating batch 3/6...")

       review:
           - Build source/translation pairs
           - Chunk into groups of 30
           - For each chunk:
               * Build review prompt
               * Call LLM generate_json()
               * Parse {"overall_passed": bool, "segment_reviews": [...]}
           - Collect flagged segment IDs
           - Return {"review_passed": bool, "review_feedback": [...], "flagged_segments": [...]}
           - If review_passed=False and iteration < 2 → loop to translate (re-translate flagged only)
           - Else → proceed to learn_personas

       learn_personas:
           - Join translated segments into text
           - Build persona analysis prompt
           - Call LLM generate_json()
           - Parse {"persona_updates": [...]}
           - Filter and match to existing personas
           - Return {"persona_suggestions": [...]}

       finalize:
           - Join translated segments into connected prose
           - Compute translated offsets for segment_map
           - Save to DB:
               * chapter.translated_content = connected_text
               * Clear old segments/translations
               * Save new segments with source offsets
               * Save translations with translated offsets
               * Save batches
               * Save persona suggestions
           - Return {"connected_translated_text": "...", "segment_map": [...]}

    4. Update PipelineRun (status=COMPLETED, stats={...})
    5. Return result dict

    ↓
Handler closes DB session, returns result
    ↓
JsonRpcServer writes JSON-RPC response to stdout
    ↓
Rust receives response, deserializes
    ↓
Tauri resolve(result)
    ↓
React receives result, updates UI
```

**Progress notifications** (parallel stream):
```
Python: await send_progress("translation", 0.3, "Translating batch 2/6...")
    ↓
JsonRpcServer.send_notification("pipeline.progress", {stage: "translation", progress: 0.3, message: "..."})
    ↓
Python writes JSON-RPC notification to stdout
    ↓
Rust sidecar emits event
    ↓
Tauri listen("pipeline.progress")
    ↓
React updates progress bar
```

### CRUD Flow (Example: List Projects)

```
React: const projects = await api.listProjects()
    ↓
Tauri invoke("rpc_call", {method: "project.list", params: {}})
    ↓
Rust sidecar.call("project.list", {})
    ↓
Python stdin receives: {"jsonrpc": "2.0", "id": 1, "method": "project.list", "params": {}}
    ↓
JsonRpcServer parses → JsonRpcRequest
    ↓
Dispatcher: handler = handlers["project.list"] → project_list()
    ↓
project_list():
    db = get_db()
    try:
        list_projects(db) →
            db.query(Project).order_by(Project.updated_at.desc()).all()
            for each project:
                count chapters
                build dict
        return [project dicts]
    finally:
        db.close()
    ↓
Handler returns [{"id": 1, "name": "My Novel", ...}, ...]
    ↓
JsonRpcServer wraps in JsonRpcResponse: {"jsonrpc": "2.0", "id": 1, "result": [...]}
    ↓
Python writes to stdout
    ↓
Rust receives, deserializes
    ↓
Tauri resolve([...])
    ↓
React receives projects array, renders ProjectList
```

## Development Workflow

**Run sidecar standalone:**
```bash
cd sidecar
python -m fiction_translator
# Reads from stdin, writes to stdout
# Ctrl+D to close stdin and exit
```

**Test with curl + jq:**
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"health.check"}' | python -m fiction_translator | jq
```

**Run with Tauri app:**
```bash
cd .. # root of repo
npm run tauri dev
# Tauri spawns sidecar automatically
```

**Build standalone binary:**
```bash
cd sidecar
python build.py  # Uses PyInstaller
# Output: dist/fiction-translator-sidecar (or .exe on Windows)
```

**Database location:**
- Development: `~/.fiction-translator/data.db`
- Production: Same (user's home directory)
- Override: Set `FT_DATABASE_PATH` env var

**Logs:**
- Python logs to **stderr** (stdout reserved for IPC)
- View logs: `python -m fiction_translator 2>sidecar.log`
- Log level: Set in `main.py` (`logging.basicConfig(level=logging.INFO)`)

## Troubleshooting

**Sidecar won't start:**
- Check Tauri config: `src-tauri/tauri.conf.json` → `tauri.bundle.externalBin`
- Check file permissions: `chmod +x dist/fiction-translator-sidecar`
- Check logs: Tauri console shows stderr output

**Translation fails:**
- Check API keys: `config.test_provider` returns success?
- Check DB: Does chapter have `source_content`?
- Check logs: Look for Python exceptions in stderr

**Progress not updating:**
- Check `send_progress` callback is passed to `run_translation_pipeline`
- Check Tauri event listener: `listen("pipeline.progress", callback)`
- Check network: Notifications are fire-and-forget, no error if Tauri not listening

**Database corruption:**
- Backup: `cp ~/.fiction-translator/data.db ~/.fiction-translator/data.db.backup`
- Reset: `rm ~/.fiction-translator/data.db` (will recreate on next startup)
- Migrate: (Future) Use Alembic migrations

## Application Architecture Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri Desktop App                     │
│  ┌───────────────────────┐  ┌────────────────────────┐  │
│  │    React Frontend     │  │     Rust Shell         │  │
│  │  (Vite + TypeScript)  │  │   (Tauri v2 Core)     │  │
│  │                       │  │                        │  │
│  │  ┌─────────────────┐  │  │  ┌──────────────────┐  │  │
│  │  │  Pages:          │  │  │  │  Commands:        │  │  │
│  │  │  - ProjectList   │  │  │  │  - rpc_call       │  │  │
│  │  │  - EditorPage    │  │  │  │  - sidecar_status │  │  │
│  │  │  - SettingsPage  │  │  │  └──────────────────┘  │  │
│  │  └─────────────────┘  │  │  ┌──────────────────┐  │  │
│  │  ┌─────────────────┐  │  │  │  Sidecar Manager  │  │  │
│  │  │  Components:     │  │  │  │  - start/stop     │  │  │
│  │  │  - SegmentEditor │  │  │  │  - health check   │  │  │
│  │  │  - CoTPanel      │  │  │  │  - JSON-RPC call  │  │  │
│  │  │  - ExportButton  │  │  │  └──────────────────┘  │  │
│  │  └─────────────────┘  │  │           │              │  │
│  │  ┌─────────────────┐  │  │           │ stdin/stdout │  │
│  │  │  API Bridge      │──│──│───────────┘              │  │
│  │  │  (tauri-bridge)  │  │  │                        │  │
│  │  └─────────────────┘  │  │                        │  │
│  └───────────────────────┘  └────────────────────────┘  │
└─────────────────────────────┬───────────────────────────┘
                              │ JSON-RPC 2.0 (stdin/stdout)
┌─────────────────────────────┴───────────────────────────┐
│                   Python Sidecar                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │  IPC Layer (JsonRpcServer)                         │  │
│  │  29 methods: health, config, project, chapter,     │  │
│  │  glossary, persona, pipeline, segment, batch,      │  │
│  │  export                                            │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                 │
│  ┌──────────────────────┴─────────────────────────────┐  │
│  │  Services Layer                                     │  │
│  │  project / chapter / glossary / persona / export    │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                 │
│  ┌──────────────────────┴─────────────────────────────┐  │
│  │  Pipeline Layer (LangGraph)                         │  │
│  │                                                     │  │
│  │  load_context ──► segment ──► extract_characters    │  │
│  │       │                            │                │  │
│  │       │                      ┌─────▼──────┐         │  │
│  │       │                      │  validate   │         │  │
│  │       │                      └──┬─────┬───┘         │  │
│  │       │              retry ◄────┘     │ pass        │  │
│  │       │              (max 3)          ▼             │  │
│  │       │                         ┌──────────┐        │  │
│  │       │                         │ translate │        │  │
│  │       │                         └────┬─────┘        │  │
│  │       │                              ▼              │  │
│  │       │                         ┌──────────┐        │  │
│  │       │              retry ◄────┤  review  │        │  │
│  │       │              (max 2)    └────┬─────┘        │  │
│  │       │                              │ pass         │  │
│  │       │                              ▼              │  │
│  │       │                      learn_personas         │  │
│  │       │                              │              │  │
│  │       │                              ▼              │  │
│  │       │                         finalize ──► END    │  │
│  │       │                                             │  │
│  └───────┴─────────────────────────────────────────────┘  │
│                         │                                 │
│  ┌──────────────────────┴─────────────────────────────┐  │
│  │  LLM Layer                                          │  │
│  │  Gemini / Claude / OpenAI                           │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                 │
│  ┌──────────────────────┴─────────────────────────────┐  │
│  │  Database Layer (SQLAlchemy + SQLite)                │  │
│  │  10 tables: Project, Chapter, Segment, Translation, │  │
│  │  TranslationBatch, GlossaryEntry, Persona,          │  │
│  │  PersonaSuggestion, PipelineRun, Export              │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Changelog

### Session 2025-02-10

**Features wired (frontend ↔ backend):**

1. **Settings Page API Keys** — Wired `SettingsPage.tsx` to save/load/test API keys via `config.set_keys`, `config.get_keys`, `config.test_provider`. Added loading states and green indicator dots for configured providers.

2. **Segment Editing** — Added `segment.update_translation` RPC method + `updateSegmentTranslation()` in `tauri-bridge.ts`. Editor page `handleSegmentEdit` now persists edits to DB with `manually_edited=True` protection.

3. **Export Functionality** — Added `export.chapter_txt` and `export.chapter_docx` RPC methods + `exportChapterTxt()` / `exportChapterDocx()` in `tauri-bridge.ts`. Editor page export button triggers TXT download with loading state.

4. **CoT Reasoning Panel** — Added `batch.get_reasoning` RPC method + `getBatchReasoning()` in `tauri-bridge.ts`. `CoTReasoningPanel.tsx` now fetches real batch reasoning data (situation_summary, character_events, review_feedback) via `useQuery`.

**Bug fixes:**

5. **Rust Build Warnings** — Added `#[allow(dead_code)]` annotations to unused structs in `events.rs` and unused fields in `ipc.rs`.

6. **Sidecar Startup Fix** — Created `__main__.py` to enable `python -m fiction_translator` module execution. Without this file, the sidecar process couldn't start, causing a 120s health check timeout.

**Files modified:**
- `src/pages/SettingsPage.tsx` — API key save/load/test wiring
- `src/pages/EditorPage.tsx` — Segment edit + export wiring
- `src/components/editor/CoTReasoningPanel.tsx` — Real batch reasoning data
- `src/api/tauri-bridge.ts` — 4 new API methods
- `sidecar/src/fiction_translator/ipc/handlers.py` — 4 new RPC handlers
- `sidecar/src/fiction_translator/__main__.py` — NEW: module entry point
- `src-tauri/src/events.rs` — Dead code annotations
- `src-tauri/src/ipc.rs` — Dead code annotations

---

**End of English documentation.**
