# Fiction Translator v2.0 — Python 사이드카 문서

## 개요

Python 사이드카는 Fiction Translator v2.0의 백엔드 엔진입니다. Tauri 애플리케이션과 별도의 프로세스로 실행되며, 모든 번역 로직, LLM 상호작용, 데이터 지속성을 처리합니다. 사이드카는 stdin/stdout을 통해 JSON-RPC 2.0으로 Tauri 프론트엔드와 통신합니다.

**핵심 책임:**
- LangGraph 기반 파이프라인을 통한 번역 요청 처리
- 프로젝트, 챕터, 세그먼트, 페르소나를 위한 SQLite 데이터베이스 관리
- LLM 제공자 추상화 제공 (Gemini, Claude, OpenAI)
- 번역 중 프론트엔드로 진행 상황 업데이트 스트리밍
- 번역된 콘텐츠를 다양한 형식으로 내보내기 (TXT, DOCX)

## 왜 이런 아키텍처인가?

### 왜 Python 사이드카인가? (임베디드가 아닌)

**이유 1: Python 네이티브 생태계**
- LangGraph와 현대적인 LLM SDK는 Python 우선
- FFI 오버헤드 없이 `httpx`, `sqlalchemy`, `python-docx`에 직접 접근
- 더 빠른 반복: 개발 중 `python -m fiction_translator`를 직접 실행

**이유 2: 크래시 격리**
- 사이드카 크래시가 Tauri 앱을 죽이지 않음
- Tauri가 실패 시 사이드카를 재시작할 수 있음
- 명확한 분리: Rust는 UI/IPC 소유, Python은 AI/데이터 소유

**이유 3: 배포 단순성**
- PyInstaller가 전체 사이드카를 단일 바이너리로 번들링 (`fiction-translator-sidecar`)
- Tauri의 `sidecar` 설정이 앱 실행 시 자동으로 실행
- 사용자는 "Python 설치" 프롬프트를 절대 보지 않음

### 왜 stdin/stdout을 통한 JSON-RPC 2.0인가?

**이유 1: 네이티브 Tauri 지원**
- Tauri는 stdin/stdout 파이프로 내장 사이드카 관리 제공
- HTTP 서버 없음 = 포트 충돌 없음, 방화벽 프롬프트 없음
- macOS, Windows, Linux에서 동일하게 작동

**이유 2: 단순성**
- 라인 기반 프레이밍: 한 줄에 하나의 JSON 객체
- 비동기 응답을 위한 요청 ID 매칭
- 알림(진행 상황 업데이트)은 응답이 필요 없음

**이유 3: 양방향**
- Tauri → Python: 메서드 호출 (요청)
- Python → Tauri: 진행 상황 업데이트 (알림)
- 둘 다 동일한 파이프를 공유하여 조정 문제 방지

### 왜 SQLAlchemy + SQLite인가?

**이유 1: 단일 파일 데이터베이스**
- `~/.fiction-translator/data.db`에 모든 사용자 데이터 포함
- 서버 프로세스 없음, 구성 없음
- 쉬운 백업: 파일만 복사

**이유 2: SQLAlchemy 2.0의 타입 안전성**
- `Mapped[int]` 타입이 개발 시점에 오류 포착
- 관계 추적이 고아 데이터 방지
- Alembic으로 마이그레이션 간단 (향후)

**이유 3: Python이 단일 진실 공급원**
- Tauri는 DB를 직접 건드리지 않음
- 모든 CRUD는 서비스 함수를 통과
- 일관성 유지와 기능 추가가 더 쉬움

### 왜 LangGraph인가?

**이유 1: 상태 관리**
- `TranslationState` TypedDict가 전체 파이프라인을 통과
- 노드가 부분 업데이트를 반환하면, LangGraph가 자동으로 병합
- 진행 상황 추적 용이 (`validation_attempts`, `review_iteration`)

**이유 2: 조건부 엣지**
- 검증 게이트: 실패 시 최대 3번 재분할
- 리뷰 루프: 플래그된 세그먼트를 최대 2번 재번역
- 선언적 흐름이 명령형 루프보다 이해하기 쉬움

**이유 3: 진행 상황 추적**
- 노드가 `notify(callback, stage, pct, message)`를 호출하여 진행 상황 스트리밍
- LangGraph가 블로킹 없이 비동기 실행 처리
- 향후: 크래시 시 재개를 위한 체크포인팅 추가

**이유 4: 확장성**
- 새 노드 추가 (예: "tone_adjuster")는 함수 + 엣지 추가만으로 가능
- 번역 전략 교체 (CoT vs 스트리밍)는 노드 교체
- 다양한 파이프라인 구성을 A/B 테스트하기 쉬움

## 디렉토리 구조

```
sidecar/
├── pyproject.toml              # 프로젝트 메타데이터, 의존성 (Poetry 또는 pip)
├── build.py                    # 바이너리 배포를 위한 PyInstaller 빌드 스크립트
└── src/fiction_translator/
    ├── main.py                 # 진입점: DB 초기화, IPC 서버 시작
    ├── ipc/                    # JSON-RPC 통신 계층
    │   ├── protocol.py         # 메시지 타입 (Request, Response, Notification, Error)
    │   ├── server.py           # 비동기 서버 루프 (stdin → handler → stdout)
    │   └── handlers.py         # 25개 메서드 핸들러 (project.*, chapter.*, pipeline.*, 등)
    ├── db/                     # 데이터베이스 계층 (SQLAlchemy 2.0)
    │   ├── models.py           # 10개 테이블: Project, Chapter, Segment, Translation, 등
    │   └── session.py          # 엔진 생성, 세션 팩토리, init_db()
    ├── services/               # 비즈니스 로직 (CRUD + 도메인 작업)
    │   ├── project_service.py  # 프로젝트 목록/생성/수정/삭제
    │   ├── chapter_service.py  # 챕터 + get_editor_data (연결된 텍스트 뷰)
    │   ├── glossary_service.py # 용어 관리
    │   ├── persona_service.py  # 캐릭터 음성 프로필
    │   └── export_service.py   # TXT/DOCX 내보내기
    ├── pipeline/               # LangGraph 번역 파이프라인
    │   ├── graph.py            # 파이프라인 정의: 노드, 엣지, run_translation_pipeline()
    │   ├── state.py            # TranslationState TypedDict (노드 간 공유 상태)
    │   ├── edges.py            # 조건부 엣지 함수 (should_re_segment, should_re_translate)
    │   ├── callbacks.py        # 진행 상황 알림 헬퍼
    │   └── nodes/              # 파이프라인 노드 구현
    │       ├── segmenter.py    # 오프셋과 함께 번역 가능한 세그먼트로 텍스트 분할
    │       ├── character_extractor.py  # 화자/캐릭터 감지 (정규식 + LLM)
    │       ├── validator.py    # 분할 품질 검사 (7가지 검증 규칙)
    │       ├── translator.py   # 용어집/페르소나 컨텍스트가 있는 CoT 배치 번역
    │       ├── reviewer.py     # 품질 검사, 재번역을 위한 세그먼트 플래그
    │       └── persona_learner.py  # 번역에서 캐릭터 통찰력 추출
    └── llm/                    # LLM 제공자 추상화
        ├── providers.py        # 통합 인터페이스: GeminiProvider, ClaudeProvider, OpenAIProvider
        └── prompts/            # 각 파이프라인 단계를 위한 프롬프트 빌더
            ├── segmentation.py
            ├── character_extraction.py
            ├── validation.py
            ├── cot_translation.py
            ├── review.py
            └── persona_analysis.py
```

## 모듈 문서

### 1. IPC 계층 (`ipc/`)

#### `protocol.py` — 메시지 타입

JSON-RPC 2.0 데이터 구조 정의:

**`JsonRpcRequest`**
- `method: str` — RPC 메서드 이름 (예: `"project.list"`)
- `params: dict | list | None` — 명명된 또는 위치 매개변수
- `id: int | str | None` — 응답 매칭을 위한 요청 ID (None = 알림)
- `jsonrpc: str` — 항상 `"2.0"`
- 메서드: `to_json()`, `from_dict(data)`

**`JsonRpcResponse`**
- `id: int | str | None` — 요청 ID와 일치
- `result: Any` — 성공 결과 (`error`와 상호 배타적)
- `error: JsonRpcError | None` — 오류 세부정보 (`result`와 상호 배타적)
- `jsonrpc: str` — 항상 `"2.0"`
- 메서드: `to_json()`

