# Fiction Translator v2.0 — Tauri Rust 셸 문서

## 개요

Tauri Rust 셸은 React 프론트엔드와 Python 사이드카를 연결하는 "접착제" 역할을 합니다. 네이티브 윈도우를 관리하고, Python 프로세스를 생성하며, JSON-RPC 호출을 중계하고, 이벤트를 전달합니다.

**아키텍처 요약:**
- **프론트엔드 (React)**: UI 컴포넌트, 상태 관리 (Zustand), 사용자 상호작용
- **Rust 셸 (Tauri)**: 윈도우 관리, 프로세스 생명주기, IPC 라우팅
- **Python 사이드카**: 핵심 비즈니스 로직, LLM 통합, 번역 파이프라인

Rust 레이어는 의도적으로 얇게 설계되었습니다 — 인프라 관련 작업을 처리하면서 모든 비즈니스 로직은 Python에 위임합니다.

## 아키텍처 선택 이유

### 왜 Tauri인가? (Electron이 아닌)

| 측면 | Tauri | Electron |
|--------|-------|----------|
| **번들 크기** | ~15MB | ~150MB |
| **메모리 사용량** | 낮음 (시스템 웹뷰 공유) | 높음 (번들된 Chromium) |
| **성능** | 네이티브 Rust 백엔드 | Node.js 백엔드 |
| **보안** | 세밀한 권한 시스템 | 광범위한 권한 |
| **성숙도** | Tauri v2는 프로덕션 준비 완료 | 매우 성숙함 |

**주요 장점:**
- 10배 작은 번들 크기로 배포가 빠름
- 시스템 웹뷰로 메모리 사용량 감소
- Rust의 성능과 안전성 보장
- 활발히 개발 중인 현대적인 플러그인 생태계

### 왜 Rust를 셸로 사용하는가? (Node.js가 아닌)

1. **Tauri의 기본 언어**: Tauri의 코어는 Rust로 작성되어 자연스러운 선택
2. **강력한 프로세스 관리**: Rust의 비동기 런타임(Tokio)이 stdin/stdout/stderr를 가진 자식 프로세스 관리에 탁월
3. **타입 안전성**: serde를 통한 IPC 메시지 처리의 컴파일 타임 보장
4. **성능**: 제로 비용 추상화, 가비지 컬렉션 일시 정지 없음
5. **신뢰성**: Result 타입을 통한 강력한 에러 처리

### 왜 stdin/stdout IPC인가? (HTTP나 WebSocket이 아닌)

| 방식 | 장점 | 단점 |
|----------|------|------|
| **stdin/stdout** | 포트 충돌 없음, 단순함, 안전함, 프로세스 생명주기 연동 | 로컬 프로세스에서만 작동 |
| **HTTP** | 언어 독립적, 익숙함 | 포트 충돌, 서버 설정 필요, 네트워크 노출 |
| **WebSocket** | 양방향, 실시간 | HTTP와 유사한 문제 |

**stdin/stdout가 우위인 이유:**
- **가용성 보장**: stdin/stdout는 항상 존재하며 포트 충돌 없음
- **네이티브 Tauri 패턴**: 파이프를 통한 사이드카 통신이 관용적
- **단순성**: 줄 기반 JSON 프로토콜, 서버 설정 불필요
- **보안**: 네트워크 노출 없음, 프로세스 내부 통신만 가능
- **생명주기 바인딩**: 앱 종료 시 Python 프로세스 자동 종료

### 왜 얇은 Rust 셸인가?

**철학**: Rust 레이어를 최소화하고, 비즈니스 로직은 Python에 배치

**장점:**
- 빠른 반복: Python 변경 시 Rust 재컴파일 불필요
- 언어 선택: LLM 통합과 데이터 처리에는 Python이 더 적합
- 유지보수성: Rust 코드를 건드릴 일이 거의 없음
- 관심사 분리: 인프라(Rust) vs. 비즈니스 로직(Python)

**Rust의 책임:**
- 윈도우 생명주기 관리
- Python 프로세스 생성 및 모니터링
- JSON-RPC 메시지 라우팅
- 이벤트 전달

**Python의 책임:**
- 번역 파이프라인 실행
- LLM API 통합
- 데이터베이스 작업
- 파일 처리
- 모든 비즈니스 로직

## 디렉토리 구조

