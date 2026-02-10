# Fiction Translator v2.0 — React 프론트엔드 문서

## 개요

React 프론트엔드는 Tauri의 webview 내부에서 실행되며, 번역 프로젝트를 관리하고 번역을 편집하기 위한 현대적인 SaaS 스타일 인터페이스를 제공합니다. React 18, Vite, TypeScript, Tailwind CSS로 구축되었으며, Tauri IPC를 통한 JSON-RPC로 Python 사이드카 백엔드와 통신합니다.

## 아키텍처 선택 이유

### 왜 React + Vite인가? (Next.js나 다른 프레임워크가 아닌)

- **Tauri webview는 로컬 SPA를 실행** — 서버 사이드 렌더링이 필요 없고 불가능함
- **Vite는 즉각적인 HMR 제공** — 개발 중 1초 이내 새로고침
- **React 생태계의 성숙도** — 훌륭한 컴포넌트 라이브러리들 (Radix UI primitives)
- **TypeScript 우선** — API 경계에서 UI 컴포넌트까지 타입 안전성

### 왜 Zustand인가? (Redux나 Context가 아닌)

- **최소한의 보일러플레이트** — 스토어는 `create()`를 사용하는 단순한 함수
- **Provider가 필요 없음** — 어디서나 import하여 사용, 래핑 불필요
- **로컬 UI 상태에 완벽** — 선택된 세그먼트, 테마, 파이프라인 상태
- **React Query가 서버 상태 처리** — Zustand는 UI 상태만 관리 (관심사의 분리)

### 왜 React Query인가? (raw fetch나 SWR이 아닌)

- **자동 캐싱 및 재검증** — 뮤테이션 시 스마트 캐시 무효화
- **낙관적 업데이트가 있는 뮤테이션** — 즉각적인 UI 피드백, 오류 시 롤백
- **뮤테이션 시 쿼리 무효화** — 프로젝트 생성 후 목록이 자동으로 새로고침
- **로딩/에러 상태 내장** — `isLoading`, `isError`, `isPending` 기본 제공
- **백그라운드 재페칭** — 오래된 데이터가 백그라운드에서 업데이트됨

### 왜 CSS 변수 + Tailwind인가? (CSS-in-JS가 아닌)

- **CSS 변수로 테마 전환 가능** — 다크/라이트 모드를 JS 오버헤드 없이 구현
- **Tailwind는 유틸리티 우선 스타일링 제공** — 빠른 반복, 일관된 간격
- **런타임 CSS-in-JS 오버헤드 없음** — 모든 스타일이 정적이며 빌드 시 컴파일됨
- **Linear/Vercel 미학** — `globals.css`에서 세심한 변수 디자인을 통해 달성

### 왜 연결된 텍스트인가? (세그먼트별이 아닌)

- **사용자는 소설을 번역함** — 고립된 세그먼트가 아닌 연속된 문장을 봐야 함
- **세그먼트 수준 편집은 숨겨짐** — 클릭하면 강조, 더블클릭하면 인라인 편집
- **전문 번역가 워크플로우와 일치** — 맥락이 중요; 조각이 아닌 단락 단위로 번역
- **부드러운 읽기 경험** — 편집기가 스프레드시트가 아닌 책 읽기처럼 느껴짐

---

## 디렉토리 구조