**`JsonRpcNotification`**
- `JsonRpcRequest`와 동일하지만 항상 `id=None`
- 푸시 이벤트에 사용 (예: 진행 상황 업데이트)
- 응답 기대하지 않음
- 메서드: `to_json()`

**`JsonRpcError`**
- `code: int` — 표준 오류 코드 (아래 상수 참조)
- `message: str` — 사람이 읽을 수 있는 오류 설명
- `data: Any` — 선택적 추가 컨텍스트

**표준 오류 코드:**
```python
PARSE_ERROR = -32700       # 잘못된 JSON
INVALID_REQUEST = -32600   # 필수 필드 누락
METHOD_NOT_FOUND = -32601  # 알 수 없는 메서드
INVALID_PARAMS = -32602    # 잘못된 매개변수 타입
INTERNAL_ERROR = -32603    # 핸들러 예외
```

**`parse_message(raw: str) -> JsonRpcRequest | None`**
- 원시 JSON 문자열을 `JsonRpcRequest`로 파싱
- 파싱 실패 시 `None` 반환 (호출자가 PARSE_ERROR 응답 전송)

#### `server.py` — 서버 루프

**`JsonRpcServer`**

RPC 수명주기를 관리하는 주요 비동기 서버 클래스.

**생성자: `__init__()`**
- 빈 핸들러 레지스트리 초기화
- 스레드 안전 stdout 접근을 위한 쓰기 잠금 생성

**메서드:**

**`register(method: str, handler: Callable[..., Awaitable[Any]])`**
- 단일 메서드 핸들러 등록
- 핸들러 시그니처: `async def handler(**params) -> dict`

**`register_all(handlers: dict[str, Callable])`**
- 여러 핸들러 대량 등록
- `handlers.get_all_handlers()`에서 시작 중 호출

**`async send_notification(method: str, params: dict | None = None)`**
- Tauri로 알림 푸시 (예: 진행 상황 업데이트)
- stdout에 `JsonRpcNotification` 작성
- 논블로킹, 응답 기대하지 않음

**`async run()`**
- 주요 이벤트 루프:
  1. stdin을 `asyncio.StreamReader`에 연결
  2. 루프에서 라인 읽기
  3. 각 라인 파싱 → `JsonRpcRequest`
  4. 핸들러로 디스패치 → `JsonRpcResponse` 얻기
  5. stdout에 응답 작성
  6. 취소 및 오류 처리
- stdin 닫힐 때 종료 (Tauri 프로세스 종료)

**`stop()`**
- 서버 중지 신호
- `_running = False` 설정

**내부 메서드:**

**`async _handle_request(request: JsonRpcRequest) -> JsonRpcResponse | None`**
- 등록된 핸들러로 요청 라우팅
- `request.id is None`이면 알림으로 처리 (응답 없음)
- 핸들러 예외 포착 → `INTERNAL_ERROR` 응답 반환
- 핸들러 등록되지 않은 경우 `METHOD_NOT_FOUND` 반환

**`async _write(message: str)`**
- stdout에 개행 종료 메시지 작성
- `asyncio.Lock`으로 스레드 안전
- 즉시 플러시 (IPC 응답성에 중요)

**흐름 다이어그램:**
```
stdin → readline → parse JSON → _handle_request → handler(**params)
                                      ↓
                                 JsonRpcResponse → _write → stdout

send_notification → JsonRpcNotification → _write → stdout (병렬)
```

#### `handlers.py` — 메서드 라우터

도메인별로 구성된 25개 RPC 메서드 등록. 각 핸들러:
1. `get_db()`로 DB 세션 열기
2. 서비스 함수 호출
3. 세션 닫기
4. dict 반환 (JSON으로 자동 직렬화)

**전역 상태:**

**`_api_keys: dict[str, str]`**
- 인메모리 API 키 저장소
- 키: `"gemini"`, `"claude"`, `"openai"`, `"google"`, `"anthropic"`
- Tauri의 보안 키체인에서 `config.set_keys`로 채워짐

**`_server: JsonRpcServer | None`**
- 알림 전송을 위한 서버 참조
- 시작 중 `set_server(server)`로 설정

**헬퍼:**

**`async send_progress(stage: str, progress: float, message: str = "")`**
- Tauri로 `pipeline.progress` 알림 전송
- 콜백을 통해 파이프라인 노드에서 호출

**건강 메서드:**

**`async health_check() -> dict`**
- `{"status": "ok", "version": "2.0.0"}` 반환
- Tauri가 사이드카가 살아있는지 확인하는 데 사용

**설정 메서드:**

**`async config_set_keys(**keys: str) -> dict`**
- API 키를 `_api_keys`에 저장 (인메모리만)
- 매개변수: `gemini="...", claude="...", openai="..."`
- `{"stored": ["gemini", "claude"]}` 반환

**`async config_get_keys() -> dict`**
- 구성된 키가 있는 제공자 반환
- 예: `{"gemini": true, "claude": false, "openai": true}`

**`async config_test_provider(provider: str) -> dict`**
- LLM 제공자가 작동하는지 테스트
- LLM에 "한 단어로 'hello' 말하기" 전송
- `{"success": true, "response": "Hello"}` 또는 `{"success": false, "error": "..."}` 반환

**프로젝트 메서드:**

**`async project_list() -> list[dict]`**
- 챕터 수와 함께 모든 프로젝트 반환
- `updated_at DESC`로 정렬

**`async project_create(name: str, source_language: str = "ko", target_language: str = "en", **kwargs) -> dict`**
- 새 프로젝트 생성
- 선택적 kwargs: `description`, `genre`, `style_settings`, `pipeline_type`, `llm_provider`
- `id`, `created_at` 등이 있는 프로젝트 dict 반환

**`async project_get(project_id: int) -> dict`**
- ID로 단일 프로젝트 가져오기
- 찾을 수 없으면 `ValueError` 발생

**`async project_update(project_id: int, **kwargs) -> dict`**
- 프로젝트 필드 업데이트
- 허용되는 kwargs: `id`를 제외한 모든 필드
- 업데이트된 프로젝트 dict 반환

**`async project_delete(project_id: int) -> dict`**
- 프로젝트와 모든 관련 데이터 삭제 (챕터, 세그먼트, 번역으로 캐스케이드)
- `{"deleted": true, "id": project_id}` 반환

**챕터 메서드:**

**`async chapter_list(project_id: int) -> list[dict]`**
- 프로젝트의 챕터 목록
- `segment_count` 및 `translated_count` 통계 포함
- `order` 필드로 정렬

**`async chapter_create(project_id: int, title: str, source_content: str = "", **kwargs) -> dict`**
- 새 챕터 생성
- 선택적 kwargs: `file_path`
- 다음 `order` 번호 자동 할당
- 챕터 dict 반환

**`async chapter_get(chapter_id: int) -> dict`**
- ID로 단일 챕터 가져오기

**`async chapter_update(chapter_id: int, **kwargs) -> dict`**
- 챕터 필드 업데이트
- 업데이트된 챕터 dict 반환

**`async chapter_delete(chapter_id: int) -> dict`**
- 챕터와 모든 세그먼트/번역 삭제 (캐스케이드)
- `{"deleted": true, "id": chapter_id}` 반환

**`async chapter_get_editor_data(chapter_id: int, target_language: str = "en") -> dict`**
- 편집기를 위한 연결된 텍스트 뷰 가져오기
- 반환:
  - `source_connected_text`: 산문으로서 전체 원본 텍스트
  - `translated_connected_text`: 산문으로서 전체 번역
  - `segment_map`: 클릭하여 강조 표시를 위한 오프셋 매핑 배열
- 각 segment_map 항목:
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

**용어집 메서드:**

**`async glossary_list(project_id: int) -> list[dict]`**
- 프로젝트의 모든 용어집 항목 목록
- `source_term`으로 정렬

**`async glossary_create(project_id: int, source_term: str, translated_term: str, **kwargs) -> dict`**
- 용어집 항목 생성
- 선택적 kwargs: `term_type`, `notes`, `context`, `auto_detected`
- 항목 dict 반환

**`async glossary_update(entry_id: int, **kwargs) -> dict`**
- 용어집 항목 필드 업데이트

**`async glossary_delete(entry_id: int) -> dict`**
- 용어집 항목 삭제
- `{"deleted": true, "id": entry_id}` 반환

**페르소나 메서드:**

**`async persona_list(project_id: int) -> list[dict]`**
- `appearance_count DESC`로 정렬된 페르소나 목록
- 모든 필드가 있는 페르소나 dict 반환