```
src-tauri/
├── Cargo.toml                  # Rust 의존성 및 패키지 메타데이터
├── tauri.conf.json             # Tauri 앱 설정 (윈도우, 빌드, 플러그인)
├── build.rs                    # 빌드 스크립트 (자동 생성)
├── capabilities/
│   └── default.json            # Tauri v2 권한 capabilities
└── src/
    ├── main.rs                 # 진입점 (최소화, lib::run() 호출)
    ├── lib.rs                  # 앱 빌더, 플러그인 등록, 설정 훅
    ├── sidecar.rs              # Python 프로세스 생명주기 관리
    ├── ipc.rs                  # JSON-RPC 메시지 타입 정의
    ├── commands.rs             # Tauri 커맨드 핸들러 (RPC 브릿지)
    ├── state.rs                # 공유 애플리케이션 상태
    └── events.rs               # 이벤트 타입 정의
```

## 모듈 문서

### main.rs — 진입점

```rust
fn main() {
    env_logger::init();
    fiction_translator_v2_lib::run();
}
```

**목적**: 로깅을 초기화하고 라이브러리에 위임하는 최소 진입점

**lib.rs와 분리한 이유:**
- 라이브러리를 바이너리와 라이브러리 양쪽으로 사용 가능
- Rust 바이너리 크레이트의 모범 사례 준수
- `#[cfg_attr(not(debug_assertions), windows_subsystem = "windows")]`는 릴리스 빌드에서 Windows 콘솔 창을 방지

### lib.rs — 앱 빌더

Tauri 애플리케이션 설정의 핵심입니다.

```rust
pub fn run() {
    env_logger::init();
    let app_state = AppState::new();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            commands::rpc_call,
            commands::sidecar_status,
        ])
        .setup(|app| {
            // 앱 준비 시 사이드카 생성
            tauri::async_runtime::spawn(async move {
                let state: State<'_, AppState> = handle.state();
                let mut sidecar = state.sidecar.lock().await;

                match sidecar.start(handle.clone()).await {
                    Ok(()) => {
                        log::info!("Sidecar started successfully");
                        // 헬스 체크
                        match sidecar.call("health.check", None).await {
                            Ok(result) => log::info!("Sidecar health: {:?}", result),
                            Err(e) => log::error!("Sidecar health check failed: {}", e),
                        }
                    }
                    Err(e) => {
                        log::error!("Failed to start sidecar: {}", e);
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**구성 요소:**

1. **플러그인 등록**
   - `.plugin(tauri_plugin_shell::init())`: 셸 명령어 및 사이드카 지원 활성화
   - 플러그인은 추가 기능 제공 (파일 시스템, HTTP 등)

2. **상태 관리**
   - `.manage(app_state)`: 모든 커맨드에서 `AppState` 사용 가능
   - `Arc<Mutex<T>>`를 통해 애플리케이션 전체에서 상태 공유

3. **커맨드 핸들러 등록**
   - `invoke_handler`: 프론트엔드에서 호출 가능한 커맨드 등록
   - `commands::rpc_call`: Python으로의 메인 RPC 브릿지
   - `commands::sidecar_status`: 헬스 체크 커맨드

4. **설정 훅**
   - 앱 준비 시 한 번 실행
   - Python 사이드카 시작을 위한 비동기 태스크 생성
   - `health.check` RPC 호출로 헬스 체크 수행
   - 에러는 로깅되지만 앱 시작을 막지 않음 (graceful degradation)

### sidecar.rs — 프로세스 생명주기 (가장 중요)

Rust 셸의 핵심입니다. Python 프로세스 생명주기를 관리하고 모든 IPC 통신을 처리합니다.

#### 데이터 구조

```rust
type PendingRequests = Arc<Mutex<HashMap<u64, oneshot::Sender<Result<Value, String>>>>>;