```
src/
├── main.tsx                    # React 진입점 (ReactDOM.render)
├── App.tsx                     # 라우터 + React Query provider
├── api/                        # 백엔드 통신
│   ├── tauri-bridge.ts         # Tauri invoke 래퍼 + 이벤트 리스너
│   └── types.ts                # Python 스키마와 일치하는 TypeScript 인터페이스
├── stores/                     # Zustand 상태 (UI 전용)
│   ├── app-store.ts            # 테마, 사이드카 상태, 커맨드 바
│   ├── editor-store.ts         # 활성/편집 세그먼트, 세그먼트 맵
│   └── pipeline-store.ts       # 번역 진행 상황 (isRunning, stage, progress)
├── hooks/                      # React Query 훅 (서버 상태)
│   ├── useProject.ts           # 프로젝트 CRUD 쿼리/뮤테이션
│   ├── useChapter.ts           # 챕터 CRUD + 편집기 데이터
│   ├── useGlossary.ts          # 용어집 CRUD
│   ├── usePersonas.ts          # 페르소나 CRUD
│   ├── useTranslation.ts       # 번역 트리거 뮤테이션
│   ├── useProgress.ts          # 파이프라인 이벤트 리스너
│   └── useTheme.ts             # 테마 관리 (dark/light/system)
├── pages/                      # 라우트 페이지
│   ├── ProjectsPage.tsx        # 대시보드 (프로젝트 목록 + 생성)
│   ├── ProjectPage.tsx         # 프로젝트 상세 (챕터/용어집/페르소나 탭)
│   ├── EditorPage.tsx          # 양면 편집기 + 진행 오버레이
│   └── SettingsPage.tsx        # API 키, 테마, 기본값
├── components/
│   ├── layout/                 # 앱 셸, 사이드바, 커맨드 바
│   │   ├── AppShell.tsx        # 사이드바 + 메인 컨테이너
│   │   ├── Sidebar.tsx         # 왼쪽 네비게이션 + 최근 프로젝트
│   │   └── CommandBar.tsx      # Cmd+K 커맨드 팔레트
│   ├── editor/                 # 연결된 텍스트 뷰, 인라인 편집기
│   │   ├── SideBySideEditor.tsx         # 스크롤 동기화된 레이아웃
│   │   ├── ConnectedTextView.tsx        # 세그먼트-to-span 렌더러
│   │   ├── InlineEditor.tsx             # 플로팅 textarea 편집기
│   │   ├── CoTReasoningPanel.tsx        # Chain-of-thought 표시
│   │   └── SegmentHighlighter.tsx       # 세그먼트 상호작용 HOC
│   ├── project/                # 프로젝트 카드, 챕터 목록
│   │   ├── ProjectCard.tsx              # 프로젝트 그리드 아이템
│   │   └── ChapterList.tsx              # 통계가 있는 챕터 테이블
│   ├── translation/            # 번역 버튼, 진행 오버레이
│   │   ├── TranslateButton.tsx          # 번역 트리거
│   │   ├── ProgressOverlay.tsx          # 파이프라인 단계가 있는 모달
│   │   └── PipelineStageIndicator.tsx   # 개별 단계 상태
│   ├── knowledge/              # 용어집 패널, 페르소나 패널
│   │   ├── GlossaryPanel.tsx            # 용어 관리 UI
│   │   └── PersonaPanel.tsx             # 캐릭터 관리 UI
│   └── ui/                     # 프리미티브 (Button, Input, Dialog, Toast)
│       ├── Button.tsx
│       ├── Input.tsx
│       ├── Dialog.tsx
│       └── ...
├── lib/                        # 유틸리티
│   ├── cn.ts                   # Tailwind merge (clsx + twMerge)
│   ├── constants.ts            # 언어, 프로바이더, 파이프라인 단계
│   └── formatters.ts           # 날짜, 시간, 텍스트 포매팅
└── styles/
    └── globals.css             # CSS 변수, 테마, 기본 스타일
```

---

## API 레이어 (`api/`)

### `tauri-bridge.ts`

**목적:** Tauri IPC를 통해 React와 Python 사이드카 간 브리지 역할.

#### `rpc<T>(method: string, params?: Record<string, unknown>): Promise<T>`

범용 JSON-RPC 호출 래퍼.

```typescript
const result = await rpc<Project>("project.get", { project_id: 1 });
```

#### `onPipelineProgress(callback: (progress: PipelineProgress) => void): Promise<UnlistenFn>`

사이드카로부터 파이프라인 진행 이벤트를 수신.

```typescript
const unlisten = await onPipelineProgress((p) => {
  console.log(`Stage: ${p.stage}, Progress: ${p.progress}, Message: ${p.message}`);
});
// 나중에: unlisten()
```

#### `onSidecarStatus(callback: (status: { connected: boolean; error?: string }) => void): Promise<UnlistenFn>`

사이드카 연결 상태 변경을 수신.

#### `api` 객체

`rpc()`를 래핑하는 편의 메서드:

**헬스체크:**
- `healthCheck()` → `{ status: string, version: string }`

**설정:**
- `setApiKeys(keys: Record<string, string>)` — LLM API 키 저장
- `getApiKeys()` → `Record<string, boolean>` — 어떤 키가 존재하는지 확인 (값은 아님)
- `testProvider(provider: string)` → `{ success: boolean, error?: string }`

**프로젝트:**
- `listProjects()` → `Project[]`
- `createProject(data)` → `Project`
- `getProject(projectId: number)` → `Project`
- `updateProject(projectId: number, data)` → `Project`
- `deleteProject(projectId: number)` → `void`

**챕터:**
- `listChapters(projectId: number)` → `Chapter[]`
- `createChapter(data)` → `Chapter`
- `getChapter(chapterId: number)` → `Chapter`
- `updateChapter(chapterId: number, data)` → `Chapter`
- `deleteChapter(chapterId: number)` → `void`
- `getEditorData(chapterId: number, targetLanguage: string)` → `EditorData`