**`async persona_create(project_id: int, name: str, **kwargs) -> dict`**
- 캐릭터 페르소나 생성
- 선택적 kwargs: `aliases`, `personality`, `speech_style`, `formality_level`, `age_group`, `example_dialogues`, `notes`, `auto_detected`, `detection_confidence`, `source_chapter_id`
- 페르소나 dict 반환

**`async persona_update(persona_id: int, **kwargs) -> dict`**
- 페르소나 필드 업데이트

**`async persona_delete(persona_id: int) -> dict`**
- 페르소나와 모든 제안 삭제 (캐스케이드)
- `{"deleted": true, "id": persona_id}` 반환

**파이프라인 메서드:**

**`async pipeline_translate_chapter(chapter_id: int, target_language: str = "en", **kwargs) -> dict`**
- 번역 파이프라인 시작
- `graph.py`에서 `run_translation_pipeline()` 실행
- `send_progress` 콜백을 통해 진행 상황 알림 전송
- 반환:
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
- 실행 중인 파이프라인 취소 (TODO: 아직 구현되지 않음)
- `{"cancelled": true}` 반환

**메서드 레지스트리:**

**`get_all_handlers() -> dict[str, Any]`**
- 메서드 이름을 핸들러 함수에 매핑하는 dict 반환
- 시작 중 `JsonRpcServer.run()`에서 호출
- 도메인별로 구성된 총 25개 메서드:
  - 건강: `health.check`
  - 설정: `config.set_keys`, `config.get_keys`, `config.test_provider`
  - 프로젝트: `project.list`, `project.create`, `project.get`, `project.update`, `project.delete`
  - 챕터: `chapter.list`, `chapter.create`, `chapter.get`, `chapter.update`, `chapter.delete`, `chapter.get_editor_data`
  - 용어집: `glossary.list`, `glossary.create`, `glossary.update`, `glossary.delete`
  - 페르소나: `persona.list`, `persona.create`, `persona.update`, `persona.delete`
  - 파이프라인: `pipeline.translate_chapter`, `pipeline.cancel`

### 2. 데이터베이스 계층 (`db/`)

#### `models.py` — 10개 테이블

모든 모델은 `Base(DeclarativeBase)`에서 상속하고 타입 안전성을 위해 SQLAlchemy 2.0 `Mapped` 타입 사용.

**열거형:**

**`TranslationStatus(str, enum.Enum)`**
- `PENDING`: 아직 번역되지 않음
- `TRANSLATING`: 번역 진행 중
- `TRANSLATED`: 번역 완료
- `REVIEWED`: 품질 검토 통과
- `APPROVED`: 사용자 승인

**`PipelineStatus(str, enum.Enum)`**
- `PENDING`: 파이프라인 시작하지 않음
- `RUNNING`: 파이프라인 진행 중
- `COMPLETED`: 파이프라인 성공적으로 완료
- `FAILED`: 파이프라인 오류 발생
- `CANCELLED`: 사용자가 취소

**테이블:**

**1. `Project`**

번역 프로젝트 (예: 소설).

필드:
- `id: int` (PK)
- `name: str(255)` — 프로젝트 제목
- `description: str | None` (Text) — 선택적 설명
- `source_language: str(10)` — 기본 `"ko"` (한국어)
- `target_language: str(10) | None` — 기본 `"en"` (영어)
- `genre: str(50) | None` — 예: "판타지", "로맨스"
- `style_settings: dict | None` (JSON) — 사용자 정의 번역 스타일 선호도
- `pipeline_type: str(30)` — 기본 `"cot_batch"` (Chain-of-Thought 배치)
- `llm_provider: str(20)` — 기본 `"gemini"` (`"claude"`, `"openai"`)
- `created_at: datetime` — 삽입 시 자동 설정
- `updated_at: datetime` — 변경 시 자동 업데이트

관계:
- `chapters: List[Chapter]` — 일대다 (캐스케이드 삭제)
- `glossary_entries: List[GlossaryEntry]` — 일대다 (캐스케이드 삭제)
- `personas: List[Persona]` — 일대다 (캐스케이드 삭제)
- `exports: List[Export]` — 일대다 (캐스케이드 삭제)

**2. `Chapter`**

프로젝트 내의 챕터.

필드:
- `id: int` (PK)
- `project_id: int` (FK → `projects.id`, 캐스케이드 삭제)
- `title: str(255)` — 챕터 제목
- `order: int` — 표시 순서 (기본 0)
- `source_content: str | None` (Text) — 원본 텍스트
- `file_path: str(512) | None` — 선택적 파일 가져오기 경로
- `translated_content: str | None` (Text) — 내보내기를 위해 캐시된 연결된 산문
- `translation_stale: bool` — 기본 `True`; 완료 후 `False` 설정
- `created_at: datetime`
- `updated_at: datetime`

관계:
- `project: Project` — 다대일
- `segments: List[Segment]` — 일대다 (캐스케이드 삭제)
- `translation_batches: List[TranslationBatch]` — 일대다 (캐스케이드 삭제)
- `pipeline_runs: List[PipelineRun]` — 일대다 (캐스케이드 삭제)
- `exports: List[Export]` — 일대다 (캐스케이드 삭제)
- `personas_last_seen: List[Persona]` — 이 챕터에서 마지막으로 본 페르소나

**3. `Segment`**

번역 가능한 단위 (문장, 단락, 대화 줄).

필드:
- `id: int` (PK)
- `chapter_id: int` (FK → `chapters.id`, 캐스케이드 삭제)
- `order: int` — 세그먼트 순서 번호
- `source_text: str` (Text, 필수) — 원본 세그먼트 텍스트
- `source_start_offset: int | None` — `chapter.source_content`의 문자 오프셋
- `source_end_offset: int | None` — 종료 오프셋
- `translated_text: str | None` (Text) — **레거시 필드** (v1 호환성)
- `status: TranslationStatus` — 기본 `PENDING` (**레거시**)
- `speaker: str(100) | None` — 대화를 위해 감지된 화자
- `segment_type: str(50)` — 기본 `"narrative"` (`"dialogue"`, `"action"`, `"thought"`)
- `extra_data: dict | None` (JSON) — 확장 가능한 메타데이터
- `created_at: datetime`
- `updated_at: datetime`

인덱스:
- `ix_segments_chapter_order` on `(chapter_id, order)`

관계:
- `chapter: Chapter` — 다대일
- `translations: List[Translation]` — 일대다 (캐스케이드 삭제)

**4. `Translation`**

각 세그먼트의 언어별 번역 (v2.0 다국어 지원).

필드:
- `id: int` (PK)
- `segment_id: int` (FK → `segments.id`, 캐스케이드 삭제)
- `target_language: str(10)` — 예: `"en"`, `"ja"`, `"zh"`
- `translated_text: str | None` (Text) — 번역된 세그먼트
- `translated_start_offset: int | None` — 연결된 번역 텍스트의 오프셋
- `translated_end_offset: int | None` — 종료 오프셋
- `manually_edited: bool` — 기본 `False`; `True`이면 재번역으로부터 보호
- `status: TranslationStatus` — 기본 `PENDING`
- `batch_id: int | None` (FK → `translation_batches.id`, 삭제 시 null 설정)
- `created_at: datetime`
- `updated_at: datetime`

제약 조건:
- 고유: `(segment_id, target_language)`

인덱스:
- `ix_translations_segment_lang` on `(segment_id, target_language)`

관계:
- `segment: Segment` — 다대일
- `batch: TranslationBatch | None` — 다대일

**5. `TranslationBatch`**

배치 CoT 추론과 리뷰 피드백 저장.

필드:
- `id: int` (PK)
- `chapter_id: int` (FK → `chapters.id`, 캐스케이드 삭제)
- `target_language: str(10)` — 대상 언어
- `batch_order: int` — 챕터 내 순서 번호
- `situation_summary: str | None` (Text) — LLM의 컨텍스트 요약
- `character_events: dict | None` (JSON) — 캐릭터 행동/감정
- `full_cot_json: dict | None` (JSON) — 완전한 CoT 추론
- `segment_ids: list | None` (JSON) — 이 배치의 세그먼트 ID 배열
- `review_feedback: dict | None` (JSON) — 리뷰어 에이전트 피드백
- `review_iteration: int` — 기본 0; 재번역 시 증가
- `created_at: datetime`

관계:
- `chapter: Chapter` — 다대일
- `translations: List[Translation]` — 일대다
- `persona_suggestions: List[PersonaSuggestion]` — 일대다