pub struct SidecarProcess {
    child: Option<Child>,                    // Python 프로세스 핸들
    stdin: Option<tokio::process::ChildStdin>,  // 요청 전송을 위한 stdin 파이프
    pending: PendingRequests,                // 요청 ID에서 응답 채널로의 맵
    connected: Arc<RwLock<bool>>,            // 연결 상태 플래그
}
```

**설계 노트:**
- `pending`: ID로 진행 중인 RPC 요청을 추적하여 비동기 요청/응답 매칭 가능
- `connected`: 여러 태스크에서 읽을 수 있는 공유 플래그로 연결 상태 확인
- `Arc<Mutex<T>>`는 비동기 태스크 간 안전한 공유 가능

#### 생성자

```rust
pub fn new() -> Self
```

실행 중인 프로세스가 없는 빈 `SidecarProcess`를 생성합니다.

#### 프로세스 시작

```rust
pub async fn start(&mut self, app_handle: tauri::AppHandle) -> Result<(), String>
```

**동작:**

1. **환경 감지**:
   - **개발 모드** (`cfg!(debug_assertions)`): `../sidecar/` 디렉토리에서 `python -m fiction_translator` 실행
   - **프로덕션**: `resources/binaries/fiction-translator-sidecar[.exe]`에서 번들된 바이너리 사용

2. **프로세스 생성**:
   - stdin/stdout/stderr를 파이프로 설정 (캡처됨)
   - Python 프로세스 생성
   - 파이프 핸들 추출

3. **백그라운드 태스크**:
   - **Stdout 리더**: JSON-RPC 응답 및 알림 파싱
   - **Stderr 리더**: Python의 stderr 출력 로깅

4. **상태 업데이트**:
   - `connected` 플래그를 `true`로 설정
   - 프론트엔드로 `sidecar:status` 이벤트 발생

**Stdout 리더 태스크** (78-115번째 줄):

```rust
tokio::spawn(async move {
    let reader = BufReader::new(stdout);
    let mut lines = reader.lines();

    while let Ok(Some(line)) = lines.next_line().await {
        // 응답으로 파싱 시도 ("id" 필드 있음)
        if let Ok(response) = serde_json::from_str::<JsonRpcResponse>(&line) {
            if let Some(id) = response.id {
                // 대기 중인 요청에 매칭하여 결과 전송
                let mut pending = pending.lock().await;
                if let Some(sender) = pending.remove(&id) {
                    let result = if let Some(error) = response.error {
                        Err(error.to_string())
                    } else {
                        Ok(response.result.unwrap_or(Value::Null))
                    };
                    let _ = sender.send(result);
                }
                continue;
            }
        }

        // 알림으로 파싱 시도 ("id" 필드 없음)
        if let Ok(notification) = serde_json::from_str::<JsonRpcNotification>(&line) {
            // Tauri 이벤트로 전달
            let event_name = notification.method.replace('.', ":");
            if let Some(params) = notification.params {
                let _ = app.emit(&event_name, params);
            }
        }
    }

    // 프로세스 종료
    *connected.write().await = false;
    let _ = app.emit("sidecar:status", serde_json::json!({"connected": false}));
});
```

**주요 동작:**
- stdout를 줄 단위로 읽음 (JSON-RPC 메시지는 개행 구분)
- **응답** (`id` 있음): ID를 통해 대기 중인 요청에 매칭
- **알림** (`id` 없음): Tauri 이벤트로 변환 (예: `pipeline.progress` → `pipeline:progress`)
- stdout 종료 시 (프로세스 사망), `connected = false` 설정 및 상태 이벤트 발생

**Stderr 리더 태스크** (118-125번째 줄):

```rust
tokio::spawn(async move {
    let reader = BufReader::new(stderr);
    let mut lines = reader.lines();

    while let Ok(Some(line)) = lines.next_line().await {
        info!("[sidecar] {}", line);
    }
});
```

단순: Python의 stderr를 Rust 로거로 전달합니다.

#### RPC 호출

```rust
pub async fn call(&mut self, method: &str, params: Option<Value>) -> Result<Value, String>
```

Python에 JSON-RPC 요청을 보내고 응답을 기다립니다.

**흐름:**

1. 자동 증가 ID로 `JsonRpcRequest` 생성
2. JSON으로 직렬화하고 개행 추가
3. 응답을 위한 oneshot 채널 생성
4. 송신자를 `pending` 맵에 저장 (요청 ID 키)
5. stdin에 요청 작성
6. stdin 플러시하여 전달 보장
7. 120초 타임아웃으로 응답 대기
8. 결과 또는 에러 반환

**타임아웃 동작:**
- 120초 후 응답이 없으면 대기 중인 요청을 제거하고 타임아웃 에러 반환
- 손실된 요청으로 인한 메모리 누수 방지

**예시:**
```rust
let result = sidecar.call("project.list", None).await?;
```

전송: `{"jsonrpc":"2.0","method":"project.list","id":1}\n`

수신: `{"jsonrpc":"2.0","id":1,"result":[...]}\n`

#### 프로세스 종료

```rust
pub async fn stop(&mut self)
```

Python 프로세스를 종료하고 상태를 정리합니다:
- `child.kill()`을 호출하여 프로세스 종료
- stdin 핸들 제거
- `connected = false` 설정

#### 연결 상태

```rust
pub async fn is_connected(&self) -> bool
```

연결 상태 플래그의 스레드 안전 읽기입니다.

### ipc.rs — 메시지 타입

JSON-RPC 2.0 프로토콜 타입을 정의합니다.

#### 요청 ID 생성

```rust
static REQUEST_ID: AtomicU64 = AtomicU64::new(1);

pub fn next_id() -> u64 {
    REQUEST_ID.fetch_add(1, Ordering::Relaxed)
}
```

스레드 안전 자동 증가 ID 생성기입니다. 1부터 시작하여 원자적으로 증가합니다.

#### JsonRpcRequest

```rust
#[derive(Debug, Serialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<Value>,
    pub id: u64,
}