**용어집:**
- `listGlossary(projectId: number)` → `GlossaryEntry[]`
- `createGlossaryEntry(data)` → `GlossaryEntry`
- `updateGlossaryEntry(entryId: number, data)` → `GlossaryEntry`
- `deleteGlossaryEntry(entryId: number)` → `void`

**페르소나:**
- `listPersonas(projectId: number)` → `Persona[]`
- `createPersona(data)` → `Persona`
- `updatePersona(personaId: number, data)` → `Persona`
- `deletePersona(personaId: number)` → `void`

**파이프라인:**
- `translateChapter(chapterId: number, targetLanguage: string)` → 번역 트리거
- `cancelPipeline()` → 활성 파이프라인 취소

---

### `types.ts`

Python 백엔드 스키마와 일치하는 TypeScript 인터페이스.

**핵심 도메인 타입:**

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

**편집기 데이터 구조:**

```typescript
interface EditorData {
  source_connected_text: string;        // 연속된 원문 텍스트
  translated_connected_text: string;    // 연속된 번역 텍스트
  segment_map: SegmentMapEntry[];       // 오프셋 매핑
}

interface SegmentMapEntry {
  segment_id: number;
  source_start: number;      // 원문 텍스트의 문자 오프셋
  source_end: number;
  translated_start: number;  // 번역 텍스트의 문자 오프셋
  translated_end: number;
  type: string;              // "dialogue" | "narration"
  speaker: string | null;
  batch_id: number | null;
}
```

**파이프라인 타입:**

```typescript
interface PipelineProgress {
  stage: string;      // 현재 파이프라인 단계 키
  progress: number;   // 0.0 ~ 1.0
  message: string;    // 사람이 읽을 수 있는 상태
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

## 상태 관리 (`stores/`)

### `app-store.ts`

**목적:** 애플리케이션 전역 UI 상태 (테마, 사이드카, 커맨드 바).

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

**사용법:**

```typescript
const { theme, setTheme, commandBarOpen, toggleCommandBar } = useAppStore();
```

**구현 노트:**
- `setTheme()`은 `<html>`에 `data-theme` 속성을 즉시 적용
- `sidecarConnected`는 `onSidecarStatus()` 이벤트 리스너를 통해 업데이트됨

---

### `editor-store.ts`

**목적:** 편집기 전용 UI 상태 (활성 세그먼트, 편집 모드, 세그먼트 맵).

```typescript
interface EditorState {
  activeSegmentId: number | null;         // 강조된 세그먼트
  setActiveSegment: (id: number | null) => void;
  editingSegmentId: number | null;        // 현재 편집 중인 세그먼트
  setEditingSegment: (id: number | null) => void;
  editText: string;                       // 인라인 편집기의 텍스트
  setEditText: (text: string) => void;
  segmentMap: SegmentMapEntry[];          // 캐시된 세그먼트 맵
  setSegmentMap: (map: SegmentMapEntry[]) => void;
  showReasoning: boolean;                 // CoT 패널 가시성
  toggleReasoning: () => void;
}
```

**사용법:**

```typescript
const { activeSegmentId, setActiveSegment } = useEditorStore();
```

---

### `pipeline-store.ts`

**목적:** 번역 파이프라인 진행 상황 추적.

```typescript
interface PipelineState {
  isRunning: boolean;
  currentStage: string | null;
  progress: number;        // 0.0 ~ 1.0
  message: string;
  setProgress: (stage: string, progress: number, message: string) => void;
  start: () => void;
  finish: () => void;
  reset: () => void;
}
```

**사용법:**

```typescript
const { isRunning, currentStage, progress, message } = usePipelineStore();
```

**흐름:**
1. `TranslateButton`이 뮤테이션 전에 `start()` 호출
2. `useProgress` 훅이 `onPipelineProgress()` 이벤트를 수신
3. 이벤트가 `setProgress()`를 호출하여 스토어 업데이트
4. `ProgressOverlay`가 스토어를 읽고 모달 표시
5. 완료 시 `finish()` 호출

---

## 훅 (`hooks/`)

### `useProject.ts`

**쿼리:**

```typescript
useProjects() → { data: Project[], isLoading, error }
useProject(id: number | null) → { data: Project, isLoading, error }
```

**뮤테이션:**

```typescript
useCreateProject() → { mutate, mutateAsync, isPending }
  // mutate({ name, source_language?, target_language?, genre?, description? })

useUpdateProject() → { mutate, mutateAsync, isPending }
  // mutate({ id, ...data })