**6. `GlossaryEntry`**

일관된 번역을 위한 용어 용어집.

필드:
- `id: int` (PK)
- `project_id: int` (FK → `projects.id`, 캐스케이드 삭제)
- `source_term: str(255)` — 원본 용어
- `translated_term: str(255)` — 선호하는 번역
- `term_type: str(50)` — 기본 `"general"` (`"name"`, `"place"`, `"item"`, 등)
- `notes: str | None` (Text) — 사용 노트
- `context: str | None` (Text) — 예제 컨텍스트
- `auto_detected: bool` — 기본 `False`; 파이프라인에서 발견되면 `True`
- `created_at: datetime`

인덱스:
- `ix_glossary_project_term` on `(project_id, source_term)`

관계:
- `project: Project` — 다대일

**7. `Persona`**

대화 번역에서 일관된 음성을 위한 캐릭터 페르소나.

필드:
- `id: int` (PK)
- `project_id: int` (FK → `projects.id`, 캐스케이드 삭제)
- `name: str(255)` — 캐릭터 이름
- `aliases: list | None` (JSON) — 대체 이름
- `personality: str | None` (Text) — 성격 설명
- `speech_style: str | None` (Text) — 말하는 방식
- `formality_level: int` — 기본 3 (1=매우 비격식, 5=매우 격식)
- `age_group: str(50) | None` — 예: `"child"`, `"adult"`, `"elderly"`
- `example_dialogues: list | None` (JSON) — 샘플 대사
- `notes: str | None` (Text) — 추가 컨텍스트
- `auto_detected: bool` — 기본 `False`
- `detection_confidence: float | None` — LLM 신뢰도 점수
- `source_chapter_id: int | None` (FK → `chapters.id`, 삭제 시 null 설정) — 첫 등장
- `appearance_count: int` — 기본 0; 각 등장마다 증가
- `last_seen_chapter_id: int | None` (FK → `chapters.id`, 삭제 시 null 설정) — 최근 등장
- `created_at: datetime`
- `updated_at: datetime`

관계:
- `project: Project` — 다대일
- `suggestions: List[PersonaSuggestion]` — 일대다 (캐스케이드 삭제)
- `source_chapter: Chapter | None` — 다대일
- `last_seen_chapter: Chapter | None` — 다대일

**8. `PersonaSuggestion`**

승인 대기 중인 LLM이 제안한 페르소나 업데이트.

필드:
- `id: int` (PK)
- `persona_id: int` (FK → `personas.id`, 캐스케이드 삭제)
- `field_name: str(50)` — 업데이트할 필드 (예: `"personality"`, `"speech_style"`)
- `suggested_value: str | None` (Text) — 제안된 새 값
- `confidence: float | None` — LLM 신뢰도 (0.0-1.0)
- `source_batch_id: int | None` (FK → `translation_batches.id`, 삭제 시 null 설정)
- `status: str(20)` — 기본 `"pending"` (`"approved"`, `"rejected"`)
- `created_at: datetime`

관계:
- `persona: Persona` — 다대일
- `source_batch: TranslationBatch | None` — 다대일

**9. `PipelineRun`**

파이프라인 실행을 위한 감사 추적.

필드:
- `id: int` (PK)
- `chapter_id: int` (FK → `chapters.id`, 캐스케이드 삭제)
- `target_language: str(10)` — 대상 언어
- `status: PipelineStatus` — 기본 `PENDING`
- `started_at: datetime | None` — 파이프라인 시작 시간
- `completed_at: datetime | None` — 파이프라인 종료 시간
- `error_message: str | None` (Text) — 실패 시 오류 세부정보
- `config: dict | None` (JSON) — 파이프라인 구성 스냅샷
- `stats: dict | None` (JSON) — 실행 통계:
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

인덱스:
- `ix_pipeline_runs_chapter_status` on `(chapter_id, status)`

관계:
- `chapter: Chapter` — 다대일

**10. `Export`**

내보낸 파일 추적.

필드:
- `id: int` (PK)
- `chapter_id: int` (FK → `chapters.id`, 캐스케이드 삭제)
- `project_id: int` (FK → `projects.id`, 캐스케이드 삭제)
- `format: str(10)` — 예: `"txt"`, `"docx"`
- `file_path: str(512)` — 내보낸 파일의 전체 경로
- `created_at: datetime`

인덱스:
- `ix_exports_chapter_format` on `(chapter_id, format)`

관계:
- `chapter: Chapter` — 다대일
- `project: Project` — 다대일

#### `session.py` — 연결 관리

**`get_db_path() -> str`**
- SQLite 데이터베이스 파일 경로 반환
- 기본: `~/.fiction-translator/data.db`
- 누락된 경우 부모 디렉토리 생성
- 환경 변수 `FT_DATABASE_PATH`로 재정의

**`get_engine() -> Engine`**
- 전역 SQLAlchemy 엔진 가져오기 또는 생성
- 싱글톤 패턴 (`_engine`에 캐시)
- 연결 인수: `check_same_thread=False` (다중 스레드 접근 허용)
- `echo=False` (SQL 로깅 비활성화)

**`get_session_factory() -> sessionmaker`**
- 세션 팩토리 가져오기 또는 생성
- 싱글톤 패턴 (`_SessionLocal`에 캐시)
- 구성: `autocommit=False, autoflush=False`

**`get_db() -> Session`**
- 새 데이터베이스 세션 생성
- **호출자가 세션을 닫아야 함**
- 패턴:
  ```python
  db = get_db()
  try:
      # ... 쿼리/수정 ...
  finally:
      db.close()
  ```

**`init_db()`**
- 존재하지 않으면 모든 테이블 생성
- `main()` 시작 중 한 번 호출
- `Base.metadata.create_all()` 사용

### 3. 서비스 계층 (`services/`)

서비스 함수는 원시 ORM 쿼리 위에 비즈니스 로직 제공.

#### `project_service.py`

**`list_projects(db: Session) -> list[dict]`**
- 챕터 수와 함께 모든 프로젝트 목록
- `updated_at DESC`로 정렬
- 반환:
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
- 새 프로젝트 생성
- 선택적 kwargs: `description`, `genre`, `style_settings`, `pipeline_type`, `llm_provider`
- 커밋하고 프로젝트 dict 반환

**`get_project(db: Session, project_id: int) -> dict`**
- 단일 프로젝트 가져오기
- 찾을 수 없으면 `ValueError` 발생
- 프로젝트 dict 반환

**`update_project(db: Session, project_id: int, **kwargs) -> dict`**
- 프로젝트 필드 업데이트 (`id` 제외)
- 커밋하고 업데이트된 dict 반환

**`delete_project(db: Session, project_id: int) -> dict`**
- 프로젝트 삭제 (모든 챕터/세그먼트/번역/용어집/페르소나로 캐스케이드)
- 커밋하고 `{"deleted": True, "id": project_id}` 반환

**`_project_to_dict(p: Project) -> dict`**
- `Project` 모델을 dict로 변환
- ISO 형식 datetime 필드

#### `chapter_service.py`

**`list_chapters(db: Session, project_id: int) -> list[dict]`**
- 프로젝트의 챕터 목록
- `segment_count` 및 `translated_count` (대기 중이 아닌 번역) 포함
- `order`로 정렬

**`create_chapter(db: Session, project_id: int, title: str, source_content: str = "", **kwargs) -> dict`**
- 새 챕터 생성
- 다음 `order` 번호 자동 할당
- 선택적 kwargs: `file_path`
- 커밋하고 챕터 dict 반환

**`get_chapter(db: Session, chapter_id: int) -> dict`**
- 단일 챕터 가져오기
- 찾을 수 없으면 `ValueError` 발생

**`update_chapter(db: Session, chapter_id: int, **kwargs) -> dict`**
- 챕터 필드 업데이트
- 커밋하고 업데이트된 dict 반환

**`delete_chapter(db: Session, chapter_id: int) -> dict`**
- 챕터 삭제 (세그먼트/번역으로 캐스케이드)
- `{"deleted": True, "id": chapter_id}` 반환

**`get_editor_data(db: Session, chapter_id: int, target_language: str = "en") -> dict`**
- 편집기를 위한 연결된 텍스트 뷰 빌드
- 세그먼트를 번역과 조인
- 클릭하여 강조 표시를 위한 문자 오프셋 계산
- 반환:
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
- 세그먼트가 없으면 `chapter.source_content`에서 `source_connected_text` 반환

**`_chapter_to_dict(ch: Chapter) -> dict`**
- `Chapter` 모델을 dict로 변환
- ISO 형식 datetime 필드

