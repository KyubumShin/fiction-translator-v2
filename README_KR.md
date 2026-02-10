# Fiction Translator v2.0

LLM 기반 Chain-of-Thought 추론을 사용하여 소설(소설, 웹 소설, 게임)을 번역하는 네이티브 데스크톱 애플리케이션입니다. v1(FastAPI+React)을 Tauri 네이티브 데스크톱 앱으로 완전히 재작성했습니다.

## 개요

Fiction Translator v2.0은 실시간 파이프라인 진행 상황, 연결된 산문 편집, 지능형 용어집 관리를 갖춘 전문 번역 환경을 제공합니다. 이 애플리케이션은 Chain-of-Thought 추론을 포함한 다단계 LangGraph 파이프라인을 사용하여 고품질 번역을 생성하면서 캐릭터 일관성과 내러티브 흐름을 유지합니다.

## 아키텍처

이 애플리케이션은 3계층 아키텍처를 사용합니다.

### 1. Tauri Rust Shell (`src-tauri/`)
다음을 담당하는 네이티브 데스크톱 래퍼:
- Sidecar 프로세스 수명 주기 관리
- 프론트엔드와 Python 백엔드 간 IPC 라우팅
- 실시간 업데이트를 위한 이벤트 포워딩
- 플랫폼별 기능

### 2. React Frontend (`src/`)
다음을 특징으로 하는 현대적인 SaaS 스타일 UI:
- 원본/번역 뷰가 나란히 표시되는 연결된 산문 편집기
- 실시간 파이프라인 진행 상황 모니터링
- 인라인 번역 편집
- 용어집 및 페르소나 관리
- 다크/라이트 테마 지원
- 명령어 팔레트 (Cmd+K)

### 3. Python Sidecar (`sidecar/`)
다음을 포함하는 비즈니스 로직 계층:
- LangGraph 8노드 번역 파이프라인
- SQLAlchemy 2.0을 사용한 SQLite 데이터베이스
- LLM 제공자 통합 (Gemini, Claude, OpenAI)
- 지식 베이스 관리 (용어집, 페르소나)

**IPC 프로토콜:** Rust와 Python 간의 stdin/stdout을 통한 JSON-RPC 2.0 (개행 구분 JSON).

## 주요 기능

- **원클릭 번역**: 실시간 파이프라인 진행 상황 추적과 함께 번역 시작
- **연결된 산문 뷰**: 연속 텍스트 표시 (세그먼트별이 아닌)로 자연스러운 읽기 제공
- **Chain-of-Thought 번역**: 보이는 추론 과정이 포함된 배치 번역
- **다단계 파이프라인**: 검증 및 검토 루프가 있는 8노드 LangGraph 워크플로우
- **다중 LLM 지원**: Google Gemini, Anthropic Claude, OpenAI GPT
- **용어집 관리**: 번역 전체에서 일관된 용어 사용
- **캐릭터 페르소나**: 자동 감지 캐릭터 추적 및 페르소나 인사이트
- **나란한 편집기**: 원본과 번역 간 세그먼트 매핑을 클릭하여 강조 표시
- **인라인 편집**: 실시간 업데이트와 함께 직접 번역 편집
- **내보내기 지원**: TXT 및 DOCX 내보내기 형식
- **명령어 팔레트**: 키보드 기반 탐색 (Cmd+K)

## 기술 스택

### 데스크톱
- Tauri v2 (Rust)

### 프론트엔드
- React 18
- TypeScript
- Vite
- TailwindCSS
- Zustand (UI 상태)
- TanStack React Query (서버 상태)
- React Router v6
- Lucide React (아이콘)

### 백엔드
- Python 3.11+
- LangGraph
- SQLAlchemy 2.0
- SQLite

### LLM 제공자
- Google Gemini
- Anthropic Claude
- OpenAI GPT

## 프로젝트 구조