useDeleteProject() → { mutate, mutateAsync, isPending }
  // mutate(id)
```

**캐시 무효화:**
- `createProject` → `["projects"]` 무효화
- `updateProject` → `["projects"]`와 `["project", id]` 무효화
- `deleteProject` → `["projects"]` 무효화

---

### `useChapter.ts`

**쿼리:**

```typescript
useChapters(projectId: number | null) → { data: Chapter[], isLoading, error }
useChapter(id: number | null) → { data: Chapter, isLoading, error }
useEditorData(chapterId: number | null, targetLanguage: string) → { data: EditorData, isLoading, error }
```

**뮤테이션:**

```typescript
useCreateChapter() → { mutate, mutateAsync, isPending }
  // mutate({ project_id, title, source_content? })

useUpdateChapter() → { mutate, mutateAsync, isPending }
  // mutate({ id, ...data })

useDeleteChapter() → { mutate, mutateAsync, isPending }
  // mutate(id)
```

**캐시 무효화:**
- `createChapter` → `["chapters", projectId]` 무효화
- `updateChapter` → `["chapter", id]`와 `["chapters"]` 무효화
- `deleteChapter` → `["chapters"]` 무효화

---

### `useGlossary.ts`

**쿼리:**

```typescript
useGlossary(projectId: number | null) → { data: GlossaryEntry[], isLoading, error }
```

**뮤테이션:**

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

**쿼리:**

```typescript
usePersonas(projectId: number | null) → { data: Persona[], isLoading, error }
```

**뮤테이션:**

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

**뮤테이션:**

```typescript
useTranslateChapter() → { mutate, mutateAsync, isPending }
  // mutate({ chapterId, targetLanguage })