impl JsonRpcRequest {
    pub fn new(method: &str, params: Option<Value>) -> Self
    pub fn to_line(&self) -> String  // JSON + "\n"으로 직렬화
}
```

**예시:**
```json
{"jsonrpc":"2.0","method":"project.list","params":null,"id":42}
```

#### JsonRpcResponse

```rust
#[derive(Debug, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: Option<u64>,
    pub result: Option<Value>,
    pub error: Option<JsonRpcError>,
}
```

**동작:**
- `id`가 있으면: 요청에 대한 응답
- `id`가 없으면: 알림 (`JsonRpcNotification`으로 파싱되어야 함)
- `result` 또는 `error` 중 하나만 있어야 함 (둘 다는 아님)

#### JsonRpcError

```rust
#[derive(Debug, Deserialize, Clone)]
pub struct JsonRpcError {
    pub code: i64,
    pub message: String,
    pub data: Option<Value>,
}

impl std::fmt::Display for JsonRpcError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "RPC Error {}: {}", self.code, self.message)
    }
}
```

표준 JSON-RPC 에러 객체입니다. `Display` 구현으로 쉬운 에러 출력이 가능합니다.

#### JsonRpcNotification

```rust
#[derive(Debug, Deserialize)]
pub struct JsonRpcNotification {
    pub method: String,
    pub params: Option<Value>,
}
```

응답을 기대하지 않는 Python의 메시지입니다 (`id` 필드 없음).

**예시:**
```json
{"jsonrpc":"2.0","method":"pipeline.progress","params":{"stage":"translation","progress":0.5}}
```

이것은 Tauri 이벤트로 변환됩니다: `pipeline:progress` (페이로드는 params)

### commands.rs — Tauri 커맨드 핸들러

프론트엔드에 두 개의 커맨드를 노출합니다.

#### rpc_call

```rust
#[tauri::command]
pub async fn rpc_call(
    state: State<'_, AppState>,
    method: String,
    params: Option<Value>,
) -> Result<Value, String>
```

**목적**: 프론트엔드와 Python 간의 메인 브릿지

**흐름:**
1. 사이드카 프로세스의 락 획득
2. `sidecar.call(method, params)` 호출
3. 결과 또는 에러를 프론트엔드로 반환

**프론트엔드 사용법:**
```typescript
const result = await invoke('rpc_call', {
  method: 'project.list',
  params: null
});
```

#### sidecar_status

```rust
#[tauri::command]
pub async fn sidecar_status(state: State<'_, AppState>) -> Result<bool, String>
```

**목적**: Python 사이드카가 실행 중인지 확인하는 헬스 체크

**반환**: 연결되어 있으면 `true`, 아니면 `false`

**프론트엔드 사용법:**
```typescript
const isConnected = await invoke('sidecar_status');
```

### state.rs — 애플리케이션 상태

```rust
pub struct AppState {
    pub sidecar: Arc<Mutex<SidecarProcess>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            sidecar: Arc::new(Mutex::new(SidecarProcess::new())),
        }
    }
}
```

**목적**: 모든 Tauri 커맨드에서 접근 가능한 공유 상태

**설계:**
- `Arc<Mutex<T>>`: 내부 가변성을 가진 스레드 안전 공유 소유권
- `Arc`: 여러 태스크가 동일한 상태에 대한 참조 보유 가능
- `Mutex`: RPC 호출 중 배타적 접근 보장

**접근 패턴:**
```rust
pub async fn some_command(state: State<'_, AppState>) -> Result<Value, String> {
    let mut sidecar = state.sidecar.lock().await;
    sidecar.call("method", None).await
}
```

### events.rs — 이벤트 타입 정의

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineProgressEvent {
    pub stage: String,
    pub progress: f64,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SidecarStatusEvent {
    pub connected: bool,
    pub error: Option<String>,
}
```

**목적**: 문서화 및 향후 타입 검사를 위한 타입 안전 이벤트 페이로드

**참고**: 이러한 타입은 현재 런타임에서 **강제되지 않음** (이벤트는 `serde_json::Value` 사용), 하지만 예상 구조를 문서화하며 향후 강력한 타입 지정에 사용 가능합니다.

**이벤트 이름:**
- `pipeline:progress`: 번역 파이프라인 실행 중 발생
- `sidecar:status`: 사이드카 연결 상태 변경 시 발생

## 데이터 흐름

### 요청 흐름 (프론트엔드 → 사이드카)