```
fiction-translator-v2/
├── src-tauri/                          # Tauri Rust Shell
│   ├── Cargo.toml                      # Rust 의존성
│   ├── tauri.conf.json                 # 앱 설정 (윈도우, 식별자, 플러그인)
│   ├── build.rs                        # Tauri 빌드 스크립트
│   ├── capabilities/
│   │   └── default.json                # Tauri v2 권한
│   ├── src/
│   │   ├── main.rs                     # 진입점
│   │   ├── lib.rs                      # 앱 빌더, 플러그인 등록, sidecar 자동 시작
│   │   ├── sidecar.rs                  # Python 프로세스 수명 주기 (시작/중지/호출)
│   │   ├── ipc.rs                      # JSON-RPC 메시지 타입, 원자적 ID 생성
│   │   ├── commands.rs                 # Tauri 명령어 핸들러 (rpc_call, sidecar_status)
│   │   ├── state.rs                    # 공유 앱 상태 (Arc<Mutex<SidecarProcess>>)
│   │   └── events.rs                   # 스트리밍 진행 상황 이벤트 구조체
│   ├── DOCS_EN.md                      # 영문 설명서
│   └── DOCS_KR.md                      # 한문 설명서
│
├── src/                                # React Frontend
│   ├── main.tsx                        # React 진입점
│   ├── App.tsx                         # 라우팅이 있는 루트 컴포넌트
│   ├── index.css                       # 전역 스타일 (CSS 변수, Tailwind)
│   ├── api/
│   │   ├── tauri-bridge.ts             # invoke() 래퍼 + 이벤트 리스너
│   │   └── types.ts                    # 공유 TypeScript 인터페이스
│   ├── stores/
│   │   ├── app-store.ts                # 전역 UI 상태 (테마, sidecar 상태)
│   │   ├── editor-store.ts             # 편집기 상태 (활성 세그먼트, 편집 중)
│   │   └── pipeline-store.ts           # 번역 파이프라인 진행 상황
│   ├── hooks/
│   │   ├── useProject.ts              # 프로젝트 CRUD 쿼리/뮤테이션
│   │   ├── useChapter.ts             # 챕터 CRUD + 편집기 데이터
│   │   ├── useGlossary.ts            # 용어집 CRUD
│   │   ├── usePersonas.ts            # 페르소나 CRUD
│   │   ├── useTranslation.ts         # 번역 파이프라인 트리거
│   │   ├── useProgress.ts            # Tauri 이벤트를 통한 실시간 진행 상황
│   │   └── useTheme.ts               # 다크/라이트 테마 관리
│   ├── pages/
│   │   ├── ProjectsPage.tsx           # 프로젝트 그리드가 있는 대시보드
│   │   ├── ProjectPage.tsx            # 프로젝트 상세 (챕터/용어집/페르소나 탭)
│   │   ├── EditorPage.tsx             # 나란한 번역 편집기 (핵심)
│   │   └── SettingsPage.tsx           # API 키, 테마, 기본 설정
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx           # 기본 레이아웃 래퍼
│   │   │   ├── Sidebar.tsx            # 네비게이션 사이드바
│   │   │   └── CommandBar.tsx         # Cmd+K 명령어 팔레트
│   │   ├── editor/
│   │   │   ├── SideBySideEditor.tsx   # 동기화된 스크롤이 있는 2단창 편집기
│   │   │   ├── ConnectedTextView.tsx  # 보이지 않는 세그먼트 스팬이 있는 산문 렌더러
│   │   │   ├── InlineEditor.tsx       # 번역 편집을 위한 떠다니는 textarea
│   │   │   ├── CoTReasoningPanel.tsx  # Chain-of-Thought 추론 표시
│   │   │   └── SegmentHighlighter.tsx # 크로스 팬 강조 표시 관리
│   │   ├── translation/
│   │   │   ├── TranslateButton.tsx    # 원클릭 번역 트리거
│   │   │   ├── ProgressOverlay.tsx    # 파이프라인 진행 상황 모달
│   │   │   └── PipelineStageIndicator.tsx  # 개별 단계 상태
│   │   ├── project/
│   │   │   ├── ProjectCard.tsx        # 프로젝트 그리드 카드
│   │   │   ├── ChapterList.tsx        # 챕터 목록
│   │   │   └── ChapterCard.tsx        # 챕터 카드
│   │   ├── knowledge/
│   │   │   ├── GlossaryPanel.tsx      # 용어집 관리 UI
│   │   │   ├── PersonaPanel.tsx       # 캐릭터 페르소나 관리
│   │   │   └── PersonaSummaryCard.tsx # 페르소나 요약 표시
│   │   └── ui/
│   │       ├── Button.tsx             # 재사용 가능한 버튼 컴포넌트
│   │       ├── Input.tsx              # 재사용 가능한 입력 컴포넌트
│   │       ├── Dialog.tsx             # 모달 대화 상자 컴포넌트
│   │       └── Toast.tsx              # 토스트 알림 컴포넌트
│   ├── lib/
│   │   ├── cn.ts                      # Tailwind 클래스 병합 유틸리티
│   │   ├── constants.ts              # 앱 상수
│   │   └── formatters.ts            # 날짜/숫자 포매터
│   ├── DOCS_EN.md                    # 영문 설명서
│   └── DOCS_KR.md                    # 한문 설명서
│
├── sidecar/                           # Python Sidecar (LangGraph)
│   ├── pyproject.toml                 # Python 의존성 및 프로젝트 설정
│   └── src/fiction_translator/
│       ├── main.py                    # 진입점: DB 초기화 + JSON-RPC 서버 시작
│       ├── ipc/
│       │   ├── protocol.py            # JSON-RPC 메시지 스키마 및 파서
│       │   ├── server.py              # 비동기 stdin/stdout JSON-RPC 서버
│       │   └── handlers.py            # 서비스로 라우팅하는 25개 메서드 핸들러
│       ├── db/
│       │   ├── models.py              # 10개의 SQLAlchemy 2.0 모델
│       │   └── session.py             # 엔진, 세션 팩토리, init_db()
│       ├── services/
│       │   ├── project_service.py     # 프로젝트 CRUD
│       │   ├── chapter_service.py     # 챕터 CRUD + get_editor_data()
│       │   ├── glossary_service.py    # 용어집 CRUD + 대량 가져오기
│       │   ├── persona_service.py     # 페르소나 CRUD + 제안 처리
│       │   └── export_service.py      # TXT/DOCX 내보내기
│       ├── pipeline/
│       │   ├── state.py               # TranslationState TypedDict
│       │   ├── graph.py               # LangGraph StateGraph 정의
│       │   ├── edges.py               # 조건부 라우팅 (검증 게이트, 검토 루프)
│       │   ├── callbacks.py           # 진행 상황 알림 발신자
│       │   └── nodes/
│       │       ├── segmenter.py       # 텍스트 세그먼테이션 (규칙 기반 + LLM)
│       │       ├── character_extractor.py  # 화자 감지 (정규식 + LLM)
│       │       ├── validator.py       # 세그먼테이션 품질 검증자
│       │       ├── translator.py      # CoT 배치 번역기
│       │       ├── reviewer.py        # 번역 품질 검토자
│       │       └── persona_learner.py # 캐릭터 인사이트 추출
│       ├── llm/
│       │   ├── providers.py           # LLMProvider ABC + Gemini/Claude/OpenAI
│       │   └── prompts/
│       │       ├── cot_translation.py      # CoT 번역 프롬프트 빌더
│       │       ├── segmentation.py         # 세그먼테이션 프롬프트
│       │       ├── character_extraction.py # 캐릭터 추출 프롬프트
│       │       ├── validation.py           # 검증 프롬프트
│       │       ├── review.py               # 검토 프롬프트
│       │       └── persona_analysis.py     # 페르소나 분석 프롬프트
│       ├── DOCS_EN.md                 # 영문 설명서
│       └── DOCS_KR.md                 # 한문 설명서
│
├── .github/workflows/
│   ├── build.yml                      # CI/CD: macOS + Windows 빌드 및 릴리스
│   └── check.yml                      # PR 체크: TypeScript + Python 린트
│
├── index.html                         # HTML 진입점
├── package.json                       # Node.js 의존성
├── vite.config.ts                     # Vite 번들러 설정
├── tsconfig.json                      # TypeScript 설정
├── tailwind.config.ts                 # Tailwind CSS 설정
└── postcss.config.js                  # PostCSS 설정
```