```

**캐시 무효화:**
- `["chapter", chapterId]` 무효화
- `["editor-data", chapterId]` 무효화

---

### `useProgress.ts`

**목적:** 파이프라인 진행 이벤트를 구독하고 `usePipelineStore`를 업데이트.

```typescript
useProgress() → PipelineState
```

**구현:**

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

**목적:** 문서 루트에 테마를 적용하고 시스템 테마 변경에 응답.

```typescript
useTheme() → { theme: "light" | "dark" | "system", setTheme: (theme) => void }
```

**구현:**

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

## 페이지 (`pages/`)

### `ProjectsPage.tsx`

**목적:** 모든 프로젝트를 표시하는 대시보드, 생성 대화상자 포함.

**상태:**
- `useProjects()` — 모든 프로젝트 가져오기
- `useCreateProject()` — 생성 뮤테이션
- 로컬 상태: 대화상자 열림, 폼 데이터

**레이아웃:**
- "새 프로젝트" 버튼이 있는 헤더
- 프로젝트가 없으면 빈 상태
- `ProjectCard` 컴포넌트 그리드
- 이름, 설명, 원본/대상 언어, 장르가 있는 생성 대화상자

**네비게이션:**
- 카드 클릭 → `/project/:id`로 이동
- 생성 후 → 새 프로젝트로 이동

---

### `ProjectPage.tsx`

**목적:** 챕터, 용어집, 페르소나 탭이 있는 프로젝트 상세.

**상태:**
- `useProject(projectId)` — 프로젝트 가져오기
- `useCreateChapter()` — 챕터 생성 뮤테이션
- `useUpdateProject()` — 프로젝트 업데이트 뮤테이션
- `useDeleteProject()` — 프로젝트 삭제 뮤테이션
- 로컬 상태: 활성 탭, 대화상자

**레이아웃:**
- 프로젝트로 돌아가는 브레드크럼
- 이름, 언어, 장르, 설명이 있는 프로젝트 헤더
- 편집/삭제 버튼
- 탭 바: 챕터 | 용어집 | 페르소나
- 탭 콘텐츠 영역

**탭:**
1. **챕터:** "챕터 추가" 버튼이 있는 `ChapterList` 컴포넌트
2. **용어집:** `GlossaryPanel` 컴포넌트
3. **페르소나:** `PersonaPanel` 컴포넌트

---

### `EditorPage.tsx`

**목적:** 번역 컨트롤이 있는 양면 편집기.

**상태:**
- `useChapter(chapterId)` — 챕터 메타데이터 가져오기
- `useEditorData(chapterId, targetLanguage)` — 편집기 데이터 가져오기
- `useProgress()` — 파이프라인 진행 상황
- 로컬 상태: 대상 언어 선택기

**레이아웃:**
- 다음을 포함하는 상단 바:
  - 프로젝트로 돌아가기 버튼
  - 챕터 제목
  - 대상 언어 선택기
  - 번역 버튼
  - 내보내기 버튼
- 메인 영역: `SideBySideEditor` 컴포넌트
- 하단 패널: `CoTReasoningPanel` 컴포넌트
- 오버레이: `ProgressOverlay` (`isRunning`일 때)

**흐름:**
1. 챕터 및 편집기 데이터 로드
2. 사용자가 대상 언어 선택
3. 사용자가 "번역" 클릭
4. `TranslateButton`이 `useTranslateChapter` 뮤테이션 트리거
5. 파이프라인 단계가 있는 `ProgressOverlay` 표시
6. `useProgress` 훅이 이벤트로부터 스토어 업데이트
7. 완료 시 편집기 데이터가 자동으로 재페칭됨

---

### `SettingsPage.tsx`

**목적:** API 키, 테마, 기본 언어 설정.

**상태:**
- `useAppStore()` — 테마
- 로컬 상태: API 키, 표시/숨김 토글, 기본 프로바이더, 기본 언어

**섹션:**
1. **외관:** 라이트/다크/시스템 테마 선택기
2. **LLM API 키:** Gemini, Claude, OpenAI (표시/숨김/테스트 버튼이 있는 마스킹된 입력)
3. **기본 LLM 프로바이더:** Gemini | Claude | OpenAI
4. **기본 언어:** 원본 및 대상 언어 선택기
5. **정보:** 버전 정보

**노트:** API 키 저장이 아직 완전히 구현되지 않음 (알림 표시).

---

## 편집기 컴포넌트 (`components/editor/`)

### `SideBySideEditor.tsx`

**목적:** 동기화된 스크롤링과 세그먼트 강조 표시가 있는 2패널 레이아웃.

**Props:**

```typescript
interface SideBySideEditorProps {
  sourceText: string;
  translatedText: string;
  segmentMap: SegmentMapEntry[];
  onSegmentEdit?: (segmentId: number, newText: string) => void;
}
```

**기능:**
- **동기화된 스크롤링:** 한 패널을 스크롤하면 다른 패널이 비례적으로 따라감
- **2개의 패널:** 원문 (왼쪽)과 번역 (오른쪽)
- **세그먼트 강조 표시:** `SegmentHighlighter` HOC 사용
- **연결된 텍스트 뷰:** 두 패널 모두 `ConnectedTextView` 사용

**구현 세부사항:**

```typescript
// 스크롤 동기화 로직
const handleSourceScroll = () => {
  if (isTranslatedScrolling) return;
  isSourceScrolling = true;
  const scrollPercentage = sourceEl.scrollTop / (sourceEl.scrollHeight - sourceEl.clientHeight);
  translatedEl.scrollTop = scrollPercentage * (translatedEl.scrollHeight - translatedEl.clientHeight);
  setTimeout(() => { isSourceScrolling = false; }, 100);
};
```

**레이아웃:**

```
┌────────────────────┬────────────────────┐
│ 원문 텍스트        │ 번역               │
│                    │                    │
│ 연속 텍스트로      │ 연속 텍스트로      │
│ 렌더링된 세그먼트  │ 렌더링된 세그먼트  │
│                    │                    │
│ (읽기 전용)        │ (편집 가능)        │
└────────────────────┴────────────────────┘
```

---

### `ConnectedTextView.tsx`

**목적:** 클릭 가능한 세그먼트 span으로 연속 텍스트 렌더링.

**Props:**

```typescript
interface ConnectedTextViewProps {
  text: string;
  segmentMap: SegmentMapEntry[];
  side: "source" | "translated";
  activeSegmentId: number | null;
  onSegmentClick: (segmentId: number) => void;
  onSegmentDoubleClick?: (segmentId: number) => void;
  onSegmentEdit?: (segmentId: number, newText: string) => void;
}
```

**작동 방식:**

1. **맵으로부터 세그먼트 구축:**
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

2. **인라인 span으로 렌더링:**
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

3. **상호작용:**
   - **단일 클릭:** 양쪽에서 세그먼트 강조
   - **더블 클릭 (번역 쪽만):** `InlineEditor` 열기

**CSS 클래스:**
- `.segment` — 모든 세그먼트의 기본 클래스
- `.segment-active` — 강조된 세그먼트 (노란색 배경)
- `.segment-dialogue` — 대화 세그먼트 (이탤릭체)

---

### `InlineEditor.tsx`

**목적:** 번역된 세그먼트 텍스트를 편집하기 위한 플로팅 textarea.

**Props:**

```typescript
interface InlineEditorProps {
  segmentId: number;
  initialText: string;
  position: { top: number; left: number; width: number };
  onSave: (text: string) => void;
  onCancel: () => void;
}
```

**기능:**
- **자동 포커스 및 선택:** 마운트 시 textarea에 포커스하고 모든 텍스트 선택
- **키보드 단축키:**
  - `Cmd/Ctrl+Enter` — 저장
  - `Escape` — 취소
- **배경:** 배경 흐리게, 클릭하면 취소
- **플로팅 위치:** 세그먼트 위에 절대 위치 지정

**UI:**
- 세그먼트 텍스트가 있는 Textarea
- 취소/저장 버튼이 있는 하단 바
- 키보드 힌트: "⌘+Enter"

**구현:**

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

**목적:** 활성 세그먼트의 배치에 대한 Chain-of-Thought 추론을 표시하는 접을 수 있는 패널.

**Props:**

```typescript
interface CoTReasoningPanelProps {
  chapterId: number;
}
```

**상태:**
- `useEditorStore`에서 `activeSegmentId`와 `showReasoning` 읽기

**UI:**
- 기본적으로 접혀 있음, 세그먼트 ID가 있는 버튼 표시
- 다음을 표시하도록 확장:
  - **상황 요약:** 장면의 맥락
  - **캐릭터 이벤트:** 주요 캐릭터 행동/감정
  - **번역 추론:** 특정 단어 선택 이유

**구현 노트:**
- 현재 플레이스홀더 데이터 표시
- TODO: `activeSegmentId`의 `batch_id`를 기반으로 추론 데이터 가져오기

---

### `SegmentHighlighter.tsx`

**목적:** 세그먼트 상호작용 상태를 제공하는 고차 컴포넌트.

**패턴:** 렌더 prop 컴포넌트

```typescript
<SegmentHighlighter segmentMap={segmentMap}>
  {({ activeSegmentId, onSegmentClick, onSegmentDoubleClick }) => (
    // 이 props로 children 렌더링
  )}