```
┌─────────────────────────────────────────────────────────────────────┐
│ React 프론트엔드                                                     │
│                                                                     │
│  api.listProjects()                                                │
│    ↓                                                                │
│  invoke("rpc_call", {                                              │
│    method: "project.list",                                         │
│    params: {}                                                      │
│  })                                                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ IPC
┌─────────────────────────────────────────────────────────────────────┐
│ Tauri Rust 셸                                                       │
│                                                                     │
│  commands::rpc_call()                                              │
│    ↓                                                                │
│  state.sidecar.lock().await                                        │
│    ↓                                                                │
│  sidecar.call("project.list", {})                                  │
│    ↓                                                                │
│  JsonRpcRequest {                                                  │
│    jsonrpc: "2.0",                                                 │
│    method: "project.list",                                         │
│    id: 42                                                          │
│  }                                                                 │
│    ↓                                                                │
│  stdin에 작성: {"jsonrpc":"2.0","method":"project.list","id":42}\n │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ stdin 파이프
┌─────────────────────────────────────────────────────────────────────┐
│ Python 사이드카                                                      │
│                                                                     │
│  JSON-RPC 서버가 stdin에서 줄 읽기                                  │
│    ↓                                                                │
│  요청 파싱                                                          │
│    ↓                                                                │
│  ProjectService.list_projects()로 라우팅                           │
│    ↓                                                                │
│  비즈니스 로직 실행                                                 │
│    ↓                                                                │
│  결과 반환                                                          │
│    ↓                                                                │
│  stdout에 작성:                                                     │
│    {"jsonrpc":"2.0","id":42,"result":[...]}\n                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ stdout 파이프
┌─────────────────────────────────────────────────────────────────────┐
│ Tauri Rust 셸                                                       │
│                                                                     │
│  Stdout 리더 태스크가 줄 읽기                                       │
│    ↓                                                                │
│  JsonRpcResponse로 파싱                                             │
│    ↓                                                                │
│  id=42를 대기 중인 요청에 매칭                                      │
│    ↓                                                                │
│  oneshot 채널로 결과 전송                                           │
│    ↓                                                                │
│  sidecar.call()이 결과 수신                                         │
│    ↓                                                                │
│  commands::rpc_call()이 Value 반환                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ IPC
┌─────────────────────────────────────────────────────────────────────┐
│ React 프론트엔드                                                     │
│                                                                     │
│  invoke()가 결과로 resolve                                         │
│    ↓                                                                │
│  api.listProjects()가 Project[] 반환                               │
│    ↓                                                                │
│  UI 업데이트                                                        │
└─────────────────────────────────────────────────────────────────────┘
```

**핵심 포인트:**
- 요청 ID (`42`)는 비동기 응답을 올바른 대기 중인 요청에 매칭하는 데 사용
- Mutex는 한 번에 하나의 RPC 호출만 stdin에 작성하도록 보장 (직렬화)
- 120초 타임아웃은 응답하지 않는 Python 프로세스에서 중단되는 것을 방지