## 개발 설정

### 필수 요구 사항

- Node.js 18+
- Python 3.11+
- Rust 툴체인 (Tauri 개발용)

### 설치

1. **프론트엔드 의존성**
   ```bash
   npm install
   ```

2. **Python Sidecar**
   ```bash
   cd sidecar
   pip install -e .
   ```

### 개발 명령어

- **개발 모드** (Tauri 핫 리로드 포함)
  ```bash
  npm run tauri dev
  ```

- **프론트엔드만** (Tauri 없이 UI 개발용)
  ```bash
  npm run dev
  ```

- **프로덕션 빌드**
  ```bash
  npm run tauri build
  ```

## 데이터베이스

이 애플리케이션은 데이터 지속성을 위해 SQLite를 사용합니다.

**위치:** `~/.fiction-translator/data.db`

**스키마:** 10개 테이블
- `projects` - 번역 프로젝트
- `chapters` - 챕터 콘텐츠 및 메타데이터
- `segments` - 경계가 있는 텍스트 세그먼트
- `translations` - 번역된 세그먼트 텍스트
- `translation_batches` - 배치 번역 메타데이터
- `glossary_entries` - 용어 용어집
- `personas` - 캐릭터 페르소나 및 특성
- `persona_suggestions` - 자동 감지 페르소나 제안
- `pipeline_runs` - 번역 파이프라인 실행 로그
- `exports` - 내보내기 기록