#### `glossary_service.py`

**`list_glossary(db: Session, project_id: int) -> list[dict]`**
- `source_term`으로 정렬된 용어집 항목 목록

**`create_glossary_entry(db: Session, project_id: int, source_term: str, translated_term: str, **kwargs) -> dict`**
- 용어집 항목 생성
- 선택적 kwargs: `term_type`, `notes`, `context`, `auto_detected`
- 커밋하고 항목 dict 반환

**`get_glossary_entry(db: Session, entry_id: int) -> dict`**
- 단일 항목 가져오기
- 찾을 수 없으면 `ValueError` 발생

**`update_glossary_entry(db: Session, entry_id: int, **kwargs) -> dict`**
- 항목 필드 업데이트
- 커밋하고 업데이트된 dict 반환

**`delete_glossary_entry(db: Session, entry_id: int) -> dict`**
- 항목 삭제
- `{"deleted": True, "id": entry_id}` 반환

**`get_glossary_map(db: Session, project_id: int) -> dict[str, str]`**
- 용어집을 `{source_term: translated_term}` 매핑으로 가져오기
- 번역 프롬프트에 사용

**`bulk_import(db: Session, project_id: int, entries: list[dict]) -> dict`**
- 여러 항목 가져오기
- 각 항목: `{"source_term": str, "translated_term": str, ...}`
- `{"imported": count}` 반환

**`_entry_to_dict(e: GlossaryEntry) -> dict`**
- 모델을 dict로 변환

#### `persona_service.py`

**`list_personas(db: Session, project_id: int) -> list[dict]`**
- `appearance_count DESC`로 정렬된 페르소나 목록

**`create_persona(db: Session, project_id: int, name: str, **kwargs) -> dict`**
- 페르소나 생성
- 선택적 kwargs: `aliases`, `personality`, `speech_style`, `formality_level`, `age_group`, `example_dialogues`, `notes`, `auto_detected`, `detection_confidence`, `source_chapter_id`
- 커밋하고 페르소나 dict 반환

**`get_persona(db: Session, persona_id: int) -> dict`**
- 단일 페르소나 가져오기

**`update_persona(db: Session, persona_id: int, **kwargs) -> dict`**
- 페르소나 필드 업데이트

**`delete_persona(db: Session, persona_id: int) -> dict`**
- 페르소나와 모든 제안 삭제 (캐스케이드)

**`get_personas_context(db: Session, project_id: int) -> str`**
- 번역 프롬프트를 위한 마크다운 페르소나 컨텍스트 생성
- 형식:
  ```markdown
  ## 캐릭터 음성 가이드

  ### Alice (또한: Ally)
  - 성격: 용감하고 호기심 많음
  - 말투: 직접적, 비격식
  - 격식: 비격식
  - 연령대: 젊은 성인
  ```

**`list_suggestions(db: Session, persona_id: int) -> list[dict]`**
- 페르소나의 대기 중인 제안 목록

**`apply_suggestion(db: Session, suggestion_id: int, approve: bool = True) -> dict`**
- 제안 승인 또는 거부
- 승인되면 페르소나 필드 업데이트
- 목록 필드 (aliases, example_dialogues) 처리 (추가)
- 문자열 필드 처리 ("; " 구분 기호로 추가)
- 커밋하고 `{"id": suggestion_id, "status": "approved"/"rejected"}` 반환

**`increment_appearance(db: Session, persona_id: int, chapter_id: int)`**
- `appearance_count` 증가
- `last_seen_chapter_id` 업데이트
- 커밋

**`_persona_to_dict(p: Persona) -> dict`**
- 모델을 dict로 변환

#### `export_service.py`

**`export_chapter_txt(db: Session, chapter_id: int, target_language: str = "en") -> dict`**
- 챕터를 일반 텍스트로 내보내기
- 세그먼트를 번역과 조인
- `~/.fiction-translator/exports/{title}_{lang}_{timestamp}.txt`에 저장
- `Export` 테이블에 내보내기 기록
- `{"path": str, "format": "txt", "size": int}` 반환

**`export_chapter_docx(db: Session, chapter_id: int, target_language: str = "en") -> dict`**
- 챕터를 DOCX로 내보내기 (`python-docx` 필요)
- 챕터 제목을 제목으로 추가
- 화자 레이블로 대화 형식 지정
- `~/.fiction-translator/exports/{title}_{lang}_{timestamp}.docx`에 저장
- 내보내기 기록
- `{"path": str, "format": "docx"}` 반환

**`list_exports(db: Session, project_id: int) -> list[dict]`**
- `created_at DESC`로 정렬된 내보내기 목록

**`delete_export(db: Session, export_id: int) -> dict`**
- 내보내기 레코드 삭제
- 선택적으로 물리적 파일 삭제
- `{"deleted": True, "id": export_id, "file_deleted": bool}` 반환

### 4. 파이프라인 계층 (`pipeline/`)

#### `state.py` — 파이프라인 상태

LangGraph 상태 관리를 위한 TypedDict 정의. 모두 `total=False` 사용하여 노드가 부분 업데이트 반환 가능.

**`SegmentData(TypedDict, total=False)`**
- `id: int | None` — 저장되면 DB ID
- `order: int` — 순서 번호
- `text: str` — 세그먼트 텍스트
- `type: str` — `"narrative"`, `"dialogue"`, `"action"`, `"thought"`
- `speaker: str | None` — 대화를 위한 화자 이름
- `source_start_offset: int` — 원본의 문자 오프셋
- `source_end_offset: int` — 종료 오프셋

**`TranslatedSegment(TypedDict, total=False)`**
- `segment_id: int` — 순서/ID
- `order: int` — 순서 번호
- `source_text: str` — 원본 텍스트
- `translated_text: str` — 번역
- `type: str` — 세그먼트 타입
- `speaker: str | None`
- `translated_start_offset: int` — 연결된 번역의 오프셋
- `translated_end_offset: int`
- `batch_id: int | None` — 연결된 배치

**`BatchData(TypedDict, total=False)`**
- `batch_order: int` — 배치 순서
- `segment_ids: list[int]` — 이 배치의 ID
- `situation_summary: str` — CoT 컨텍스트 요약
- `character_events: list[dict]` — 캐릭터 행동/감정
- `translations: list[dict]` — `[{"segment_id": int, "text": str}]`
- `review_feedback: list[dict] | None` — 리뷰어 코멘트
- `review_iteration: int` — 재번역 횟수

**`TranslationState(TypedDict, total=False)`**

전체 파이프라인 상태 (카테고리별로 구성된 50+ 필드):

**입력:**
- `chapter_id: int`
- `project_id: int`
- `source_text: str`
- `source_language: str`
- `target_language: str`
- `llm_provider: str`
- `api_keys: dict[str, str]`

**컨텍스트 (DB에서 로드):**
- `glossary: dict[str, str]` — 용어 매핑
- `personas_context: str` — 마크다운 페르소나 가이드
- `style_context: str` — 스타일 선호도
- `existing_personas: list[dict]` — 알려진 페르소나

**분할:**
- `segments: list[SegmentData]`

**캐릭터 추출:**
- `detected_characters: list[dict]`

**검증:**
- `validation_passed: bool`
- `validation_errors: list[str]`
- `validation_attempts: int`

**번역:**
- `batches: list[BatchData]`
- `translated_segments: list[TranslatedSegment]`

**리뷰:**
- `review_passed: bool`
- `review_feedback: list[dict]`
- `review_iteration: int`
- `flagged_segments: list[int]` — 재번역이 필요한 ID

**페르소나 학습:**
- `persona_suggestions: list[dict]`

**출력:**
- `connected_translated_text: str` — 최종 산문
- `segment_map: list[dict]` — 오프셋 매핑

**파이프라인 메타데이터:**
- `pipeline_run_id: int | None`
- `progress_callback: Any` — 비동기 호출 가능
- `error: str | None`
- `total_tokens: int`
- `total_cost: float`

#### `graph.py` — 파이프라인 정의

**`build_translation_graph() -> StateGraph`**

LangGraph 파이프라인 구성. 노드와 엣지가 워크플로우 정의.

**파이프라인 흐름:**
```
load_context → segment → extract_characters → validate
    ↓ validation_passed?
    YES → translate
    NO, attempts < 3 → segment (재시도)
    NO, attempts >= 3 → translate (어쨌든 진행)

translate → review
    ↓ review_passed?
    YES → learn_personas
    NO, iteration < 2 → translate (플래그된 것 재번역)
    NO, iteration >= 2 → learn_personas (진행)

learn_personas → finalize → END
```