### 이벤트 흐름 (사이드카 → 프론트엔드)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Python 사이드카                                                      │
│                                                                     │
│  파이프라인 실행 중:                                                │
│    await server.send_notification(                                 │
│      "pipeline.progress",                                          │
│      {                                                             │
│        "stage": "translation",                                     │
│        "progress": 0.5,                                            │
│        "message": "번역 중 배치 1/2"                                │
│      }                                                             │
│    )                                                               │
│    ↓                                                                │
│  stdout에 작성:                                                     │
│    {"jsonrpc":"2.0","method":"pipeline.progress","params":{...}}\n │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ stdout 파이프
┌─────────────────────────────────────────────────────────────────────┐
│ Tauri Rust 셸                                                       │
│                                                                     │
│  Stdout 리더 태스크가 줄 읽기                                       │
│    ↓                                                                │
│  JsonRpcResponse로 파싱 시도 ("id" 있음)                            │
│    → 실패 ("id" 필드 없음)                                          │
│    ↓                                                                │
│  JsonRpcNotification으로 파싱 시도 ("id" 없음)                      │
│    → 성공!                                                          │
│    ↓                                                                │
│  메서드 이름 변환:                                                  │
│    "pipeline.progress" → "pipeline:progress"                       │
│    ↓                                                                │
│  app_handle.emit("pipeline:progress", params)                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ Tauri 이벤트 시스템
┌─────────────────────────────────────────────────────────────────────┐
│ React 프론트엔드                                                     │
│                                                                     │
│  listen("pipeline:progress", (event) => {                          │
│    const { stage, progress, message } = event.payload;            │
│    usePipelineStore.getState().setProgress(stage, progress);      │
│  })                                                                │
│    ↓                                                                │
│  ProgressOverlay 컴포넌트 재렌더링                                  │
│    ↓                                                                │
│  사용자가 업데이트된 진행 표시줄과 메시지 확인                      │
└─────────────────────────────────────────────────────────────────────┘
```

**핵심 포인트:**
- 알림은 **`id` 필드 없음** (응답을 기대하지 않음)
- 메서드 이름은 Python에서 점 표기법 사용 (`pipeline.progress`)
- Tauri 이벤트용 콜론 표기법으로 변환 (`pipeline:progress`)
- 여러 리스너가 동일한 이벤트를 구독 가능

### 생명주기 흐름

```
┌─────────────────────────────────────────────────────────────────────┐
│ 앱 시작                                                             │
│                                                                     │
│  main()이 lib::run() 호출                                          │
│    ↓                                                                │
│  tauri::Builder::default()                                         │
│    .plugin(tauri_plugin_shell::init())                             │
│    .manage(AppState::new())                                        │
│    .invoke_handler(...)                                            │
│    .setup(|app| {                                                  │
│      // 비동기 태스크 생성                                         │
│      tauri::async_runtime::spawn(async move {                      │
│        let state = handle.state::<AppState>();                     │
│        let mut sidecar = state.sidecar.lock().await;               │
│                                                                     │
│        sidecar.start(handle.clone()).await?;                       │
│          ↓                                                          │
│          ┌─────────────────────────────────────────┐               │
│          │ 1. 환경 감지 (개발/프로덕션)           │               │
│          │ 2. Python 프로세스 생성                │               │
│          │ 3. stdin/stdout/stderr 캡처            │               │
│          │ 4. stdout 리더 태스크 생성             │               │
│          │ 5. stderr 리더 태스크 생성             │               │
│          │ 6. connected = true 설정               │               │
│          │ 7. "sidecar:status" 이벤트 발생        │               │
│          └─────────────────────────────────────────┘               │
│                                                                     │
│        // 헬스 체크                                                │
│        sidecar.call("health.check", None).await?;                  │
│      });                                                           │
│    })                                                              │
│    .run(...)                                                       │
│    ↓                                                                │
│  프론트엔드 로드 및 사이드카 연결                                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 정상 작동                                                           │
│                                                                     │
│  프론트엔드 → invoke("rpc_call") → Rust → Python → Rust → 프론트엔드│
│  Python → 알림 → Rust → 이벤트 → 프론트엔드                        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 앱 종료                                                             │
│                                                                     │
│  사용자가 윈도우 닫기                                               │
│    ↓                                                                │
│  Tauri가 정리 트리거                                                │
│    ↓                                                                │
│  Python 프로세스 종료 (자식 프로세스 종료)                          │
│    ↓                                                                │
│  Stdout 리더 태스크가 EOF 감지                                      │
│    ↓                                                                │
│  connected = false 설정                                             │
│    ↓                                                                │
│  앱 종료                                                            │
└─────────────────────────────────────────────────────────────────────┘
```

**에러 처리:**
- 사이드카 시작 실패 시: 에러 로깅, 앱은 계속 실행 (graceful degradation)
- 헬스 체크 실패 시: 경고 로깅, 앱은 계속 실행
- 작동 중 Python 크래시 시: `connected`가 `false`가 되고, 프론트엔드는 `sidecar_status` 커맨드로 감지 가능

## 설정

### tauri.conf.json

```json
{
  "productName": "Fiction Translator",
  "version": "2.0.0",
  "identifier": "com.fiction-translator.v2",
  "build": {
    "beforeDevCommand": "",
    "beforeBuildCommand": "npm run build",
    "devUrl": "http://localhost:1420",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "title": "Fiction Translator",
        "width": 1400,
        "height": 900,
        "minWidth": 800,
        "minHeight": 600,
        "resizable": true,
        "fullscreen": false
      }
    ],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [...]
  },
  "plugins": {
    "shell": {
      "scope": [
        {
          "name": "translator-sidecar",
          "sidecar": true,
          "args": true
        }
      ]
    }
  }
}
```

**주요 설정:**

- **identifier**: OS용 고유 앱 ID (`com.fiction-translator.v2`)
- **build.devUrl**: 개발 서버 URL (Vite는 포트 1420에서 실행)
- **build.frontendDist**: 프로덕션 빌드 출력 디렉토리
- **app.windows**: 기본 윈도우 설정
  - 1400x900 기본 크기
  - 최소 800x600
  - 크기 조절 가능, 전체 화면 아님
- **security.csp**: Content Security Policy 비활성화 (인라인 스크립트 허용)
- **plugins.shell**: 사이드카 바이너리 실행 허용

### capabilities/default.json

```json
{
  "identifier": "default",
  "description": "Fiction Translator용 기본 권한",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-execute",
    "shell:allow-open"
  ]
}
```

**권한:**

- `core:default`: 기본 Tauri 코어 기능 (윈도우 관리, 이벤트 등)
- `shell:allow-execute`: 셸 명령어 실행 허용 (사이드카에 필요)
- `shell:allow-open`: 기본 애플리케이션으로 파일/URL 열기 허용

**보안 참고**: 이러한 권한은 메인 윈도우에만 적용됩니다. Tauri v2의 capability 시스템은 프론트엔드가 할 수 있는 작업을 세밀하게 제어합니다.

### Cargo.toml

```toml
[package]
name = "fiction-translator-v2"
version = "2.0.0"
edition = "2021"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
log = "0.4"
env_logger = "0.11"