**초기화:** 데이터베이스는 첫 실행 시 모든 필수 테이블 및 인덱스와 함께 자동으로 생성됩니다.

## LangGraph 번역 파이프라인

번역 파이프라인은 조건부 라우팅이 있는 8개 노드로 구성됩니다.

```
Load Context
    ↓
Segmenter (규칙 기반 + LLM을 사용한 텍스트 세그먼테이션)
    ↓
Character Extractor (정규식 + LLM을 통한 화자 감지)
    ↓
Validator (세그먼테이션 품질 확인)
    ├─ PASS → 계속
    └─ FAIL → Segmenter 재시도 (최대 2회)
    ↓
CoT Translator (Chain-of-Thought를 포함한 배치 번역)
    ↓
Reviewer (번역 품질 평가)
    ├─ PASS → 계속
    └─ FAIL → Translator 재시도 (최대 2회)
    ↓
Persona Learner (캐릭터 인사이트 추출)
    ↓
Finalize (데이터베이스에 결과 저장)
```

**파이프라인 기능:**
- 실시간 진행 상황 알림
- 지수 백오프를 사용한 자동 재시도
- 세그먼테이션 및 번역 단계에서의 품질 게이트
- Chain-of-Thought 추론 보존
- 캐릭터 페르소나 학습

## 지원되는 언어

**원본 및 대상 언어:**
- 한국어
- 일본어
- 중국어
- 영어
- 스페인어
- 프랑스어
- 독일어
- 포르투갈어
- 러시아어
- 베트남어
- 태국어
- 인도네시아어

대상 언어는 번역 실행당 구성 가능하여 유연한 언어 쌍 조합을 허용합니다.

## 설명서

각 아키텍처 계층에는 이중 언어 설명서가 포함되어 있습니다.

### Tauri Rust Shell
- `src-tauri/DOCS_EN.md` - 영문 설명서
- `src-tauri/DOCS_KR.md` - 한문 설명서

### React Frontend
- `src/DOCS_EN.md` - 영문 설명서
- `src/DOCS_KR.md` - 한문 설명서

### Python Sidecar
- `sidecar/DOCS_EN.md` - 영문 설명서
- `sidecar/DOCS_KR.md` - 한문 설명서

## 라이선스

MIT