</SegmentHighlighter>
```

**노트:** 이 컴포넌트는 참조되지만 아직 코드베이스에 없음 (`SideBySideEditor`에 인라인으로 구현되었을 수 있음).

---

## 레이아웃 컴포넌트 (`components/layout/`)

### `AppShell.tsx`

**목적:** 사이드바와 메인 콘텐츠 영역이 있는 루트 레이아웃 컨테이너.

**Props:**

```typescript
interface AppShellProps {
  children: React.ReactNode;
}
```

**구조:**

```tsx
<div className="flex h-screen bg-background text-foreground">
  <Sidebar />
  <main className="flex-1 overflow-auto">
    {children}
  </main>
  <CommandBar />
</div>
```

**훅:**
- 마운트 시 테마를 초기화하기 위해 `useTheme()` 호출

---

### `Sidebar.tsx`

**목적:** 로고, 네비게이션 항목, 최근 프로젝트, 사이드카 상태가 있는 왼쪽 네비게이션 패널.

**상태:**
- `useLocation()` — 활성 상태를 위한 현재 라우트
- `useProjects()` — 최근 목록을 위한 프로젝트 가져오기

**섹션:**
1. **헤더:** "Fiction Translator v2.0"
2. **네비게이션 항목:** 프로젝트, 설정
3. **최근 프로젝트:** 마지막 5개 프로젝트
4. **사이드카 상태:** 초록색 점 + "Sidecar Connected"

**구현:**

```typescript
const navItems = [
  { label: "Projects", path: "/", icon: "📁" },
  { label: "Settings", path: "/settings", icon: "⚙️" },
];
```

---

### `CommandBar.tsx`

**목적:** 빠른 네비게이션을 위한 Cmd+K 커맨드 팔레트.

**상태:**
- `useAppStore()` — `commandBarOpen`, `setCommandBarOpen`
- `useProjects()` — 네비게이션 명령을 위한 프로젝트
- 로컬 상태: 검색 쿼리

**키보드 단축키:**
- `Cmd/Ctrl+K` — 커맨드 바 토글
- `Escape` — 닫기

**명령:**
- "Go to Projects"
- "Go to Settings"
- "Open: [프로젝트 이름]" (각 프로젝트마다)

**UI:**
- 모달 오버레이
- 상단에 검색 입력
- 필터링된 명령 목록
- 명령을 클릭하여 실행 및 닫기

---

## 번역 컴포넌트 (`components/translation/`)

### `TranslateButton.tsx`

**목적:** 챕터 번역을 트리거하는 버튼.

**Props:**

```typescript
interface TranslateButtonProps {
  chapterId: number;
  targetLanguage: string;
  disabled?: boolean;
}
```

**상태:**
- `useTranslateChapter()` — 번역 뮤테이션
- `usePipelineStore()` — `isRunning` 상태

**동작:**
- `disabled` prop, `isPending`, 또는 `isRunning`일 때 비활성화
- 활성일 때 스피너와 "Translating..." 표시
- 클릭 시 `translate({ chapterId, targetLanguage })` 호출

---

### `ProgressOverlay.tsx`

**목적:** 번역 파이프라인 진행 상황을 표시하는 전체 화면 모달.

**상태:**
- `useProgress()` — `isRunning`, `progress`, `currentStage`, `message`

**UI:**
- 제목: "Translating Chapter"
- 진행률 퍼센트: `Math.round(progress * 100)%`
- 진행률 바 (애니메이션)
- 상태 표시기가 있는 파이프라인 단계 목록
- 취소 버튼

**단계 상태 로직:**

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

**목적:** 아이콘과 레이블이 있는 개별 단계 상태 표시기.

**Props:**

```typescript
interface PipelineStageIndicatorProps {
  label: string;
  status: "completed" | "active" | "pending";
  detail?: string;  // 선택적 하위 메시지
}
```

**UI:**
- ✓ 완료 (초록색)
- ● 활성 (파란색, 깜박임)
- ○ 대기 중 (회색)
- 레이블 및 선택적 상세 메시지

**노트:** 이 컴포넌트는 참조되지만 아직 코드베이스에 없음.

---

## 유틸리티 (`lib/`)

### `constants.ts`

**언어:**

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

**LLM 프로바이더:**

```typescript
export const LLM_PROVIDERS = {
  gemini: { name: "Google Gemini", model: "gemini-2.0-flash" },
  claude: { name: "Anthropic Claude", model: "claude-sonnet-4-5-20250929" },
  openai: { name: "OpenAI GPT", model: "gpt-4o" },
} as const;
```

**장르 옵션:**

```typescript
export const GENRE_OPTIONS = [
  "fantasy", "romance", "thriller", "litrpg", "horror",
  "comedy", "sci-fi", "mystery", "drama", "action",
] as const;
```

**파이프라인 단계:**

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

**날짜 포매팅:**

```typescript
formatDate(dateStr: string | null): string
  // → "Jan 15, 2024"