[lib]
name = "fiction_translator_v2_lib"
crate-type = ["staticlib", "cdylib", "rlib"]
```

**주요 의존성:**

- **tauri**: 핵심 Tauri 프레임워크 (v2)
- **tauri-plugin-shell**: 사이드카 지원을 위한 셸 플러그인
- **serde**: 직렬화/역직렬화 프레임워크
- **serde_json**: RPC 메시지를 위한 JSON 지원
- **tokio**: 비동기 런타임 (프로세스, io, sync 등을 위한 `full` 기능 포함)
- **log**: 로깅 파사드
- **env_logger**: 단순 로거 구현

**라이브러리 설정:**
- `staticlib`: 네이티브 통합용
- `cdylib`: 동적 링킹용
- `rlib`: Rust 라이브러리 사용용

## 개발 워크플로우

### 개발 모드에서 실행

```bash
npm run tauri dev
```

**실행 과정:**
1. Vite 개발 서버가 `http://localhost:1420`에서 시작
2. Tauri가 Rust 앱을 빌드하고 실행
3. Rust가 `cfg!(debug_assertions)`가 true임을 감지
4. `../sidecar/`에서 `python -m fiction_translator` 생성
5. Python은 코드 변경 시 핫 리로드 (watchdog 사용 시)
6. 프론트엔드는 코드 변경 시 핫 리로드 (Vite HMR)

**로그:**
- Rust 로그: `npm run tauri dev`를 실행한 콘솔
- Python 로그: 동일한 콘솔 (stderr 리더를 통해)
- 프론트엔드 로그: 브라우저 DevTools 콘솔

### 프로덕션 빌드

```bash
npm run tauri build
```

**실행 과정:**
1. `npm run build` 실행 (Vite 빌드)
2. 릴리스 모드로 Rust 컴파일
3. Python 사이드카 바이너리 번들 (PyInstaller 또는 유사 도구 사용)
4. 플랫폼별 인스톨러 생성 (DMG, MSI, AppImage 등)

**프로덕션 동작:**
- Rust는 `resources/binaries/fiction-translator-sidecar[.exe]`에서 사이드카 로드
- 모든 에셋이 번들되며 외부 의존성 없음
- 최적화된 성능 (Rust 릴리스 모드, 압축된 JS)

### 사이드카 통신 디버깅

**RPC 트래픽 확인:**

`sidecar.rs`에 로깅 추가:
```rust
pub async fn call(&mut self, method: &str, params: Option<Value>) -> Result<Value, String> {
    let request = JsonRpcRequest::new(method, params);
    log::debug!("→ RPC: {}", serde_json::to_string(&request).unwrap());
    // ... 요청 전송 ...
    log::debug!("← RPC 응답: {:?}", result);
    result
}
```

**사이드카를 독립적으로 테스트:**
```bash
cd sidecar
python -m fiction_translator
# stdin을 통해 수동으로 JSON-RPC 요청 전송:
{"jsonrpc":"2.0","method":"health.check","id":1}
```

## 문제 해결

### 개발 모드에서 사이드카가 시작되지 않음

**증상**: "Failed to start sidecar" 에러

**해결책:**
1. Python이 설치되고 PATH에 있는지 확인: `python --version`
2. 올바른 디렉토리에 있는지 확인: `cd src-tauri && cargo run`
3. `src-tauri/`에 대해 상대적으로 `../sidecar/`가 존재하는지 확인
4. Python 모듈 구조 확인: `cd ../sidecar && python -m fiction_translator`

### 프로덕션에서 사이드카가 시작되지 않음

**증상**: 앱은 열리지만 사이드카 상태가 연결 해제됨

**해결책:**
1. `resources/binaries/`에 번들된 바이너리가 존재하는지 확인
2. 바이너리에 실행 권한이 있는지 확인 (Unix)
3. 안티바이러스가 사이드카를 차단하지 않는지 확인
4. Tauri 로그에서 에러 확인

### RPC 호출 타임아웃

**증상**: "Sidecar call timed out after 120s"

**가능한 원인:**
1. Python 프로세스가 멈춤/크래시 (stderr 로그 확인)
2. 요청이 잘못됨 (Python이 파싱할 수 없음)
3. Python 메서드가 존재하지 않거나 에러 발생
4. Python이 사용자 입력을 기다림 (발생하지 않아야 함)