**노드:**

**`async load_context_node(state: TranslationState) -> dict`**
- DB에서 용어집, 페르소나, 설정 로드
- `{"glossary": dict, "personas_context": str, "existing_personas": list}` 반환

**`segmenter_node(state: TranslationState) -> dict`**
- `nodes/segmenter.py`에 구현
- `{"segments": list[SegmentData]}` 반환

**`character_extractor_node(state: TranslationState) -> dict`**
- `nodes/character_extractor.py`에 구현
- `{"detected_characters": list[dict]}` 반환

**`validator_node(state: TranslationState) -> dict`**
- `nodes/validator.py`에 구현
- `{"validation_passed": bool, "validation_errors": list, "validation_attempts": int}` 반환

**`translator_node(state: TranslationState) -> dict`**
- `nodes/translator.py`에 구현
- `{"batches": list[BatchData], "translated_segments": list[TranslatedSegment]}` 반환

**`reviewer_node(state: TranslationState) -> dict`**
- `nodes/reviewer.py`에 구현
- `{"review_passed": bool, "review_feedback": list, "review_iteration": int, "flagged_segments": list}` 반환

**`persona_learner_node(state: TranslationState) -> dict`**
- `nodes/persona_learner.py`에 구현
- `{"persona_suggestions": list[dict]}` 반환

**`async finalize_node(state: TranslationState) -> dict`**
- 번역된 세그먼트를 연결된 산문으로 조인
- segment_map을 위한 번역된 오프셋 계산
- DB에 지속:
  - `chapter.translated_content`에 연결된 텍스트 저장
  - 이 챕터의 이전 세그먼트/번역 지우기
  - 오프셋과 함께 새 세그먼트 저장
  - 오프셋과 함께 번역 저장
  - 배치 저장
  - 페르소나 제안 저장
  - 커밋
- `{"connected_translated_text": str, "segment_map": list[dict]}` 반환

**엣지:**

선형 엣지:
- `load_context → segment`
- `segment → extract_characters`
- `extract_characters → validate`
- `translate → review`
- `learn_personas → finalize`
- `finalize → END`

조건부 엣지 (`edges.py`에 정의):
- `validate → should_re_segment → {"translate", "segment"}`
- `review → should_re_translate → {"learn", "translate"}`

**`get_translation_graph() -> CompiledGraph`**
- 컴파일된 그래프 싱글톤 반환 (`_compiled_graph`에 캐시)
- 첫 호출 시 지연 초기화

**`async run_translation_pipeline(db, chapter_id: int, target_language: str = "en", api_keys: dict | None = None, progress_callback=None, **kwargs) -> dict`**

번역을 위한 고수준 진입점.

**단계:**
1. DB에서 챕터와 프로젝트 로드
2. 상태 `RUNNING`으로 `PipelineRun` 레코드 생성
3. 입력 매개변수로 초기 상태 빌드
4. `await graph.ainvoke(initial_state)`로 그래프 호출
5. 성공 시:
   - `PipelineRun`을 `COMPLETED`로 업데이트
   - 통계 저장
   - 결과 반환
6. 실패 시:
   - `PipelineRun`을 `FAILED`로 업데이트
   - 오류 메시지 저장
   - 예외 재발생

**반환:**
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

#### `edges.py` — 조건부 라우팅

**`should_re_segment(state: TranslationState) -> str`**
- 검증 후 호출
- 검증 통과 또는 최대 시도 도달 (3) 시 `"translate"` 반환
- 검증 실패 및 시도 < 3 시 `"segment"` 반환

**`should_re_translate(state: TranslationState) -> str`**
- 리뷰 후 호출
- 리뷰 통과 또는 최대 반복 도달 (2) 시 `"learn"` 반환
- 리뷰가 세그먼트를 플래그하고 반복 < 2 시 `"translate"` 반환

#### `callbacks.py` — 진행 상황 헬퍼

**`PIPELINE_STAGES: list[str]`**
- `["load_context", "segmentation", "character_extraction", "validation", "translation", "review", "persona_learning", "finalize"]`

**`stage_progress(stage: str) -> float`**
- 주어진 단계의 전체 진행 상황 (0.0-1.0) 가져오기
- 예: `"validation"` → 0.5 (8단계 중 절반)

**`async notify(callback: Any, stage: str, pct: float, message: str) -> None`**
- 존재하는 경우 진행 상황 콜백을 안전하게 호출
- 파이프라인 중단을 방지하기 위해 콜백 예외 삼킴

#### `nodes/` — 파이프라인 노드 구현

**`segmenter.py`**

**`async segmenter_node(state: TranslationState) -> dict`**

문자 오프셋과 함께 원본 텍스트를 번역 가능한 단위로 분할.

**접근 방식:**
1. **규칙 기반 분할** (항상 실행):
   - 단락 경계에서 분할 (이중 개행)
   - 언어별 정규식 패턴으로 대화 감지
   - 대화 마커에서 화자 추출
   - 각 세그먼트의 문자 오프셋 계산

2. **LLM 개선** (선택적, 10,000자 미만 텍스트):
   - 분할 프롬프트로 LLM에 텍스트 전송
   - JSON 응답을 세그먼트로 파싱
   - 오프셋을 계산하기 위해 원본에서 각 세그먼트의 텍스트 위치 지정

**언어 지원:**
- 한국어: `"..."`, `「...」` 대화 마커; `"라고 Alice"`, `Alice가 말했다` 같은 화자 패턴
- 일본어: `「...」`, `『...』` 괄호; `」とAlice`, `Aliceは言った` 같은 화자 패턴
- 중국어: `"..."` 따옴표; `"Alice说`, `Alice说："` 같은 화자 패턴
- 영어: `"..."`, `'...'` 따옴표; `said Alice`, `Alice said:` 같은 화자 패턴

**세그먼트 타입:**
- `narrative`: 기본 산문
- `dialogue`: 인용된 말
- `action`: 현재 자동 감지되지 않음 (향후)
- `thought`: 괄호 또는 작은 따옴표의 내적 독백

**반환:**
```python
{
    "segments": [
        {
            "id": None,
            "order": 0,
            "text": "그녀는 방으로 걸어 들어갔다.",
            "type": "narrative",
            "speaker": None,
            "source_start_offset": 0,
            "source_end_offset": 15
        },
        {
            "id": None,
            "order": 1,
            "text": "\"안녕하세요,\" 그녀가 부드럽게 말했다.",
            "type": "dialogue",
            "speaker": "그녀",
            "source_start_offset": 16,
            "source_end_offset": 38
        }
    ]
}
```

**`character_extractor.py`**

**`async character_extractor_node(state: TranslationState) -> dict`**

정규식 + 선택적 LLM 분석을 사용하여 캐릭터 추출.

**접근 방식:**
1. **패턴 기반 추출**:
   - 화자 이름을 위해 대화 세그먼트 스캔
   - 이미 설정된 경우 세그먼트의 `speaker` 필드 사용
   - 언어별 화자 감지 패턴 적용
   - `Counter`에서 발생 횟수 계산

2. **LLM 기반 추출** (선택적, API 키 사용 가능한 경우):
   - 모든 세그먼트 텍스트 연결 (8000자로 제한)
   - 캐릭터 추출 프롬프트로 LLM에 전송
   - JSON 파싱: `{"characters": [{"name": str, "role": str, "personality_hints": str, ...}]}`
   - 정규식 결과와 병합 (LLM이 우선)

3. **기존 페르소나와 병합**:
   - 이름 또는 별칭으로 DB 페르소나와 감지된 이름 매칭
   - 일치하는 경우 `persona_id` 및 `canonical_name` 추가

**반환:**
```python
{
    "detected_characters": [
        {
            "name": "Alice",
            "aliases": ["Ally"],
            "role": "main",
            "speaking_lines": 15,
            "personality_hints": "호기심 많고 용감함",
            "speech_style_hints": "직접적, 비격식",
            "source": "llm",
            "persona_id": 42,
            "canonical_name": "Alice"
        }
    ]
}
```

**`validator.py`**

**`async validator_node(state: TranslationState) -> dict`**

7가지 검사로 분할 품질 검증.

