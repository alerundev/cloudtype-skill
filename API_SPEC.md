# Cloudtype API Spec

Cloudtype 콘솔(`app.cloudtype.io`)이 사용하는 API 의 명세 정리입니다.
이 스킬은 이 명세에 기반하여 자연어 요청을 Cloudtype API 호출로 변환합니다.

목적: 어떤 에이전트라도 API 키만 있으면 Cloudtype 을 코드 작성부터 배포까지 일관되게 제어할 수 있도록 합니다.

## Scope Policy

**In scope** (에이전트 자동화 가능 범위):
프로젝트 / 스테이지 / 배포, 환경변수, 스케일링, 재시작 / 재배포, 로그, 메트릭, 롤백, 시크릿 등
API 키만으로 끝까지 처리할 수 있는 작업.

**Partial** (에이전트가 준비하고 사용자가 마무리):
- 커스텀 도메인 (DNS 등록기관 설정은 사용자 직접)
- 신규 GitHub OAuth 설치 (브라우저 동의 필요)
- 팀 초대 수락

**Out of scope** (스킬에서 의도적으로 제외):
- 커스텀 도메인 연결 — DNS 등록기관 설정이 사용자에게 필요합니다.
- **구독 / 결제 / 리소스 구매 일체** — 사용자가 콘솔에서 직접 처리합니다. AI 자동 리소스 증량은 물론, 구독 풀 증설이 필요한 경우도 동일합니다.
- **자동 리소스 조정** — OOM 또는 응답 지연이 감지되더라도 보고만 수행하며, cpu/memory/disk/replicas 를 자동으로 변경하지 않습니다. 풀 종류(`spot`) 의 선택 규칙은 자동 조정이 아닌 관측 기반 선택이며, [Resources / `spot` 시맨틱](#resources--spot-시맨틱) 을 따릅니다.
- **자동 우회 금지** — 실패 시 다른 preset 으로 갈아타기, 새 deployment 이름으로 별도 서비스 생성, Dockerfile 자동 작성/주입 등은 스킬이 자동으로 수행하지 않습니다. 모두 사용자 승인 후에만 진행합니다.
- 결제 / 환불 — PG 처리는 사용자 직접
- **API 키 발급** — 보안 경계상 콘솔 전용
- GitHub App / OAuth 최초 설치 — 브라우저 동의 필요
- 계정 생성 / 로그인 / 이메일 변경

원칙: 워크플로 마지막에 사용자가 다른 시스템에 로그인하여 마무리해야 하는 항목은 "자동화됨"으로 표기하지 않습니다.

## Base URLs

| Console | API |
|---|---|
| `https://app.cloudtype.io` | `https://api.cloudtype.io` |

API base URL 은 환경변수로 오버라이드할 수 있습니다.

- `CLOUDTYPE_API_BASE` — HTTP base URL 오버라이드
- `CLOUDTYPE_WS_BASE` — WebSocket base URL 오버라이드

## Authentication

**Method**: `Authorization: Bearer <JWT_API_KEY>`

- JWT payload 에는 `uid` 와 `iat` 가 포함되며, `exp` 는 없습니다(장기 사용 키).
- 알고리즘: HS256
- `?token=<KEY>` 쿼리 파라미터 형태도 동일하게 인정됩니다.
- 콘솔 UI 는 세션 쿠키를 사용하며, API 키는 프로그램에서의 접근 경로입니다.
- API 키 인증 시 `/auth` 응답에는 `provider: "apikey"`, `deviceid: "apikey-<id>"` 가 포함됩니다.

## Resource Hierarchy

```
User (uid)
 └── Scope (= space, 예: "myspace") — 과금/쿼터 경계
      └── Project (예: "myproject")
           └── Stage (예: "main") — 브랜치/환경 단위
                └── Deployment (예: "web") — 실제 실행되는 서비스
```

## Confirmed Endpoints (GET)

### Auth / User

| Method | Path | Notes |
|---|---|---|
| GET | `/auth` | API 키로 현재 사용자 조회 |
| GET | `/userscope/{uid}/scopes` | 사용자가 접근 가능한 스페이스 |

### Scope (Space)

| Method | Path | Notes |
|---|---|---|
| GET | `/scope/{scope}` | 스페이스 상세 |
| GET | `/scope/{scope}/members` | 멤버 목록 |
| GET | `/scope/{scope}/resource/limit` | 쿼터 한도 |
| GET | `/scope/{scope}/resource/stat` | 현재 사용량 |
| GET | `/scope/{scope}/cluster?onlyScoped=true` | K8s 클러스터 |

### Project

| Method | Path | Notes |
|---|---|---|
| GET | `/project?uid={uid}` | 사용자의 모든 프로젝트 |
| GET | `/project/{scope}` | 스페이스 내 프로젝트 |
| GET | `/project/{scope}/{project}` | 프로젝트 상세 |
| GET | `/project/{scope}/{project}/stage` | 스테이지 목록 |
| GET | `/project/{scope}/{project}/stage/{stage}` | 스테이지 상세 |
| GET | `/project/{scope}/{project}/stage/{stage}/stat` | 스테이지 통계 |
| GET | `/project/{scope}/{project}/stage/{stage}/cluster` | 클러스터 바인딩 |
| GET | `/project/{scope}/{project}/stage/{stage}/deployment` | 전체 배포 목록 |
| GET | `/project/{scope}/{project}/stage/{stage}/events?deployment={name}` | K8s events (Started, Pulled, Failed 등) |
| GET | `/project/{scope}/{project}/stage/{stage}/secret` | 시크릿 store 조회 |
| PUT | `/project/{scope}/{project}/stage/{stage}/secret` | 시크릿 저장 (아래 섹션 참고) |
| GET | `/project/{scope}/{project}/stage/{stage}/vars` | 스테이지 레벨 공용 변수 |
| GET | `/project/{scope}/{project}/stage/{stage}/route` | 스테이지 라우트 |

### Deployment

| Method | Path | Notes |
|---|---|---|
| GET | `.../deployment/{name}` | 배포 상세 (request + stat) |
| GET | `.../deployment/{name}/stat` | 경량 상태 |
| GET | `.../deployment/{name}/session` | 이전 배포 요청 이력 |
| GET | `.../deployment/{name}/session/latest` | 마지막 배포 요청 (env 값 포함) |
| GET | `.../deployment/{name}/resource/service` | 실시간 K8s Pod 정보 + CPU/메모리 사용량 |
| GET | `.../deployment/{name}/resource/route` | Ingress / entrypoints |
| GET | `.../deployment/{name}/resource/volume` | PVC 정보 |
| GET | `.../deployment/{name}/resource/log` | 존재하지만 적절한 파라미터가 필요 (현재 cluster error 반환) |
| GET | `.../deployment/{name}/resource/pod` | 존재하지만 적절한 파라미터가 필요 |

### Resource catalog & limits

Cloudtype 은 선구독 모델로, 리소스 풀을 먼저 확보한 뒤 그 안에서 deployment 에 할당합니다.
세 엔드포인트의 관계: **`available = limit - stat`**.

| Method | Path | Notes |
|---|---|---|
| GET | `/scope/{scope}/resource/limit` | 구독한 총 풀 + 서비스 단위 제약 (`maxCPUPerService`, `maxMemoryPerService` 등) |
| GET | `/scope/{scope}/resource/stat` | 현재 사용량 + `stats[]` 배열에 서비스별 세부 정보(cpu/memory/disk/replicas/status/exposes/entrypoints) |
| GET | `/scope/{scope}/resource/available` | 할당 가능 잔여량 (메모리 증설 가능 여부 판단 기준) |
| GET | `/scope/{scope}/cluster/{cluster}` | 클러스터 상세 |

**주요 키 (limit / available 공통)**
- `cpu`, `memory`, `disk` — 구독 풀(stable) 리소스 총량/잔여량 (메모리/디스크 단위: GB). 구독 안 한 스페이스는 모두 `0`.
- `spot.cpu`, `spot.memory`, `spot.disk` — 프리티어 풀 리소스 총량/잔여량. 카드 등록 스페이스는 보통 1GB / 1GB.
- `running` / `spot.running` — 풀별 **동시 실행 가능 서비스 수**. `0` 이면 해당 풀로 추가 배포 불가.
- `maxReplicas` / `spot.maxReplicas` — 한 서비스 안의 replica 수 한도. `0` 이면 해당 풀로 배포 불가.
- `maxCPUPerService`, `maxMemoryPerService`, `maxDiskPerService` (`spot.*` 계열 동일) — 서비스 1개당 사양 상한.
- `service` — 스페이스 전체 서비스 수 잔여 (풀 공통). `0` 이면 어느 풀로도 추가 배포 불가.
- `servicePerStage` — stage 당 서비스 수 잔여 (풀 공통).
- `project`, `stage` — project/stage 개수 제약
- `features` — 스페이스에서 추가로 활성화된 feature 목록 (예: `app:container`, `app:dockerfile`). **기본 preset (postgresql/redis/web/node 등) 의 가용 여부와는 무관**하며, 이 배열에 없다고 해당 preset 을 스페이스에서 못 쓰는 것으로 판단하지 마세요.
- `ephemeral.*` — 다른 노드 타입의 별도 풀
- `maxImageSize`, `logRetention`, `deploymentRetention` 등

**활용 패턴**
- **배포 직전 풀 선택** — `available` 을 조회해 구독/프리티어 두 풀 중 `resources.spot` 값을 결정. 규칙은 [Resources / `spot` 시맨틱](#resources--spot-시맨틱) 참조.
- 배포 전 사용자가 명시적으로 리소스를 요구하면 `available` 과 비교한 뒤, 부족 시 "콘솔에서 풀 증설이 필요합니다" 안내
- OOM 진단 시 `available.memory` 를 함께 보고하여 "증설 가능한 한도는 X GB 입니다" 안내
- **자동 증량 금지** — 구독/결제 API 자체가 스킬 범위 밖

### Catalog

Preset / framework / DB 등 Cloudtype 에 배포 가능한 모든 `app` 의 마스터 카탈로그입니다. 스킬은 이 다섯 엔드포인트로 이름/옵션/리소스를 알아내며, 사전 카탈로그를 본문에 박아두지 않습니다.

| Method | Path | Notes |
|---|---|---|
| GET | `/app?limit=300` | 전체 카탈로그 마스터 (190개안팜, framework / DB / 템플릿 구분 없이 모두 포함). preset 이름 확정용. |
| GET | `/app/{name}` | 단일 preset 세부. **`stat.schema`** (JSON Schema 형식 옵션 명세), **`stat.resources`** (`cpu`/`memory`/`disk` 각각 `min` / `initial`) 포함. 옵션 채움에 사용. |
| GET | `/app/presets` | 프론트엔드 템플릿 만 추린 목록 (react/vue/angular 등, 약 100여 개). |
| GET | `/app/metadata` | preset 메타 (카테고리, 버전 목록, `context` 요구 등). 버전 매칭에 유용. |
| GET | `/app/categories` | 카테고리 이름 배열 (예: `["frontend", "javascript", "language", ...]`). 매칭 키워드 고르는 데 보조. |

**활용 패턴**

1. 배포 직전에 `/app?limit=300` 으로 전체 마스터를 받아 세션 동안 캐시. 사용자 요청 / repo 신호를 `name` / `displayName` / `categories` 로 매칭.
2. preset 이 정해지면 `/app/{name}` 으로 세부 조회.
   - `stat.schema.required` 의 옵션만 PUT 의 `options` 에 포함. 명시 없는 필수는 `default` 값 또는 자동 생성값.
   - 스키마에 없는 옵션 이름을 LLM 상식으로 박지 않습니다.
   - `attrs.type == "password"` 또는 이름이 `*password*` / `*secret*` / `*token*` / `*key*` 인 옵션은 stage secret store 에 저장 후 `secret` 참조로 연결.
3. `stat.resources.initial` 은 preset 의 권장 초기 사양입니다. 스킬의 기본 정책은 "사용자 명시 없으면 `resources` 상세 생략 → 서버 디폴트" 이므로 이 값을 잡의로 박을 필요는 없습니다. 풀 선택 후 가용량 판단 (`/resource/available`) 이 부족하면 [리소스 부족](#리소스-부족) 안내 흐름을 따릅니다.

### GitHub 연동 정책

스킬 사용자는 Cloudtype ↔ GitHub 연동이 이미 되어 있는 상태를 전제합니다.
스킬은 연동을 설정하거나 해제하지 않으며, **이미 연결된 상태를 활용**만 합니다.

#### Tier 1 — 배포에 직접 사용 (조회 호출 불필요)

사용자가 repo URL 과 브랜치를 명시한 경우, OAuth API 호출 없이 바로 PUT 합니다.

```jsonc
"context": { "git": { "url": "https://github.com/<owner>/<repo>.git", "branch": "main" } }
```

Cloudtype 서버가 저장된 GitHub App credential 로 클론을 수행합니다 (public / private 무관).

#### Tier 2 — 조회 전용 (사용자 요청이 모호한 경우)

모두 GET 이며 read-only 입니다.
- 연동 여부 확인: `/oauth/github/has`
- 연결된 계정 / repo 검색: `/oauth/github/accounts`, `/oauth/github/repository/{installationId}`
- 브랜치 목록: `/oauth/github/repository/{installationId}/{repo}/branch`

#### Tier 3 — 수행하지 않음

- `DELETE /user/authconfig/{uid}/github` (연동 해제)
- 연동 설정 변경 일체
- GitHub App 최초 설치 (브라우저 OAuth, 별도 API 없음)

### User / OAuth / Auth

| Method | Path | Notes |
|---|---|---|
| GET    | `/auth/auth/{uid}` | uid 기반 auth 조회 |
| GET    | `/user/byuid?uid={uid}` | uid 로 사용자 정보 조회 |
| GET    | `/user/authconfig/{uid}` | 사용자 전체 auth config |
| GET    | `/user/authconfig/{uid}/github` | GitHub 연동 설정 |
| DELETE | `/user/authconfig/{uid}/github` | GitHub 연동 해제 |
| GET    | `/oauth/github/has` | 현재 세션의 GitHub 토큰 존재 여부 |
| GET    | `/oauth/github/accounts` | 연결된 GitHub 계정 목록 (installation 단위) |
| GET    | `/oauth/github/repository/{installationId}` | 해당 installation 의 repo 목록 |
| GET    | `/oauth/github/repository/{installationId}/{repo}/branch` | repo 의 브랜치 목록 |

GitHub repo 목록 조회 / 브랜치 선택 / 연동 해제는 API 로 가능하며,
최초 GitHub App 설치 자체는 브라우저 OAuth flow 를 통해서만 가능합니다.

### 기타 read API

| Method | Path | Notes |
|---|---|---|
| GET | `/stage?uid={uid}&stage=@{scope}/{project}:{stage}` | stage 조회 (URL 인코딩된 scope/project/stage) |
| GET | `/scope/{id16}?byid=true` | scope id 로 조회 (이름 대신) |
| GET | `/project/{scope}/{project}/stage/{stage}/resource/route` | stage 레벨 라우트 (`/stage/{stage}/route` 와 별개) |

## WebSocket Endpoints

모두 `wss://api.cloudtype.io/...` 아래에 위치합니다. 로그 스트리밍 및 인터랙티브 터미널에 사용됩니다.
세 엔드포인트 모두 동일한 핸드셰이크 프로토콜을 사용합니다.

| Endpoint | Purpose |
|---|---|
| `/project/logs` | 런타임 stdout / stderr 스트림 |
| `/project/build/logs` | 빌드 진행 상황 스트림 |
| `/project/attach` | 인터랙티브 셸 (pty) |

### Handshake

브라우저에서 WS upgrade 시 Authorization 헤더를 설정할 수 없으므로,
서버는 첫 메시지로 **prepare envelope** 을 사용합니다. 클라이언트는 다음 JSON 을 전송합니다.

```json
{
  "type": "prepare",
  "params": {
    "scope": "myspace",
    "project": "myproject",
    "stage": "main",
    "deployment": "web",
    "options": {
      "follow": true,
      "pretty": false,
      "tailLines": 500,
      "previous": false,
      "timestamps": true
    }
  },
  "headers": {
    "Authorization": "Bearer <CLOUDTYPE_API_KEY>",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*"
  }
}
```

서버는 `"accept"`(plain text)로 응답한 뒤 로그 청크(UTF-8 텍스트, 프레임당 다수 라인 가능)를 스트리밍합니다.

### Log frame format

각 라인 형식: `<RFC3339 nano timestamp> <stdout/stderr text>`

```
2026-05-26T07:08:01.072250947Z {"ts":"...","level":"info","msg":"listening","port":8000}
```

`timestamps: false` 인 경우 앞쪽 타임스탬프가 생략됩니다.

### Build log frame format

이모지를 포함하는 자유 형식 텍스트입니다.

```
🏁 Deployment started ...
👉 Prepare build
🙌 No build required.
🚀 Deploy to a cluster
✅ Done.
```

새 빌드의 경우 다음과 같은 형태가 나타납니다.

```
🏂 Build runner(sel-1) is starting...
  ├ Build type is dockerfile
  └ Build env is {"NODE_ENV":"p*********", ...}    # env 값은 마스킹됨
```

### Terminal (`/project/attach`)

동일한 prepare envelope 사용 후 클라이언트는 리사이즈 제어 메시지를 보낼 수 있습니다.

```json
{"r": 60, "c": 128}    // rows, cols
```

서버는 pty 출력(raw ANSI escape sequence; mouse reporting, alt-screen 등 포함)을 스트리밍하며,
클라이언트는 키 입력을 텍스트 프레임으로 전송합니다.

### 동작 확인

Python `websockets` 로 prepare envelope 의 `Authorization: Bearer <key>` 를 전달하면 라이브 로그 수신이 가능합니다.
브라우저나 콘솔 세션은 필요하지 않습니다.

## Key Object Shapes

### Deployment

```jsonc
{
  "id": "...",
  "name": "web",
  "displayName": "My Web Service",
  "owner": "<uid>",
  "scope": "myspace",
  "project": "myproject",
  "stage": "main",
  "request": {                 // 사용자가 요청한 spec
    "name": "web",
    "app": "node@20",          // preset name
    "options": { /* env, app 별 옵션 */ },
    "resources": { "cpu": 2, "memory": 2, "disk": 10, "replicas": 1, "spot": false },  // spot:false = 구독 리소스
    "context": { "preset": "node", "git": {} }
  },
  "stat": {                    // 관찰되는 런타임 상태
    "status": "running" | "stopped" | "deploying" | "...",
    "ready": 1, "replicas": 1, "available": 1, "unavailable": 0,
    "exposes": [ { "protocol": "http", "port": 3000, "hostname": "web" } ],
    "entrypoints": [ { "link": "https://...cloudtype.app", "type": "http" } ],
    "routes": [ /* ... */ ],
    "volumes": [ /* PVCs */ ]
  }
}
```

## Known Plan Limits (`/resource/available` 기준, Hobby 플랜)

- 최대 이미지 크기: **5 GB**
- 로그 보관: **15일**
- 배포 이력 보관: **15개**
- 동시 배포 수: **3**
- 일일 배포 수: **100**
- 서비스 1개당: 4 vCPU / 16 GB / 1000 GB disk
- 도메인: **100**
- 프로젝트: 15, 스테이지/프로젝트: 8, 서비스/스테이지: 32

## Write / Action API

### Deployment control

| Method | Path | Body | Notes |
|---|---|---|---|
| PUT | `/project/{scope}/{project}/stage/{stage}/deployment/{name}/start` | (empty) | 정지된 배포 시작 |
| PUT | `/project/{scope}/{project}/stage/{stage}/deployment/{name}/stop` | (empty) | 실행 중인 배포 정지 |
| DELETE | `/project/{scope}/{project}/stage/{stage}/deployment/{name}` | — | 배포 삭제 |

### Redeploy / Update (동일 엔드포인트)

별도의 redeploy 엔드포인트는 존재하지 않습니다. `/redeploy`, `/deploy`, `/apply`, `/rebuild`, `/rollout` 은 모두 404 입니다.
재배포와 업데이트는 모두 생성과 동일한 `PUT .../deployment` 를 사용합니다.

- 동일 name + 동일 spec → **재배포** (새 빌드 세션, 새 이미지)
- 동일 name + 변경된 env / resources / branch → **업데이트 + 재배포**
- 다른 name → **생성**

기존 deployment 의 spec 을 다시 PUT 하면 서버가 새로운 `deploying` 세션 id 를 반환하며 빌드를 시작합니다.

### Stage-level secrets

**배포환경(stage) 단위 공용 시크릿** — 미리 저장해둔 값을 배포 시점에 주입합니다.

```
GET  /project/{scope}/{project}/stage/{stage}/secret
PUT  /project/{scope}/{project}/stage/{stage}/secret
```

GET 응답 예:
```jsonc
{
  "my-db-password": "...",
  "another-secret": "..."
}
```

PUT 요청:
```jsonc
{
  "secrets": {
    "my-db-password": "...",
    "another-secret": "..."
  },
  "merge": false    // false = 전체 교체 (누락된 시크릿은 삭제됨), true = 추가/갱신만
}
```

### 시크릿 안전 정책

- **읽기**: 스킬에서는 시크릿 조회를 수행하지 않습니다. 기존 시크릿 확인이 필요한 경우 Cloudtype 콘솔 사용을 안내합니다.
- **쓰기(일반)**: 자동으로 `merge: true` 를 강제하여 기존 시크릿이 보존되도록 합니다.
- **쓰기(전체 교체)**: `merge: false` 는 사용자가 "기존 항목을 모두 삭제하고 새로 작성하겠다"고 명시한 경우에 한해, 한 번 더 확인한 뒤 수행합니다.
- **이미 존재하는 키 덮어쓰기**: 한 번 확인을 받습니다("이미 `X` 시크릿이 존재합니다. 덮어쓸까요?").
- **시크릿 단건 삭제**: 별도 엔드포인트는 확인되지 않았습니다. `merge: false` 의 누락을 통한 간접 삭제가 가능합니다.

### env / buildenv 항목의 두 가지 형태

`options.env[]` 또는 `options.buildenv[]` 의 각 항목은 **인라인 값** 또는 **시크릿 참조** 둘 중 하나입니다.

```jsonc
// 인라인 값 (평문으로 spec 에 저장됨)
{"name": "NODE_ENV",     "value":  "production"}

// 시크릿 참조 (민감 값에 권장)
{"name": "DB_PASSWORD",  "secret": "my-db-password"}
//          ↑                  ↑
//   컨테이너 내 env 이름     stage 시크릿 store 의 키 이름
```

두 형태는 한 배열 안에 혼용 가능합니다. env 이름과 secret 키 이름은 동일할 필요가 없으나, 가독성을 위해 일치시키는 것을 권장합니다.

### ⚠️ 시크릿 참조 규칙

`{"secret": "<키>"}` 참조 객체는 **오직 `options.env[]` / `options.buildenv[]` 항목 안에서만** 동작합니다. 그 외 모든 `options.*` 필드(preset 옵션 전부 — `rootpassword`, `rootpw`, `requirepass`, `adminPassword` 등 preset/필드 이름 무관)에는 **plain 값만** (보통 문자열) 넣으세요. 객체를 넣으면 PUT 은 200 통과 / 배포도 "성공"으로 보이지만 곧 서비스가 `stopped` 로 전환되며 `[ServiceError] secret value must be a string` 이 발생합니다.

권장 패턴 (DB 배포):
```jsonc
// 1) DB preset 의 password 자리: plain 문자열 직접
{"options": {"rootpassword": "QyaKsJVP2Qn4w5poSEe9sbqbeWY"}}

// 2) 같은 값을 stage secret store 에도 저장 (merge: true)
PUT .../stage/{stage}/secret
{"secrets": {"DB_PASSWORD": "QyaKsJVP2Qn4w5poSEe9sbqbeWY"}, "merge": true}

// 3) 앱 서비스의 env[] 에서는 그 시크릿을 참조로 사용
{"options": {"env": [{"name": "DB_PASSWORD", "secret": "DB_PASSWORD"}]}}
```

### 자동 시크릿 이전 정책 (권장)

사용자가 env 를 평문으로 전달하는 경우 키 이름을 기반으로 자동 분류합니다.

- `*PASSWORD*`, `*SECRET*`, `*TOKEN*`, `*KEY*`, `*PWD*`, `*PRIVATE*`, `*AUTH*` → 시크릿 이전 제안 ("해당 항목을 시크릿으로 옮길까요?")
- `*URL*`, `*HOST*` 는 모호함 — 값에 인증 정보가 포함된 경우(`postgresql://user:PASS@...` 등)에만 시크릿화 권장
- `NODE_ENV`, `LOG_LEVEL`, `PORT` 등 단순 플래그는 인라인으로 유지

### Rewrites — 소스 수정 없이 CORS 우회 (web preset)

web preset 의 리버스 프록시 옵션입니다. 프론트엔드 코드가 **자기 자신을 호출**(예: `fetch('/api/...')`) 하도록 작성되어 있으면,
web preset 단에서 해당 요청을 가로채 다른 서비스로 프록시합니다. 결과적으로 CORS 처리, 프론트 ↔ 백엔드 URL 분기, 별도의 nginx 운영 등이 불필요해집니다.

페이로드 구조:
```jsonc
"options": {
  "rewrites": [
    {"from": "/api/*",  "to": "backend:3000"},
    {"from": "/auth/*", "to": "https://other.example.com"}
  ]
}
```

**적용 가능 조건**

Rewrites 는 "소스 수정 없이 모든 CORS 를 해결"하는 만능 도구가 아닙니다. **코드가 self-referential** 일 때만 적용 가능합니다.

| 코드 형태 | Rewrites 적용 가능 | 필요 조치 |
|---|---|---|
| `fetch('/api/...')` (상대 경로) | 가능 | Rewrites 추가만 |
| `fetch(API_BASE + '/api/...')` (env 분기) | 가능 | env 를 빈 문자열로 설정 + Rewrites 추가 |
| `fetch('https://hardcoded.com/api/...')` | 불가능 | 코드 수정 필요 (상대 경로로 변경) |

진단 시 먼저 코드의 fetch / axios 호출 패턴을 분석한 뒤 적용 가능 여부를 판정합니다.

### web preset 옵션 정리

- `docbase` (예: `/dist`) — 빌드 산출물 서빙 루트
- `spa` (bool) — SPA 폴백 (404 → index.html)
- `nodeversion` (int) — 빌드용 Node 버전
- `rewrites` (array) — 리버스 프록시 규칙

### Deployment options (전체 필드)

`options` 객체에 들어갈 수 있는 키들 (node 계열 preset 기준; 다른 preset 도 유사):

| Key | 타입 | 예 | 목적 |
|---|---|---|---|
| `ports`              | string 또는 int | `"4000"` | 서비스 포트 |
| `env`                | array | `[{name,value}]` | 런타임 환경변수 |
| `buildenv`           | array | `[{name,value}]` | 빌드 타임 환경변수 |
| `install`            | string | `"npm ci"` | 설치 커맨드 |
| `build`              | string | `"npm run build"` | 빌드 커맨드 |
| `start`              | string | `"npm start"` | 시작 커맨드 |
| `healthz`            | string | `"/healthz"` | 헬스체크 HTTP 경로 (readiness probe) |
| `initialDelaySeconds`| string 또는 int | `"5"` | 헬스체크 시작 전 대기 시간(초) |
| `strategy`           | string | `"recreate"` | 배포 전략 (`recreate` / `rolling`) |
| `npmrc`              | string | `"..."` | .npmrc 내용 (private npm registry 인증 등) |
| `docbase`            | string | `"/dist"` | (web preset) 정적 파일 루트 |
| `spa`                | bool   | `true` | (web preset) SPA 폴백 |
| `nodeversion`        | int    | `18` | (web preset 빌드 시 Node 버전) |
| `rootusername` / `rootpassword` / `database` | string | — | (DB preset 전용) |
| `config`             | string | postgresql.conf 와 유사 내용 | (DB preset) 추가 설정 파일 내용 |
| `tz`                 | string | `"Asia/Seoul"` | (DB preset) 타임존 (TZ env 로 매핑) |

### Dockerfile preset

framework preset(node / python 등) 과 달리, **Docker 레벨 제어를 모두 노출**하는 preset 입니다.

```jsonc
{
  "name": "my-service",
  "app": "dockerfile",                  // framework preset 과 달리 app = preset 이름 그대로
  "options": {
    "ports": "3001",
    "dockerfile":      "Dockerfile",   // repo 내 Dockerfile 경로
    "dockerfiletext":  "FROM ...",     // 인라인 Dockerfile (repo 에 Dockerfile 이 없어도 빌드 가능)
    "commands":        "...",           // CMD / entrypoint 오버라이드
    "uid":             "1000",          // 컨테이너 실행 UID (non-root)
    "gid":             "2000",          // 실행 GID
    "shell":           "/bin/sh",       // 명령 실행 셸
    "args":            [{"name":"K","value":"V"}],  // docker build --build-arg
    "labels":          [{"name":"K","value":"V"}],  // K8s pod label 또는 Docker image label
    "env":             [{"name":"K","value":"V"}],  // 런타임 ENV
    "healthz":         "/health",
    "initialDelaySeconds": "5",
    "strategy":        "rolling"        // "rolling" 또는 "recreate"
  },
  "resources": {"spot": false, "cpu": 1, "replicas": 2},  // spot:false = 구독 리소스
  "context": {
    "git": {"url": "https://...", "branch": "main"},
    "preset": "dockerfile"
  }
}
```

**활용 패턴**
- 사용자가 dockerfile preset 을 명시한 경우에 사용합니다.
- non-root 실행, 특수 셸 사용 등 고급 설정이 필요한 경우 dockerfile preset 전용 옵션(`uid` / `gid` / `shell` 등)이 활용됩니다.
- `dockerfiletext` 는 repo 에 Dockerfile 이 없을 때 인라인 방식으로 사용할 수 있는 옵션입니다. **스킬은 해당 내용을 자동으로 생성하지 않습니다.** 이 옵션 사용은 사용자 명시가 필요합니다.

### Container preset

**빌드 단계 없는 배포** — 외부 Docker 이미지를 그대로 pull 하여 실행합니다.

```jsonc
{
  "name": "my-container",
  "app": "container",
  "options": {
    "image":           "nginxinc/nginx-unprivileged:1.24",  // 외부 Docker 이미지 (필수)
    "ports":           "8088",
    "commands":        "...",            // 이미지의 CMD / ENTRYPOINT 오버라이드
    "uid":             "1000",
    "gid":             "1000",
    "shell":           "/bin/sh",
    "env":             [],
    "healthz":         "/...",
    "initialDelaySeconds": "3",
    "strategy":        "rolling"
  },
  "resources": {"spot": false},        // spot:false = 구독 리소스
  "context": {"preset": "container"}    // git 불필요 (이미지에서 직접 실행)
}
```

**dockerfile / container / framework preset 차이**

| 특성 | container | dockerfile | framework (node 등) |
|---|---|---|---|
| 빌드 단계 | 없음 (pull 만) | docker build | install + build |
| `image` (외부 이미지) | 필수 | 사용 안 함 | 사용 안 함 |
| `dockerfile` / `dockerfiletext` | 사용 안 함 | 사용 | 사용 안 함 |
| `install` / `build` / `start` | 사용 안 함 | 사용 안 함 | 사용 |
| `context.git` | 사용 안 함 (소스 불필요) | 필수 | 필수 |
| Docker Hub / 외부 레지스트리 pull | 가능 | 불가 | 불가 |

**활용 패턴**
- 외부 이미지 그대로 실행 (예: `nginx`, `redis`, `mysql`, GHCR 등)
- "코드 없이 특정 이미지 배포" 요청 → container preset
- private registry 인증은 현재 확인되지 않았습니다(공개 이미지로만 검증). 필요 시 추가 확인이 필요합니다.

### `app` 필드 패턴

| preset 종류 | `app` 값 패턴 | 예 |
|---|---|---|
| Framework (node / python 등) | `<runtime>@<version>` | `node@20`, `python@3.11` |
| Web (빌드 결과 서빙) | `web` | html, vue, react 등 모든 web preset |
| Dockerfile | `dockerfile` | preset 이름 그대로 (코드 + Dockerfile 빌드) |
| Container | `container` | preset 이름 그대로 (빌드 없이 외부 이미지 실행) |
| DB | `<engine>@<version>` | `postgresql@16`, `mariadb@10`, `redis@7` 등 |

→ preset 메타의 `config[0].app` 값을 참조하여 결정합니다.

### PostgreSQL preset

```jsonc
{
  "name": "postgresql",
  "app": "postgresql@16",
  "options": {
    "rootusername": "root",          // → POSTGRES_USER (plain string)
    "rootpassword": "<plain-password-string>",  // → POSTGRES_PASSWORD. plain 문자열만 허용, {"secret":...} 객체 X
    "database":     "<dbname>",      // → POSTGRES_DB
    "config":       "<conf text>",   // 선택 (postgresql.conf 형식)
    "tz":           "Asia/Seoul"     // 선택 (TZ env 로 매핑)
  },
  "resources": {
    "spot": false,   // spot:false = 구독 리소스. 프리티어는 spot:true (디스크 1GB 제약)
    "cpu": 1, "memory": 1,
    "disk": 10    // DB 는 disk 필수 (UI 디폴트 10GB)
  },
  "context": {"preset": "postgresql"}
}
```

DB preset 은 본질적으로 공식 Docker 이미지(postgres 등) 에 preset 이 노출한 옵션이 컨테이너 ENV(`POSTGRES_*`) 로 자동 매핑되는 구조입니다.
사용자는 Docker 이미지 측 ENV 컨벤션을 직접 알 필요가 없습니다.

다른 DB preset(mariadb / mysql / mongo / redis) 도 유사한 구조로 동작하며, 옵션 이름은 일반적으로 `rootusername` / `rootpassword` / `database` 가 공통입니다.

**타입 처리**: UI 는 `ports` / `initialDelaySeconds` 를 string 으로 전송합니다. 서버는 int 입력도 수용하지만, 일관성을 위해 SDK 에서는 한 가지 타입으로 통일하는 것을 권장합니다.

### Resources / `spot` 시맨틱

**`resources.spot` 은 Cloudtype 의 리소스 풀 종류를 선택하는 필드입니다.**

| `resources.spot` | 의미 |
|---|---|
| `true` | 프리티어 풀 |
| `false` | 구독 풀 |

**구독 사용자도 `spot: true` 를 사용할 수 있습니다.** 구독 플랜에서도 프리티어 풀을 함께 활용할 수 있습니다.

#### 풀 선택 규칙

배포 직전에 `GET /scope/{scope}/resource/available` 로 잔여 가용량을 조회하고 다음 규칙으로 `spot` 을 결정합니다.

1. 사용자가 풀을 명시한 경우 → 그 풀을 그대로 사용.
   - "프리티어 / free tier / 무료 / 테스트용 / 임시로" → `resources: {spot: true}`
   - "구독 리소스 / 운영용 / 프로덕션 / 무중단" → `resources: {spot: false}`
2. 사용자 명시가 없는 경우 → 잔여 가용량 기반 자동 선택.
   - 구독 풀 (`cpu`/`memory`/`disk`) 에 가용량 있음 → `resources: {spot: false}`
   - 구독 풀이 `0` 이고 프리티어 풀 (`spot.cpu`/`spot.memory`/`spot.disk`) 에 가용량 있음 → `resources: {spot: true}`

선택된 풀에 가용량이 없으면 배포를 시도하지 않고 사용자에게 구독 추가를 안내합니다. 다른 풀로의 자동 우회는 금지입니다.

### Resources 자동 조정 금지 정책

스킬은 리소스 사양(`cpu`, `memory`, `disk`, `replicas`)을 자동으로 변경하지 않습니다. 사용자 명시가 없는 경우에는 해당 필드들을 PUT 페이로드에 포함하지 않습니다.

`spot` 필드는 위 [풀 선택 규칙](#풀-선택-규칙) 에 따라 설정합니다. 사용자 명시 없이 `spot: false` 를 디폴트로 가정하여 넣지 않습니다.

- OOM / 응답 지연 등이 감지되어도 **자동 조정 없이 보고 후 사용자 결정 대기**합니다.
- 근거:
  1. **구독 풀 제한** — Cloudtype 은 선구독 모델로, 구독한 풀을 초과하면 배포가 실패합니다.
  2. **사용자 판단 보존** — 워크로드를 가장 잘 아는 것은 사용자이므로, 증설 여부는 사용자가 결정합니다.
  3. **진짜 원인 가림 방지** — OOM 의 원인이 실제 메모리 부족이 아니라 누수 / 무한 루프 / 알고리즘 비효율 등인 경우, 자동 증설은 문제를 가립니다.

  (과금 폭탄은 구조적으로 발생하지 않으며, 다른 deployment 에 직접적 영향도 K8s pod limit 으로 격리됩니다.)

### Resources 부분 업데이트

PUT 시 `resources` 에 일부 키만 전송해도 나머지는 서버 디폴트로 채워집니다.

- 요청 예: `resources: {spot: true, memory: 0.25}` — `spot: true` 는 프리티어 풀을 선택
- 응답 예: `{spot: true, cpu: 0, memory: 0.25, disk: 0, replicas: 1}`

누락된 키는 서버가 자동으로 채웁니다.

### Context.git.path (슬래시 선택)

공식 문서는 `/pathname` 스타일을 제시하지만, 콘솔은 슬래시 없는 `"backend"` 도 전송합니다(서버 응답에도 그대로 echo).
일관성을 위해 SDK 에서는 `/` 로 시작하는 형태 사용을 권장합니다.

### Deployment create / update

```
PUT /project/{scope}/{project}/stage/{stage}/deployment
```

생성과 업데이트에 동일하게 사용됩니다 (idempotent).

```jsonc
{
  "request": [{                      // 여러 deployment 를 배치 가능
    "name": "my-service",
    "app": "node@16",                // preset 이름 (버전은 @ 로 표기)
    "options": {
      "env": [{"name": "NODE_ENV", "value": "production"}],
      "ports": 3000,                 // single int 또는 array
      "buildenv": []
    },
    "resources": {                   // 생략 시 서버 디폴트. 사용자 명시 없으면 키 자체 생략 권장.
      "spot": false,                 // false=구독 리소스, true=프리티어 리소스
      "cpu": 1, "memory": 1,
      "replicas": 2                  // 생략 시 1
    },
    "context": {
      "git": {
        "url": "https://github.com/<owner>/<repo>.git",
        "branch": "main"
      },
      "preset": "node"
    }
  }],
  "owner": "<uid>"
}
```

응답: 전체 deployment 레코드(`id`, `deploying` 빌드 세션 id, echo 된 `request` 포함)를 배열로 반환합니다.

### Project create

```
POST /project
Body: {"scope": "myspace", "name": "test", "displayName": null, "cluster": "gke-exp-0"}
```

## Preset 권장 옵션 (확인된 항목)

| preset | request.app | 필수 options | docbase | 빌드 산출물 위치 |
|---|---|---|---|---|
| `html`        | `web`              | `docbase`, `spa`, `ports` | `/` | — (정적) |
| `vue`         | `web`              | `docbase`, `spa`, `ports`, `nodeversion`, `install`, `build`, `buildenv[]` | **`/dist`** | `dist/` |
| `vanilla-vite`| `web`              | (vue 와 유사) | `/dist` (권장) | `dist/` |
| `node`        | `node@<ver>`       | `ports`, `env[]`, `install`, `start` | — | — |
| `postgresql`  | `postgresql@<ver>` | `rootusername`, `rootpassword`, `database` | — | — (빌드 없음) |

**주의**: vue / vite 계열은 `docbase` 기본값이 `/` 이므로, 산출물이 아닌 repo 루트의 `index.html`(소스 원본)이 서빙됩니다. **반드시 `docbase: "/dist"` 명시가 필요합니다.**

**Framework preset 의 선택 옵션**: `node` / `python` 계열을 포함한 framework preset 은 web preset 과 동일하게 `healthz` (헬스체크 HTTP 경로) 와 `initialDelaySeconds` (헬스체크 시작 전 대기 초) 을 선택적으로 받습니다. 명시 없으면 서버 디폴트로 동작하며, 익숙한 사용자가 직접 조정하는 어디부터입니다.

## Multi-deployment 내부 통신

같은 `stage` 내 deployment 끼리는 **deployment name 이 그대로 내부 hostname** 으로 동작합니다.
- 예: backend 컨테이너에서 `PGHOST=meeting-db`, `PGPORT=5432` 로 접속
- 외부 공개 URL 이 아닌 내부 cluster 네트워크 경유
- 프론트엔드는 빌드 타임에 백엔드 public URL 을 env 로 받아 번들에 포함시키는 방식을 권장합니다(예: Vite 의 `VITE_*`).

## Monorepo / 서브 디렉토리 배포

**키: `context.git.path`** (`subpath` 가 아닙니다)

- 공식 문서의 "서브 디렉토리 배포" 항목 참고:
  ```yaml
  context:
    git:
      path: /pathname
  ```
- 레포 루트 기준 절대 경로 스타일 (`/backend`, `/frontend` 등)
- `subpath` 라는 키도 서버 응답에 echo 되지만, 실제 빌드에는 무시됩니다. 공식 키 이름은 `path` 이며 SDK 에서는 `path` 사용을 원칙으로 합니다.

## env 응답 마스킹

- GET deployment 응답에서 env 의 value 는 일부만 노출되는 형태로 마스킹됩니다.
- 빌드 로그의 `Build env is {...}` 출력 역시 앞 글자와 `*` 길이 표기 형태로 마스킹됩니다.
- 실제 값은 컨테이너 내부에서는 평문으로 존재합니다.
- SDK 는 env 값을 응답으로 재확인하지 말고, 설정 의도를 별도로 보관하거나 동작 테스트로 검증합니다.

## PUT 응답의 stale spec

PUT 직후 응답에서 이전 spec 이 echo 될 수 있습니다(예: git url 교체 후에도 이전 git url 이 표시되는 경우).
다만 `deploying` 필드는 새 빌드 세션 id 로 갱신되므로, **PUT 성공 여부는 `deploying` 값이 변경되었는지로 판단**합니다.
실제 적용된 spec 은 빌드 로그의 `repository` 메타에서 확인합니다.

## Field Quirks

- **`request.app` 필드는 preset 이름이 아니라 `preset.config[0].app` 값** 입니다.
  예: preset `html` 의 config app 은 `"web"`. preset 이름을 그대로 `app` 에 넣으면
  `app "<name>" in "<deployment>" does not exist` 오류(50401 ServiceError)가 발생합니다.
  preset 메타에서 `config[0].app` 값을 사용해야 합니다.
- **`prefer` 필드가 두 곳에 존재**합니다.
  - `deployment.prefer` — 사용자 의도 (`"start"` / `"stop"`)
  - `deployment.stat.prefer` — 현재 컨트롤러 상태 (생성 직후 잠시 `"stop"`)
- **DELETE 후 단건 GET 은 404 가 아닌 `HTTP 200` + empty body** 를 반환합니다.
  존재 확인은 응답 body 파싱 가능 여부 또는 stage 의 deployment 목록을 통해 수행합니다.
- DELETE 시 routes / entrypoints 도 함께 정리됩니다. 라이브 URL 은 즉시 404 입니다.
- 빌드 로그 WS 는 빌드 종료 시 close code `1005` 로 정상 종료됩니다.
- html preset 빌드 시간은 약 19초 (Dockerfile 빌드이지만 base 캐시로 가볍게 종료됨).