**디버그:**
- Python RPC 핸들러에 로깅 추가
- Python 메서드를 독립적으로 테스트
- 일시적으로 타임아웃을 줄여 빠르게 실패

### 이벤트가 프론트엔드에 도달하지 않음

**증상**: `listen("pipeline:progress")`가 실행되지 않음

**체크리스트:**
1. Python이 올바른 알림 형식 사용 (`id` 필드 없음)
2. 메서드 이름 변환이 올바른지 (`pipeline.progress` → `pipeline:progress`)
3. 이벤트 발생 전에 프론트엔드 리스너 등록
4. 브라우저 DevTools 콘솔에서 에러 확인

## 확장 포인트

### 새 RPC 메서드 추가

**Python 쪽** (`sidecar/src/fiction_translator/ipc/server.py`):
```python
async def handle_request(self, method: str, params: Any) -> Any:
    if method == "my_new_method":
        return await self.my_new_handler(params)
```

**프론트엔드 쪽** (`src/lib/api.ts`):
```typescript
export async function myNewMethod(params: any) {
  return invoke('rpc_call', { method: 'my_new_method', params });
}
```

**Rust 변경 불필요!**

### 새 이벤트 추가

**Python 쪽:**
```python
await server.send_notification("my.event", {"key": "value"})
```

**프론트엔드 쪽:**
```typescript
import { listen } from '@tauri-apps/api/event';

listen('my:event', (event) => {
  console.log('이벤트 수신:', event.payload);
});
```

**Rust 변경 불필요!**

### 새 Tauri 커맨드 추가

**Rust 쪽** (`commands.rs`):
```rust
#[tauri::command]
pub async fn my_command(state: State<'_, AppState>) -> Result<String, String> {
    Ok("Rust에서 안녕하세요!".to_string())
}
```

**`lib.rs`에 등록**:
```rust
.invoke_handler(tauri::generate_handler![
    commands::rpc_call,
    commands::sidecar_status,
    commands::my_command,  // 여기에 추가
])
```

**프론트엔드 쪽:**
```typescript
const result = await invoke('my_command');
```

## 모범 사례

### Rust 코드를 수정해야 하는 경우

**거의 필요 없음:**
- RPC 메서드 추가 → Python만
- 이벤트 추가 → Python만
- UI 변경 → 프론트엔드만
- 비즈니스 로직 → Python만

**Rust 변경이 필요한 경우:**
- 새 Tauri 커맨드 (직접 Rust 기능)
- 새 플러그인 (파일 시스템, HTTP 등)
- 윈도우 관리 변경
- OS 기능과의 깊은 통합

### 에러 처리

**패턴:**
```rust
pub async fn something() -> Result<Value, String> {
    let result = risky_operation()
        .await
        .map_err(|e| format!("컨텍스트: {}", e))?;
    Ok(result)
}
```

**항상:**
- Tauri 커맨드에 `Result<T, String>` 사용 (String 에러가 잘 직렬화됨)
- 에러에 컨텍스트 추가 (단순히 `.map_err(|e| e.to_string())`만 하지 말 것)
- 반환하기 전에 에러 로깅
- 프론트엔드에서 에러 처리 (성공을 가정하지 말 것)

### 성능

**팁:**
- RPC 호출은 비동기이므로 UI를 차단하지 않음
- 진행 업데이트에는 이벤트 사용 (폴링 대신)
- 가능한 경우 여러 RPC 호출을 배치 처리
- 대용량 데이터 전송에는 스트리밍 고려

### 보안

**기억할 것:**
- stdin/stdout IPC는 **로컬 전용** (네트워크 노출 없음)
- Tauri의 권한 시스템이 무단 접근으로부터 보호
- Python 쪽에서 입력 유효성 검사 (프론트엔드를 신뢰하지 말 것)
- RPC 메시지의 민감한 데이터는 암호화되지 않음 (로컬 프로세스만)

## 결론

Tauri Rust 셸은 React UI와 Python 비즈니스 로직 사이의 얇고 신뢰할 수 있는 브릿지입니다. 이를 최소화하고 Python에 위임함으로써 다음을 달성합니다:

- 빠른 반복 (Python 변경 시 재컴파일 불필요)
- 작은 바이너리 크기 (Rust는 컴파일됨, Python은 인터프리트됨)
- 명확한 관심사 분리 (인프라 vs. 비즈니스 로직)
- 강력한 프로세스 관리 (Tokio의 비동기 런타임)

대부분의 개발 작업에서 IPC 문제를 디버깅하거나 네이티브 통합을 추가할 때만 Rust 레이어와 상호작용하게 됩니다. 이 설계는 단순성과 유지보수성을 우선시합니다.