formatRelativeTime(dateStr: string | null): string
  // → "5m ago" | "3h ago" | "2d ago" | "Jan 15, 2024"
```

**텍스트 유틸리티:**

```typescript
truncate(str: string, maxLen: number): string
  // → "This is a long text..." (maxLen 초과 시)

languageName(code: string): string
  // → "Korean" (코드 "ko"로부터)
```

---

### `cn.ts`

**목적:** 적절한 우선순위로 Tailwind 클래스를 병합하는 유틸리티.

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**사용법:**

```typescript
<div className={cn("base-class", isActive && "active-class", className)} />
```

---

## 데이터 흐름

### 페이지 네비게이션 흐름

```
/ (ProjectsPage)
  → 프로젝트 카드 클릭
    → /project/:id (ProjectPage)
      → 챕터 행 클릭
        → /editor/:chapterId (EditorPage)
```

### 번역 흐름

```
1. 사용자가 "Translate" 버튼 클릭
2. TranslateButton이 usePipelineStore.start() 호출
3. TranslateButton.onClick → useTranslateChapter.mutate({ chapterId, targetLanguage })
4. 뮤테이션이 api.translateChapter() 호출 → rpc("pipeline.translate_chapter", { ... })
5. Tauri invoke가 Python 사이드카로 전송
6. 사이드카가 파이프라인 시작, Tauri 이벤트 시스템을 통해 이벤트 발생
7. 한편: useProgress 훅의 onPipelineProgress() 이벤트 리스너
8. 각 이벤트가 usePipelineStore.setProgress(stage, progress, message) 업데이트
9. ProgressOverlay가 파이프라인 스토어를 읽고 실시간 업데이트 표시
10. 파이프라인 완료 → React Query가 편집기 데이터 무효화
11. EditorPage가 새 번역으로 자동 재페칭
```

### 편집기 상호작용 흐름

```
1. 사용자가 ConnectedTextView에서 텍스트 클릭
2. ConnectedTextView가 문자 오프셋과 세그먼트 맵으로부터 세그먼트 식별
3. onSegmentClick(segmentId) → useEditorStore.setActiveSegment(segmentId)
4. 두 패널 모두 일치하는 <span data-segment-id={...}>에 CSS 클래스로 강조
5. 사용자가 더블 클릭 (번역 쪽만)
6. ConnectedTextView가 위치 계산, onSegmentDoubleClick(segmentId) 호출
7. 세그먼트 위치에 InlineEditor 표시
8. 사용자가 텍스트 편집, Cmd+Enter 누름
9. onSave(newText) → onSegmentEdit(segmentId, newText)
10. API 호출이 세그먼트 업데이트 (TODO: 백엔드 엔드포인트 구현)
11. 편집기 데이터 재페칭, 텍스트 업데이트
```

### 테마 흐름

```
1. useTheme 훅이 app-store에서 테마 읽기
2. useEffect가 테마 변경 감시
3. theme === "system"인 경우:
   - window.matchMedia("(prefers-color-scheme: dark)") 확인
   - 시스템 기본 설정에 따라 <html>에 .dark 클래스 적용