**검증 규칙:**
1. **비어 있지 않음**: 최소 하나의 세그먼트 필요
2. **빈 세그먼트 없음**: 모든 세그먼트에 비어 있지 않은 텍스트
3. **너무 큰 세그먼트 없음**: 세그먼트당 최대 10,000자
4. **유효한 오프셋**: 음수 아님, end >= start, 단조 증가
5. **커버리지**: 세그먼트가 원본 텍스트의 최소 80% 커버
6. **유효한 타입**: `{"narrative", "dialogue", "action", "thought"}` 중 타입
7. **화자 감지** (경고만): 대화 세그먼트는 이상적으로 화자 있어야 함

**반환:**
```python
{
    "validation_passed": True,
    "validation_errors": [],
    "validation_attempts": 1
}
```

검증 실패 시, 파이프라인은 `segmenter_node`로 다시 루프 (최대 3번 시도).

**`translator.py`**

**`async translator_node(state: TranslationState) -> dict`**

Chain-of-Thought 추론을 사용하여 배치로 세그먼트 번역.

**배치 그룹화:**
- 배치당 최대 20,000자
- 배치당 최대 10개 세그먼트
- 가능한 경우 대화 교환을 함께 유지

**번역 프로세스:**
1. 번역할 세그먼트 결정:
   - 전체 번역: 모든 세그먼트
   - 재번역 루프: `flagged_segments`만
2. 세그먼트를 배치로 그룹화
3. 각 배치에 대해:
   - 용어집, 페르소나, 스타일 컨텍스트로 CoT 번역 프롬프트 빌드
   - 재번역하는 경우 리뷰 피드백 포함
   - `generate_json()`을 통해 LLM에 전송
   - CoT 응답 파싱:
     ```python
     {
         "situation_summary": str,
         "character_events": [{"character": str, "emotion": str, "action": str}],
         "translations": [{"segment_id": int, "text": str}]
     }
     ```
   - `TranslatedSegment` 항목 생성
   - `BatchData` 저장

**재번역 시:**
- 새 번역을 이전 번역과 병합
- 플래그된 세그먼트만 교체
- 이전 반복의 다른 모든 세그먼트 보존

**반환:**
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

품질에 대한 번역 검토 및 재번역을 위한 세그먼트 플래그.

**리뷰 프로세스:**
1. 원본/번역 쌍 빌드
2. 쌍 청크 (토큰 제한을 피하기 위해 LLM 호출당 최대 30개)
3. 각 청크에 대해:
   - 쌍, 용어집, 페르소나로 리뷰 프롬프트 전송
   - JSON 응답 파싱:
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
4. 모든 플래그된 세그먼트 ID 수집
5. 플래그된 세그먼트를 위한 피드백 목록 빌드

**반환:**
```python
{
    "review_passed": True,  # 세그먼트가 플래그되면 False
    "review_feedback": [
        {
            "segment_id": 5,
            "issue": "용어집 용어 누락",
            "suggestion": "'sword' 대신 'magic sword' 사용"
        }
    ],
    "review_iteration": 1,
    "flagged_segments": [5, 12]
}
```

`review_passed=False` 및 `review_iteration < 2`이면 파이프라인은 `translator_node`로 다시 루프.

**`persona_learner.py`**

**`async persona_learner_node(state: TranslationState) -> dict`**

페르소나 업데이트를 위해 번역에서 캐릭터 통찰력 추출.

**학습 프로세스:**
1. 번역된 세그먼트를 연결된 텍스트로 조인
2. 페르소나 분석 프롬프트로 LLM에 전송
3. JSON 응답 파싱:
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
4. 제안 필터링:
   - 유효한 필드만
   - 신뢰도 >= 0.3
   - 가능한 경우 기존 페르소나와 매칭

**반환:**
```python
{
    "persona_suggestions": [
        {
            "name": "Alice",
            "persona_id": 42,
            "field": "speech_style",
            "value": "짧은 문장 사용, 축약 피함",
            "confidence": 0.85,
            "evidence": "12개 대화 세그먼트에서 관찰됨"
        }
    ]
}
```

제안은 사용자 검토를 위해 `finalize_node`의 `PersonaSuggestion` 테이블에 저장됨.

### 5. LLM 계층 (`llm/`)

#### `providers.py` — 제공자 추상화

**`LLMResponse` (dataclass)**
- `text: str` — 생성된 텍스트
- `model: str` — 사용된 모델 ID
- `usage: dict` — 토큰 수 (`{"prompt_tokens": int, "completion_tokens": int}`)
- `raw_response: Any | None` — 디버깅을 위한 전체 API 응답

**`LLMProvider` (ABC)**

LLM 제공자를 위한 추상 기본 클래스.

**`async generate(prompt: str, system_prompt: str | None = None, temperature: float = 0.3, max_tokens: int = 4096) -> LLMResponse`**
- 텍스트 완성 생성
- 서브클래스에서 구현해야 함

**`async generate_json(prompt: str, system_prompt: str | None = None, temperature: float = 0.2, max_tokens: int = 4096) -> dict`**
- JSON 응답 생성 및 파싱
- 시스템 프롬프트에 "유효한 JSON으로만 응답." 추가
- 마크다운 코드 블록 제거 (````json ... ````)
- JSON 파싱 실패 시 `ValueError` 발생

**`is_available() -> bool`**
- 제공자가 구성되었는지 확인 (API 키 있음)
- 서브클래스에서 구현해야 함

**`GeminiProvider(LLMProvider)`**

Google Gemini API 제공자.

**생성자: `__init__(api_key: str, model: str = "gemini-2.0-flash")`**
- 기본 모델: `gemini-2.0-flash` (빠르고 저렴)
- 대안: `gemini-1.5-pro` (더 유능함)

**`async generate(...) -> LLMResponse`**
- 엔드포인트: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}`
- 요청 형식:
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
- 응답 파싱: `data["candidates"][0]["content"]["parts"][0]["text"]`
- `usageMetadata`에서 사용량 추출

**`ClaudeProvider(LLMProvider)`**

Anthropic Claude API 제공자.

**생성자: `__init__(api_key: str, model: str = "claude-sonnet-4-5-20250929")`**
- 기본 모델: `claude-sonnet-4-5-20250929`
- 대안: `claude-opus-4` (가장 유능함)

**`async generate(...) -> LLMResponse`**
- 엔드포인트: `POST https://api.anthropic.com/v1/messages`
- 헤더: `x-api-key`, `anthropic-version: 2023-06-01`
- 요청 형식:
  ```python
  {
      "model": str,
      "max_tokens": int,
      "temperature": float,
      "messages": [{"role": "user", "content": prompt}],
      "system": system_prompt  # 선택적
  }
  ```
- 응답 파싱: `data["content"][0]["text"]`

**`OpenAIProvider(LLMProvider)`**

OpenAI GPT API 제공자.

**생성자: `__init__(api_key: str, model: str = "gpt-4o")`**
- 기본 모델: `gpt-4o` (GPT-4 Omni)
- 대안: `gpt-4-turbo`, `gpt-3.5-turbo`

**`async generate(...) -> LLMResponse`**
- 엔드포인트: `POST https://api.openai.com/v1/chat/completions`
- 헤더: `Authorization: Bearer {api_key}`
- 요청 형식:
  ```python
  {
      "model": str,
      "messages": [
          {"role": "system", "content": system_prompt},  # 선택적
          {"role": "user", "content": prompt}
      ],
      "temperature": float,
      "max_tokens": int
  }
  ```
- 응답 파싱: `data["choices"][0]["message"]["content"]`

**팩토리 함수:**

**`get_llm_provider(provider_name: str = "gemini", api_keys: dict[str, str] | None = None, model: str | None = None) -> LLMProvider`**
- LLM 제공자 인스턴스 생성
- `provider_name`: `"gemini"`, `"claude"`, `"openai"`
- `api_keys`: 제공자 이름을 API 키에 매핑
  - 별칭 허용: `"google"` → `"gemini"`, `"anthropic"` → `"claude"`
- `model`: 선택적 모델 재정의
- 제공자를 알 수 없거나 API 키가 누락된 경우 `ValueError` 발생

**`get_available_providers(api_keys: dict[str, str]) -> list[str]`**
- API 키가 구성된 제공자 목록 반환
- 예: `["gemini", "openai"]`

**제공자 레지스트리:**
```python
PROVIDERS = {
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
}
```

#### `prompts/` — 프롬프트 빌더

각 프롬프트 빌더는 특정 파이프라인 단계를 위한 시스템 및 사용자 프롬프트를 구성합니다. 이들은 파이프라인 노드에서 참조되지만 실제 구현 세부 정보는 별도 파일에 있을 것입니다:

- `segmentation.py` — `build_segmentation_prompt()`
- `character_extraction.py` — `build_character_extraction_prompt()`
- `validation.py` — (필요 없음; 검증은 결정론적)
- `cot_translation.py` — `build_cot_translation_prompt()`
- `review.py` — `build_review_prompt()`
- `persona_analysis.py` — `build_persona_analysis_prompt()`

## 데이터 흐름

### 번역 파이프라인 흐름 (엔드투엔드)

```
사용자가 React UI에서 "번역" 클릭
    ↓
api.translateChapter(chapterId, targetLanguage)
    ↓
Tauri invoke("rpc_call", {method: "pipeline.translate_chapter", params: {chapter_id: 123, target_language: "en"}})
    ↓
Rust sidecar.call("pipeline.translate_chapter", params)
    ↓
Python stdin이 JSON-RPC 요청 수신
    ↓
JsonRpcServer가 요청 파싱
    ↓
Dispatcher가 pipeline_translate_chapter(chapter_id=123, target_language="en") 호출
    ↓
Handler가 DB 세션 열고, run_translation_pipeline() 호출
    ↓
run_translation_pipeline():
    1. PipelineRun 레코드 생성 (status=RUNNING)
    2. 초기 상태 빌드
    3. LangGraph 호출:

       load_context:
           - DB에서 용어집 로드
           - DB에서 페르소나 로드
           - {"glossary": {...}, "personas_context": "...", "existing_personas": [...]} 반환

       segment:
           - 규칙 기반: 단락으로 분할, 대화 감지
           - 선택적 LLM 개선
           - 문자 오프셋 계산
           - {"segments": [...]} 반환

       extract_characters:
           - 정규식: 대화에서 화자 추출
           - 선택적 LLM: 더 깊은 캐릭터 분석
           - 기존 페르소나와 병합
           - {"detected_characters": [...]} 반환

       validate:
           - 7가지 검증 규칙 확인
           - {"validation_passed": bool, "validation_errors": [...], "validation_attempts": 1} 반환
           - 실패하고 시도 < 3이면 → segment로 루프
           - 그렇지 않으면 → translate로 진행

       translate:
           - 세그먼트를 배치로 그룹화 (최대 10개 세그먼트, 20k자)
           - 각 배치에 대해:
               * 용어집, 페르소나, 스타일로 CoT 프롬프트 빌드
               * LLM generate_json() 호출
               * {"situation_summary": "...", "character_events": [...], "translations": [...]} 파싱
               * TranslatedSegment 항목 생성
           - {"batches": [...], "translated_segments": [...]} 반환
           - 진행 상황 알림 전송: await send_progress("translation", 0.5, "배치 3/6 번역 중...")

       review:
           - 원본/번역 쌍 빌드
           - 30개씩 청크
           - 각 청크에 대해:
               * 리뷰 프롬프트 빌드
               * LLM generate_json() 호출
               * {"overall_passed": bool, "segment_reviews": [...]} 파싱
           - 플래그된 세그먼트 ID 수집
           - {"review_passed": bool, "review_feedback": [...], "flagged_segments": [...]} 반환
           - review_passed=False이고 iteration < 2이면 → translate로 루프 (플래그된 것만 재번역)
           - 그렇지 않으면 → learn_personas로 진행

       learn_personas:
           - 번역된 세그먼트를 텍스트로 조인
           - 페르소나 분석 프롬프트 빌드
           - LLM generate_json() 호출
           - {"persona_updates": [...]} 파싱
           - 필터링하고 기존 페르소나와 매칭
           - {"persona_suggestions": [...]} 반환

       finalize:
           - 번역된 세그먼트를 연결된 산문으로 조인
           - segment_map을 위한 번역된 오프셋 계산
           - DB에 저장:
               * chapter.translated_content = connected_text
               * 이전 세그먼트/번역 지우기
               * 원본 오프셋과 함께 새 세그먼트 저장
               * 번역된 오프셋과 함께 번역 저장
               * 배치 저장
               * 페르소나 제안 저장
           - {"connected_translated_text": "...", "segment_map": [...]} 반환

    4. PipelineRun 업데이트 (status=COMPLETED, stats={...})
    5. 결과 dict 반환

    ↓
Handler가 DB 세션 닫고, 결과 반환
    ↓
JsonRpcServer가 stdout에 JSON-RPC 응답 작성
    ↓
Rust가 응답 수신, 역직렬화
    ↓
Tauri resolve(result)
    ↓
React가 결과 수신, UI 업데이트
```

**진행 상황 알림** (병렬 스트림):
```
Python: await send_progress("translation", 0.3, "배치 2/6 번역 중...")
    ↓
JsonRpcServer.send_notification("pipeline.progress", {stage: "translation", progress: 0.3, message: "..."})
    ↓
Python이 stdout에 JSON-RPC 알림 작성
    ↓
Rust 사이드카가 이벤트 발생
    ↓
Tauri listen("pipeline.progress")
    ↓
React가 진행 표시줄 업데이트
```

### CRUD 흐름 (예: 프로젝트 목록)

```
React: const projects = await api.listProjects()
    ↓
Tauri invoke("rpc_call", {method: "project.list", params: {}})
    ↓
Rust sidecar.call("project.list", {})
    ↓
Python stdin 수신: {"jsonrpc": "2.0", "id": 1, "method": "project.list", "params": {}}
    ↓
JsonRpcServer 파싱 → JsonRpcRequest
    ↓
Dispatcher: handler = handlers["project.list"] → project_list()
    ↓
project_list():
    db = get_db()
    try:
        list_projects(db) →
            db.query(Project).order_by(Project.updated_at.desc()).all()
            각 프로젝트에 대해:
                챕터 수 계산
                dict 빌드
        [project dicts] 반환
    finally:
        db.close()
    ↓
Handler가 [{"id": 1, "name": "내 소설", ...}, ...] 반환
    ↓
JsonRpcServer가 JsonRpcResponse로 래핑: {"jsonrpc": "2.0", "id": 1, "result": [...]}
    ↓
Python이 stdout에 작성
    ↓
Rust가 수신, 역직렬화
    ↓
Tauri resolve([...])
    ↓
React가 프로젝트 배열 수신, ProjectList 렌더링
```

## 개발 워크플로우

**사이드카 독립 실행:**
```bash
cd sidecar
python -m fiction_translator
# stdin에서 읽고, stdout에 작성
# stdin을 닫고 종료하려면 Ctrl+D
```

**curl + jq로 테스트:**
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"health.check"}' | python -m fiction_translator | jq
```

**Tauri 앱과 함께 실행:**
```bash
cd .. # 저장소 루트
npm run tauri dev
# Tauri가 사이드카를 자동으로 실행
```

**독립 바이너리 빌드:**
```bash
cd sidecar
python build.py  # PyInstaller 사용
# 출력: dist/fiction-translator-sidecar (Windows에서는 .exe)
```

**데이터베이스 위치:**
- 개발: `~/.fiction-translator/data.db`
- 프로덕션: 동일 (사용자 홈 디렉토리)
- 재정의: `FT_DATABASE_PATH` 환경 변수 설정

**로그:**
- Python은 **stderr**로 로그 (stdout은 IPC용으로 예약됨)
- 로그 보기: `python -m fiction_translator 2>sidecar.log`
- 로그 레벨: `main.py`에서 설정 (`logging.basicConfig(level=logging.INFO)`)

## 문제 해결

**사이드카가 시작되지 않음:**
- Tauri 설정 확인: `src-tauri/tauri.conf.json` → `tauri.bundle.externalBin`
- 파일 권한 확인: `chmod +x dist/fiction-translator-sidecar`
- 로그 확인: Tauri 콘솔이 stderr 출력 표시

**번역 실패:**
- API 키 확인: `config.test_provider`가 성공 반환?
- DB 확인: 챕터에 `source_content`가 있는지?
- 로그 확인: stderr에서 Python 예외 찾기

**진행 상황 업데이트 안 됨:**
- `send_progress` 콜백이 `run_translation_pipeline`에 전달되었는지 확인
- Tauri 이벤트 리스너 확인: `listen("pipeline.progress", callback)`
- 네트워크 확인: 알림은 발사 후 망각, Tauri가 듣지 않으면 오류 없음

**데이터베이스 손상:**
- 백업: `cp ~/.fiction-translator/data.db ~/.fiction-translator/data.db.backup`
- 재설정: `rm ~/.fiction-translator/data.db` (다음 시작 시 재생성됨)
- 마이그레이션: (향후) Alembic 마이그레이션 사용

---

**한국어 문서 끝.**