4. theme === "dark" 또는 "light"인 경우:
   - .dark 클래스를 직접 적용 (dark면 true, light면 false)
5. globals.css의 CSS 변수가 .dark 클래스에 반응
6. 모든 컴포넌트가 새 색상으로 재렌더링
```

### 쿼리 무효화 흐름

**프로젝트 생성 후:**
```
useCreateProject.mutate() → api.createProject()
  → onSuccess: queryClient.invalidateQueries({ queryKey: ["projects"] })
    → useProjects()가 자동 재페칭
      → ProjectsPage가 새 프로젝트 표시
```

**챕터 번역 후:**
```
useTranslateChapter.mutate() → api.translateChapter()
  → onSuccess: queryClient.invalidateQueries({ queryKey: ["chapter", chapterId] })
             queryClient.invalidateQueries({ queryKey: ["editor-data", chapterId] })
    → useChapter()와 useEditorData()가 자동 재페칭
      → EditorPage가 업데이트된 번역 표시
```

---

## 스타일링 시스템

### CSS 변수

`src/styles/globals.css`에 위치:

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

### Tailwind 설정

색상은 `hsl()`을 통해 CSS 변수 사용:

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

### 컴포넌트 클래스

**세그먼트 강조:**

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

## 성능 고려사항

### React Query Stale Time

```typescript
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30000 } },  // 30초
});
```

데이터가 30초 동안 최신으로 간주되어 불필요한 재페칭 방지.

### 스크롤 동기화 디바운싱

```typescript
setTimeout(() => { isSourceScrolling = false; }, 100);
```

패널 간 스크롤 이벤트 핑퐁 방지.

### 세그먼트 맵 메모이제이션

```typescript
const segments = useMemo(() => {
  // 맵으로부터 세그먼트 구축
}, [text, segmentMap, side]);
```

텍스트나 맵이 변경될 때만 재계산.

### 이벤트 리스너 정리

```typescript
useEffect(() => {
  let unlisten: (() => void) | null = null;
  onPipelineProgress((p) => { /* ... */ }).then((fn) => { unlisten = fn; });
  return () => { unlisten?.(); };
}, [setProgress]);
```

Tauri 이벤트 리스너로부터 메모리 누수 방지.

---

## 개발 워크플로우

### 앱 실행

```bash
npm run tauri dev
```

핫 리로드가 있는 Vite dev 서버 + Tauri 윈도우 시작.

### 빌드

```bash
npm run tauri build
```

최적화된 프로덕션 번들 + 네이티브 실행 파일 생성.

### 타입 체킹

```bash
npm run typecheck
```

체크 모드로 TypeScript 컴파일러 실행.

---

## 향후 개선사항

### 아직 구현되지 않음

1. **세그먼트 편집 백엔드:** `onSegmentEdit`이 TODO API 엔드포인트 호출
2. **내보내기 기능:** EditorPage의 `handleExport`
3. **API 키 저장:** 설정 페이지가 지속하는 대신 알림 표시
4. **CoT 추론 데이터:** 현재 플레이스홀더 표시, batch_id 쿼리 필요
5. **SegmentHighlighter 컴포넌트:** 참조되지만 인라인으로 구현되었을 수 있음
6. **PipelineStageIndicator 컴포넌트:** 참조되지만 코드베이스에서 찾을 수 없음
7. **ProjectCard, ChapterList, GlossaryPanel, PersonaPanel 컴포넌트:** import되지만 저장소에 없음

### 권장 다음 단계

1. 사이드카에 세그먼트 업데이트 엔드포인트 구현
2. 내보내기 기능 추가 (DOCX, TXT, JSON)
3. Tauri 보안 저장소를 통한 API 키 저장 연결
4. batch_id를 기반으로 데이터베이스에서 CoT 추론 가져오기
5. 필요한 경우 SegmentHighlighter를 별도 컴포넌트로 추출
6. project/knowledge 패널용 누락된 컴포넌트 파일 생성
