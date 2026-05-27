# Cloudtype API Spec (in progress)

> Reverse-engineered from `app.cloudtype.dev` console.
> Source: HAR capture 2026-05-26, plus direct API testing.
> Final target: `app.cloudtype.io` (likely identical API surface).
>
> **Goal:** Power an OpenClaw `cloudtype` skill so any agent can drive
> Cloudtype via API alone — closing the loop between "vibe coding" and
> "vibe deployment".

## Scope Policy

**In scope** (full agent automation):
Anything an agent can finish end-to-end with just an API key — projects,
stages, deployments, env vars, scaling, restart/redeploy, logs, metrics,
rollback, registered secrets.

**Partial** (agent prepares + guides, human finishes):
Custom domains (DNS at registrar requires human), new GitHub OAuth
install (browser consent), team invite acceptance.

**Out of scope** (intentionally excluded from the skill):
- Custom domain connection — DNS at registrar needs a human
- **구독 / 결제 / 리소스 구매 일체** — 운영자 명시적 배제, 사용자 명시 있더라도 건들지 않음.
  AI 자동 리소스 이용량 증가는 물론 구독 푹 증량이 필요한 경우도 **사용자가 콘솔에서 직접** 좌용.
- **자동 리소스 조정** — OOM/느림 감지 시에도 보고만 하고 자동으로 cpu/memory/disk/replicas/spot 변경 안 함.
  이유: 구독 푹 제약, 다른 서비스 영향, 사용자 학습 보존.
- Billing / refund — PG flows need a human
- **API key issuance itself** — security boundary, console-only
- GitHub App / OAuth initial install — browser consent
- Account creation / login / email change

Rule of thumb: if the workflow ends with the human still needing to log
into a different system to finish, do not market it as automated.

## Base URLs

| Env | Console | API |
|---|---|---|
| Dev | `https://app.cloudtype.dev` | `https://api.cloudtype.dev` |
| Prod | `https://app.cloudtype.io` | `https://api.cloudtype.io` (assumed) |

## Authentication

**Method:** `Authorization: Bearer <JWT_API_KEY>`

- JWT payload contains `uid` and `iat` (no `exp` — keys are long-lived).
- Algorithm: HS256.
- Also accepts `?token=<KEY>` as query parameter (same effect).
- Console UI uses session cookies; API keys are the programmatic path.
- When authenticated via API key, server reports `provider: "apikey"` and
  `deviceid: "apikey-<id>"` in `/auth` response.

## Resource Hierarchy

```
User (uid)
 └── Scope (= space, e.g. "myspace") — billing/quota boundary
      └── Project (e.g. "openclaw")
           └── Stage (e.g. "main") — like a branch/environment
                └── Deployment (e.g. "openclaw2") — actual running app
```

## Confirmed Endpoints (GET)

### Auth / User

| Method | Path | Notes |
|---|---|---|
| GET | `/auth` | Current user from API key |
| GET | `/userscope/{uid}/scopes` | Spaces accessible to user |

### Scope (Space)

| Method | Path | Notes |
|---|---|---|
| GET | `/scope/{scope}` | Space detail |
| GET | `/scope/{scope}/members` | Member list |
| GET | `/scope/{scope}/resource/limit` | Quota limits |
| GET | `/scope/{scope}/resource/stat` | Current usage |
| GET | `/scope/{scope}/cluster?onlyScoped=true` | K8s clusters |

### Project

| Method | Path | Notes |
|---|---|---|
| GET | `/project?uid={uid}` | All projects by user |
| GET | `/project/{scope}` | Projects in a space |
| GET | `/project/{scope}/{project}` | Project detail |
| GET | `/project/{scope}/{project}/stage` | Stage list |
| GET | `/project/{scope}/{project}/stage/{stage}` | Stage detail |
| GET | `/project/{scope}/{project}/stage/{stage}/stat` | Stage stats |
| GET | `/project/{scope}/{project}/stage/{stage}/cluster` | Cluster binding |
| GET | `/project/{scope}/{project}/stage/{stage}/deployment` | All deployments |
| GET | `/project/{scope}/{project}/stage/{stage}/events?deployment={name}` | K8s events (Started, Pulled, Failed, ...) |
| GET | `/project/{scope}/{project}/stage/{stage}/secret` | Secret store (⭐ returns raw values — 귈 명확) |
| PUT | `/project/{scope}/{project}/stage/{stage}/secret` | Secret store 상세는 아래 섹션 |
| GET | `/project/{scope}/{project}/stage/{stage}/vars` | Stage-level common vars |
| GET | `/project/{scope}/{project}/stage/{stage}/route` | Stage routes |

### Deployment (the meaty layer)

| Method | Path | Notes |
|---|---|---|
| GET | `.../deployment/{name}` | Deployment detail (request + stat) |
| GET | `.../deployment/{name}/stat` | Lightweight stat |
| GET | `.../deployment/{name}/session` | Past deployment requests |
| GET | `.../deployment/{name}/session/latest` | Last deployment request (includes env values!) |
| GET | `.../deployment/{name}/resource/service` | Live K8s Pod info + CPU/mem usage ⭐ |
| GET | `.../deployment/{name}/resource/route` | Ingress + entrypoints |
| GET | `.../deployment/{name}/resource/volume` | PVC info |
| GET | `.../deployment/{name}/resource/log` | 🔨 EXISTS but needs right params (currently returns cluster error) |
| GET | `.../deployment/{name}/resource/pod` | 🔨 EXISTS but needs right params |

### Resource catalog & limits (구독 푹 확인용, 핵심!)

클라우드타입은 선구독 모델 — 리소스 푹을 먼저 사고 그 안에서 deployment에 할당.
아래 3개의 관계: **`available = limit - stat`** (검증됨).

| Method | Path | Notes |
|---|---|---|
| GET | `/scope/{scope}/resource/limit` | 구독한 **총 푹** + 서비스 당 제약 (`maxCPUPerService`, `maxMemoryPerService` 등) |
| GET | `/scope/{scope}/resource/stat` | 지금 **사용 중인** 양 + `stats[]` 배열에 서비스별 디테일 (cpu/memory/disk/replicas/status/exposes/entrypoints 포함) ⭐ |
| GET | `/scope/{scope}/resource/available` | **할당 가능 잔여량** (메모리 늘릴 수 있는지 차근 이 값 기준) |
| GET | `/scope/{scope}/cluster/{cluster}` | Cluster detail |

**주요 키 (limit/available 공통)**:
- `cpu`, `memory`, `disk`, `running` — stable 노드 총/잔여 (메모리는 GB)
- `maxReplicas`, `maxCPUPerService`, `maxMemoryPerService`, `maxDiskPerService` — **서비스 1개 당 제약** 
  (하지만 실질적 한도는 `available` 이하)
- `spot.*`, `ephemeral.*` — 다른 노드 타입의 별도 푹
- `service`, `servicePerStage`, `project`, `stage` — 개수 제약
- `maxImageSize` 검, `logRetention`(15일), `deploymentRetention`(15개) 등

**SDK 활용 패턴**:
- 배포 전: 사용자가 명시적 리소스 요구하면 `available`과 비교 → 부족이면 "콘솔에서 푹 증량 필요"
- OOM 진단 보고 시: `available.memory` 포함해 "늘릴 수 있는 한도 X GB입니다" 안내
- **자동 증량 절대 금지** — 구독/결제 API 자체가 scope 밖 (운영자 명시)

### Catalog

| Method | Path | Notes |
|---|---|---|
| GET | `/app/presets` | App templates (~106 entries, ~1.6MB) |
| GET | `/app/presets?offset=0&limit=200` | Paginated |
| GET | `/app` | All apps catalog (large, ~1.9MB) |
| GET | `/app/metadata` | App metadata (~680KB) |
| GET | `/app/categories` | (returned null in test) |

### GitHub 연동 정책 (운영자 명시, 2026-05-27)

클라우드타입 스킬 사용자는 **이미 cloudtype↔github 연동을 해둔 상태**가 전제.
스킬은 절대로 연동을 설정/해제하지 않으며, **이미 되어 있는 연동을 활용**만 함.

#### Tier 1 — 배포에 직접 사용 (조회조차 불필요)

사용자가 repo URL과 브랜치를 명시한 경우, OAuth API 호출 없이 바로 PUT:

```jsonc
"context": { "git": { "url": "https://github.com/<owner>/<repo>.git", "branch": "main" } }
```

→ cloudtype 서버가 저장된 GitHub App credential로 clone (public/private 무관).
**곧 fruit-shop / demo-meeting-backend 배포가 이 동작 활용 (둘 다 public이었지만, private도 같은 원리 추정 — 검증 필요).**

#### Tier 2 — 조회 전용 (사용자 요청이 모호한 경우에만)

아래 에드포인트는 모두 GET이며 read-only:
- "내 GitHub 연동 되었나?" → `/oauth/github/has`
- "내 레포 중에 ~~ 찾아줘" → `/oauth/github/accounts` + `/oauth/github/repository/{installationId}`
- "이 레포의 브랜치 목록?" → `/.../repository/{installationId}/{repo}/branch`

#### Tier 3 — **절대 금지**

- `DELETE /user/authconfig/{uid}/github` (연동 해제)
- 연동 설정 변경 일체
- GitHub App 최초 install (브라우저 OAuth, API 자체 없음)

### User / OAuth / Auth (캐처 #5에서 발견, 2026-05-26)

| Method | Path | Notes |
|---|---|---|
| GET    | `/auth/auth/{uid}` | uid 기반 auth 조회 (사이드패널 등) |
| GET    | `/user/byuid?uid={uid}` | 유저 정보 by uid |
| GET    | `/user/authconfig/{uid}` | 유저의 전체 auth config |
| GET    | `/user/authconfig/{uid}/github` | GitHub 연동 설정 |
| DELETE | `/user/authconfig/{uid}/github` | GitHub 연동 해제 |
| GET    | `/oauth/github/has` | 현재 세션에 GitHub 일대답 토큰 존재 여부 |
| GET    | `/oauth/github/accounts` | 연결된 GitHub 계정 목록 (installation 단위) |
| GET    | `/oauth/github/repository/{installationId}` | 해당 installation의 repo 목록 |
| GET    | `/oauth/github/repository/{installationId}/{repo}/branch` | repo 브랜치 목록 (`["main"]`) |

→ **GitHub 연동 (repo 목록 조회, 브랜치 선택, 연동 해제) API 공개 확인**.
   최초 GitHub App install 자체는 브라우저 OAuth flow이지만, 그 이후 설정은 API로 가능.
   v1 스코프 안에 **GitHub repo/branch 선택**은 포함 가능 (식별되지 않은 repo 탐색 자동화).

### 기타 read API (캐처 #5에서 발견)

| Method | Path | Notes |
|---|---|---|
| GET | `/stage?uid={uid}&stage=@{scope}/{project}:{stage}` | stage 조회 (URL-encoded scope/project/stage) |
| GET | `/scope/{id16}?byid=true` | scope id로 조회 (이름 대신) |
| GET | `/project/{scope}/{project}/stage/{stage}/resource/route` | stage 레벨 라우트 (이전에 알던 `/stage/{stage}/route` 와 별개) |

## WebSocket Endpoints ⭐

All under `wss://api.cloudtype.dev/...`. Used for streaming logs and
interactive terminal. Same handshake protocol across all three.

| Endpoint | Purpose |
|---|---|
| `/project/logs` | Runtime stdout/stderr stream |
| `/project/build/logs` | Build progress stream |
| `/project/attach` | Interactive shell (pty) |

### Handshake

Browser cannot set Authorization on WS upgrade, so the server uses a
**`prepare` envelope** as the first message. Client sends JSON:

```json
{
  "type": "prepare",
  "params": {
    "scope": "myspace",
    "project": "openclaw",
    "stage": "main",
    "deployment": "channel-backend",
    "options": {
      "follow": true,
      "pretty": false,
      "tailLines": 500,
      "previous": false,
      "timestamps": true
    }
  },
  "headers": {
    "Authorization": "Bearer <JWT>",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*"
  }
}
```

Server replies with `"accept"` (plain text). Then streams log chunks
(plain UTF-8 text, possibly multiple lines per frame).

### Log frame format

Each line: `<RFC3339 nano timestamp> <stdout/stderr text>`

```
2026-05-26T07:08:01.072250947Z {"ts":"...","level":"info","msg":"🚀 channel-backend listening","port":8000}
```

When `timestamps: false`, leading timestamp is omitted.

### Build log frame format

Free-form text with emojis (🏁 / 👉 / 🙌 / 🚀 / ✅). Example:

```
🏁 Deployment started ...
👉 Prepare build
🙌 No build required.
🚀 Deploy to a cluster
✅ Done.
```

Or for a fresh build:

```
🏂 Build runner(sel-1) is starting...
  ├ Build type is dockerfile
  └ Build env is {"NODE_ENV":"p*********", ...}    ← env values masked here
```

### Terminal (/project/attach)

Same prepare envelope, then client can send a resize control message:

```json
{"r": 60, "c": 128}    // rows, cols
```

Server streams pty output (raw ANSI escape sequences — includes mouse
reporting, alt-screen, etc). Client sends keystrokes as text frames.

### Verified working

Direct Python `websockets` connection with `Authorization: Bearer <key>`
in the prepare envelope returns live logs. No browser/console session
required.

## Key Object Shapes

### Deployment (the meaty one)

```jsonc
{
  "id": "mpeu83ip0ef0c2d3",
  "name": "openclaw2",
  "displayName": "오픈클로-디스코드AI봇",
  "owner": "<uid>",
  "scope": "myspace",
  "project": "openclaw",
  "stage": "main",
  "request": {                 // user-requested spec
    "name": "openclaw2",
    "app": "openclaw",         // preset name
    "options": { /* env vars, app-specific config */ },
    "resources": { "cpu": 2, "memory": 2, "disk": 10, "replicas": 1, "spot": false },
    "context": { "preset": "openclaw", "git": {} }
  },
  "stat": {                    // observed runtime state
    "status": "running" | "stopped" | "deploying" | "...",
    "ready": 1, "replicas": 1, "available": 1, "unavailable": 0,
    "exposes": [ { "protocol": "http", "port": 3000, "hostname": "openclaw2" } ],
    "entrypoints": [ { "link": "https://...cloudtype.app", "type": "http" } ],
    "routes": [ /* ... */ ],
    "volumes": [ /* PVCs */ ]
  }
}
```

## Discovered Identifiers (test account)

- `uid`: `mm8nufqy98769b8f`
- `scope`: `myspace` (Hobby plan)
- `project`: `openclaw`
- `stage`: `main`
- `deployments`: openclaw2, postgresqlchannel, channel-backend, meridian-global-landing, hk-materials-trading

## Known Plan Limits (from `/resource/available`, Hobby)

- Max image size: **5 GB**
- Log retention: **15 days**
- Deployment retention: **15 versions**
- Concurrent deploy: **3**
- Daily deploy count: **100**
- Per-service: 4 vCPU / 16 GB / 1000 GB disk
- Domains: **100**
- Projects: 15, Stages per project: 8, Services per stage: 32

## Write / Action API (Phase 2/3 discovered)

All observed from `app.cloudtype.dev6.har` (2026-05-26).

### Deployment control

| Method | Path | Body | Notes |
|---|---|---|---|
| PUT | `/project/{scope}/{project}/stage/{stage}/deployment/{name}/start` | (empty) | Start a stopped deployment |
| PUT | `/project/{scope}/{project}/stage/{stage}/deployment/{name}/stop` | (empty) | Stop a running deployment (verified) |
| DELETE | `/project/{scope}/{project}/stage/{stage}/deployment/{name}` | — | Delete deployment |

### Redeploy / Update (same endpoint)

There is **no dedicated redeploy endpoint** — `/redeploy`, `/deploy`,
`/apply`, `/rebuild`, `/rollout` all return 404. Instead, redeploying or
updating uses the same `PUT .../deployment` as creation:

- Same name + same spec → **redeploy** (new build session, new image)
- Same name + changed env / resources / branch → **update + redeploy**
- Different name → **create**

Verified by re-PUTting an existing deployment's spec — server returned a
new `deploying` session id and started a fresh build.

### Stage-level secrets (캐처 #9, 2026-05-27)

**배포환경 단위 공용 시크릿** — 따로 저장해둔 값을 배포 시점에 주입 (다음 캐처에서 방식 확인).

```
GET  /project/{scope}/{project}/stage/{stage}/secret
PUT  /project/{scope}/{project}/stage/{stage}/secret
```

GET 응답:
```jsonc
{
  "meeting-db-root-password": "meetroom-838d331e357c",   // ⚠️ 평문으로 돌아옴
  "postgresql-root-password": "1234"
}
```

PUT 요청:
```jsonc
{
  "secrets": {
    "meeting-db-root-password": "meetroom-838d331e357c",
    "postgresql-root-password": "1234",
    "abc": "1234",
    "def": "4567"
  },
  "merge": false    // false = 전체 교체 (기존에 있다가 누락된 시크릿은 삭제됨!), true = 추가/갱신만
}
```

### 🦶 시크릿 안전 정책 (SDK 권장)

- **읽기**: 자유롭게 (단 응답이 평문이므로 로그·사용자에게 출력 시 주의)
- **쓰기 (일반 요청)**: 자동으로 `merge: true` 강제 — 기존 시크릿 보존
- **쓰기 (전체 교체)**: `merge: false`는 사용자가 명시적으로 "모두 지우고 이걸로" 요청한 경우에만, 한번 재확인
- **이미 있는 키 덮어쓰기**: 한번 사용자에게 확인 ("이미 `X` 시크릿 있어요, 덮을까요?")
- **상세한 시크릿 삭제**: 별도 endpoint 미관측 (`merge: false`로 경우 누락으로 간접 삭제 가능)

### env / buildenv 항목의 2가지 형태 (캐처 #10, 2026-05-27)

`options.env[]` 또는 `options.buildenv[]` 의 각 항목은 **인라인 값** 또는 **시크릿 참조** 둘 중 하나:

```jsonc
// 형태 1: 인라인 값 (평문으로 spec에 보관)
{"name": "NODE_ENV",     "value":  "production"}

// 형태 2: 시크릿 참조 (민감 값에 권장) ⭐
{"name": "DB_PASSWORD",  "secret": "meeting-db-root-password"}
//          ↑                  ↑
//   컨테이너 안 env 이름      stage 시크릿 store의 키 이름
```

둘은 한 배열 안에 섞어서 들어갈 수 있음. env name과 secret key는 같을 필요 없으나 혀권장 권장.

### 🦶 SDK 자동 시크크화 정책 (권장)

사용자가 env를 평문으로 주는 경우 AI가 키 이름을 보고 자동 분류:

- `*PASSWORD*`, `*SECRET*`, `*TOKEN*`, `*KEY*`, `*PWD*`, `*PRIVATE*`, `*AUTH*` → 시크크화 권유 ("이거 시크릿으로 옮길까요?")
- `*URL*`, `*HOST*` 는 애매함 → 값 안에 인증정보 포함 여부 보고 결정 (`postgresql://user:PASS@...` 같으면 시크릿)
- `NODE_ENV`, `LOG_LEVEL`, `PORT`, 단순 flag들 → 인라인으로 유지

### ⭐ Rewrites — 소스 수정 없이 CORS 우회 (web preset, KB 권워)

**운영자 목표 "소스 수정 없이 배포 성공"의 핵심 도구.**

KB 출처: `cloudtype-kb.md` 줄 1662 ("리버스 프록시", docs.cloudtype.io/ko/developers/reverseproxy)

**동작**:
- 프론트엔드 코드가 **자기 자신을 호출** 하도록 작성하면 (예: `fetch('/api/...')`)
- web preset 면에서 이 호출을 가로채서 **다른 서비스로 프록시**
- 그래서 **CORS 문제·코드의 프론트↔백엔드 URL 분기·nginx 별도 운영 불필요**

**페이로드 구조 (추정, 캐처에서는 `[]` 보임)**:
```jsonc
"options": {
  "rewrites": [
    // 같은 stage 내 서비스 (드롭다운 선택 가능)
    {"from": "/api/*",  "to": "backend:3000"},     // 서비스 이름:포트
    // 또는 외부 URL 직접 입력 (추정)
    {"from": "/auth/*", "to": "https://other.example.com"}
  ]
}
```
✅ 쿼올라임: rewrites 입력된 실제 캐처 받아볼 필요 (다음 캡처 후 확정)

**⚠ 적용 가능 조건 (운영자 명시, 2026-05-27)**:

Rewrites는 "소스 수정 없이 모든 CORS 해결!"이 아니라 **코드가 이미 self-referential이어야 적용 가능**:

| 코드 형태 | Rewrites 적용 가능? | 필요 조치 |
|---|---|---|
| `fetch('/api/...')` (상대경로) | ✅ 가능 | rewrites 추가만 |
| `fetch(API_BASE + '/api/...')` (env 분기) | ✅ 가능 | env를 빈 string으로 설정 + rewrites 추가 |
| `fetch('https://hardcoded.com/api/...')` | ❌ 불가 | 코드 수정 필요 (상대경로로 변경) |

→ SDK 진단 시 먼저 코드의 fetch/axios 호출 패턴 분석 후 가능 여부 판정.

**우리의 회의실 데모 회고**:
- 데모의 Vue 코드는 케이스 (b) 에 해당 — `API_BASE` env 분기를 쓴 형태
- 그래서 rewrites 쓰려면 가능했음 (env 비워두고 rewrites 추가)
- 하지만 코드가 처음부터 하드코드 URL로 되어 있었다면 rewrites도 무력 — 코드 수정 필요.

### web preset 추가 옵션 정리

- `docbase` (예: `/dist`) — 빌드 산출물 서빙 루트
- `spa` (bool) — SPA 폴백 (404 → index.html)
- `nodeversion` (int) — 빌드용 Node 버전
- `rewrites` (array) — 리버스 프록시 규칙 ⛬

### Deployment options (전체 필드 — 측정됨, 2026-05-26 캐처 #5)

`options` 객체에 들어갈 수 있는 키들 (node@20 preset 기준, 다른 preset도 유사):

| key | 타입 | 예 | UI 라벨 / 목적 |
|---|---|---|---|
| `ports`              | string 또는 int | `"4000"` | 서비스 포트 |
| `env`                | array | `[{name,value}]` | 런타임 환경변수 |
| `buildenv`           | array | `[{name,value}]` | 빌드 타임 환경변수 |
| `install`            | string | `"npm ci"` | 설치 커맨드 |
| `build`              | string | `"npm run build"` | 빌드 커맨드 |
| `start`              | string | `"npm start"` | 시작 커맨드 |
| `healthz`            | string | `"/test"` | 헬스체크 HTTP 경로 (readiness probe) |
| `initialDelaySeconds`| string 또는 int | `"5"` | 헬스체크 시작 전 대기초 |
| `strategy`           | string | `"recreate"` | 배포 전략 (recreate / rollingUpdate 추정) |
| `npmrc`              | string | `"..."` | .npmrc 내용 (private npm registry 인증 등) |
| `docbase`            | string | `"/dist"` | (web preset) 정적 파일 루트 |
| `spa`                | bool   | `true` | (web preset) SPA 폴백 |
| `nodeversion`        | int    | `18` | (web preset 빌드 시의 node 버전) |
| `rootusername`/`rootpassword`/`database` | string | — | (DB preset 전용) |
| `config`             | string | postgresql.conf 와 유사 내용 | (DB preset) 추가 설정 논리 파일 |
| `tz`                 | string | `"Asia/Seoul"` | (DB preset) 타임존 (TZ env로 매핑 추정) |

### Dockerfile preset 완전 매핑 (캐처 #7, 2026-05-27)

평범한 framework preset (node/python/...)와 다르게, **도커 레벨 제어를 다 노출**하는 멐세 preset.

```jsonc
{
  "name": "my-service",
  "app": "dockerfile",                  // ⚠️ framework preset과 달리 app=preset 이름 그대로
  "options": {
    "ports": "3001",
    "dockerfile":      "Dockerfile",   // repo 내 Dockerfile 경로
    "dockerfiletext":  "FROM ...",     // ⭐ 인라인 Dockerfile (repo 안 Dockerfile 없어도 도우면 빌드 가능)
    "commands":        "...",           // CMD/entrypoint 오버라이드
    "uid":             "1000",          // 컨테이너 실행 UID (non-root)
    "gid":             "2000",          // 실행 GID
    "shell":           "/bin/sh",       // 명령 실행 셰
    "args":            [{"name":"K","value":"V"}],  // docker build --build-arg (buildenv와 유사하나 별도 구조)
    "labels":          [{"name":"K","value":"V"}],  // k8s pod label 또는 docker image label
    "env":             [{"name":"K","value":"V"}],  // 런타임 ENV
    "healthz":         "/health",
    "initialDelaySeconds": "5",
    "strategy":        "rolling"        // "rolling" 또는 "recreate" (k8s deployment strategy)
  },
  "resources": {"spot": false, "cpu": 1, "replicas": 2},
  "context": {
    "git": {"url": "https://...", "branch": "main"},
    "preset": "dockerfile"
  }
}
```

**핵심 활용 패턴**:
- repo 안 Dockerfile 없는 의문의 프로젝트 → **AI가 적절한 Dockerfile 생성해서 `dockerfiletext`로 주입** 가능
- preset 자동 감지 안 되는 비표준 스택 → dockerfile preset으로 대체
- non-root 실행, 특이 셰 필요 등 고급 설정은 dockerfile preset 전용

### Container preset 완전 매핑 (캐처 #8, 2026-05-27)

**빌드 없는 배포** — 외부 도커 이미지를 그대로 pull 해서 실행.

```jsonc
{
  "name": "my-container",
  "app": "container",
  "options": {
    "image":           "nginxinc/nginx-unprivileged:1.24",  // ⭐ 필수: 외부 docker 이미지 (Docker Hub, GHCR, ECR,  …)
    "ports":           "8088",
    "commands":        "...",            // 이미지의 CMD/ENTRYPOINT 오버라이드 (추정)
    "uid":             "1000",           // 실행 UID
    "gid":             "1000",           // 실행 GID
    "shell":           "/bin/sh",
    "env":             [...],
    "healthz":         "/...",
    "initialDelaySeconds": "3",
    "strategy":        "rolling"
  },
  "resources": {"spot": false},
  "context": {"preset": "container"}    // ⚡ git 필요 없음 (바로 이미지에서 실행)
}
```

**dockerfile vs container vs framework preset 차이**:

| 특성 | container | dockerfile | framework (node 등) |
|---|---|---|---|
| 빌드 단계 | ❌ 없음 (pull만) | ✅ docker build | ✅ npm install + build |
| `image` (외부 이미지) | ⭐ 필수 | ❌ | ❌ |
| `dockerfile` / `dockerfiletext` | ❌ | ✅ | ❌ |
| `install` / `build` / `start` | ❌ | ❌ | ✅ |
| `context.git` | ❌ (소스 불필요) | ✅ 필수 | ✅ 필수 |
| Docker Hub / external registry pull | ✅ | ❌ | ❌ |

**활용 패턴**:
- 곧바로 외부 이미지 띄우기 (예: `nginx`, `redis`, `mysql`, GitHub Container Registry)
- AI의 "코드 없이 특정 이미지 배포" 요청 → container preset 선택
- **⚠ private registry 인증**은 캐처에 없음 (공개 이미지만 검증됨) → 올아 필요 시 추가 캐처 필요

### App 필드 패턴 (이제서 완전 명확)

| preset 종류 | `app` 값 패턴 | 예 |
|---|---|---|
| Framework (node/python/...) | `<runtime>@<version>` | `node@20`, `python@3.11` |
| Web (빌드 결과 서빙) | `web` | html, vue, react 등 preset 모두 |
| Dockerfile | `dockerfile` | preset 이름 그대로, 코드 + Dockerfile 빌드 |
| Container | `container` | preset 이름 그대로, 빌드 없이 외부 이미지 실행 |
| DB | `<engine>@<version>` | `postgresql@16`, `mariadb@10`, `redis@7` 등 |

→ preset 매타의 `config[0].app` 값을 참조하여 결정. 몇번이라도 타입명으로 명확한 며측 가능.

### PostgreSQL preset 완전 매핑 (캐처 #6, 2026-05-27)

```jsonc
{
  "name": "postgresql",
  "app": "postgresql@16",
  "options": {
    "rootusername": "root",          // → POSTGRES_USER (추정)
    "rootpassword": "<secret>",      // → POSTGRES_PASSWORD
    "database":     "<dbname>",      // → POSTGRES_DB
    "config":       "<conf text>",   // 선택, postgresql.conf 형식
    "tz":           "Asia/Seoul"     // 선택, TZ env
  },
  "resources": {
    "spot": false,
    "cpu": 1, "memory": 1,
    "disk": 10    // ⚠️ DB는 disk 필수 (UI 디폴트 10GB)
  },
  "context": {"preset": "postgresql"}
}
```

⚡ **운영자의 시각 교정 검증**: DB preset 은 그냥 docker postgres 이미지 + preset 이 노출한 options 이
자동으로 컨테이너 ENV (POSTGRES_*)로 매핑되는 구조. 사용자는 docker postgres env 컴벤션을 몰라도 됨.

다른 DB preset도 유사한 구조로 추정 (mariadb / mysql / mongo / redis):
- 이름은 같은 `rootusername` / `rootpassword` / `database` 세트일 가능성 높음
- 각자 명세는 커버 시나리오로 확인 필요

**타입 혐의**: UI는 `ports`/`initialDelaySeconds`를 **string**으로 보냄 (그래도 서버가 수용함).
API 직접 호출 시 int도 통해서 뒀 다 동작 확인됨. SDK는 int로 통일 권장.

### ⚠️ Resources 자동 조정 **금지** (운영자 정책, 2026-05-27)

**AI/스킬은 절대로 리소스 사양을 자동으로 변경하지 않는다.**

- 모든 배포는 디폴트 (서버 최저 사양)로 나감. 그래서 PUT 페이로드에서 `resources`는 사용자 명시가 없으면 아예 빼고 보낸다.
- OOM/느림 등 이슈 감지 시도 **자동 fix 없이 사용자에게 보고 + 옵션 제시 + 결정 대기**.
- 자동 조정 금지 근거:
  1. **구독 푹 제한** — 클라우드타입은 선구독 모델, 구독한 푹을 초과하면 배포 자체 실패
  2. **사용자 학습 보존** — 자기 워크로드를 모르는 채 클라우드타입을 쓰면 더 큰 문제 적층
  3. **진짜 원인 가려짐** — OOM이 실제도 메모리 부족일 수도 있지만 메모리 누수/무한루프/부적절한 알고리즘이 원인일 수도 있음
  - 과금 폭탄은 이유 아닔 (구조적으로 불가). 다른 deployment 영향도 아닔 (k8s pod limit 격리).

### Resources 부분 업데이트 (검증됨, 이론적 동작)

PUT 시 `resources`에 일부 키만 보내도 나머지는 서버 디폴트로 채워짐:

- 운영자 캐처: `resources: {spot: true, memory: 0.25}` 만 보냄
- 응답: `{spot: true, cpu: 0, memory: 0.25, disk: 0, replicas: 1}`
- → 누락된 키는 자동 채움

### Context.git.path (슬래시 선택적)

KB는 `/pathname` 스타일을 제시하지만 UI는 슬래시 없이 `"backend"` 도 보냄 (응답에도 그대로 echo).
실제 빌드 동작은 모두 검증 아직 안 됨 (UI 프롬프트는 PUT만 있고 빌드 결과 머파다 부재).
SDK 권장: `/`로 시작해서 보내기 (둘 다 동작하더라도 일관성).

### Deployment create / update

```
PUT /project/{scope}/{project}/stage/{stage}/deployment
```

Used for both creating new deployments AND updating existing ones (idempotent).
Body:

```jsonc
{
  "request": [{                      // can batch multiple
    "name": "salesforce-mcp",
    "app": "node@16",                // preset name ("app" key, can include version with @)
    "options": {
      "env": [{"name": "NODE_ENV", "value": "production"}],
      "ports": 3000,                 // single int OR array
      "buildenv": []                 // build-time env
    },
    "resources": {
      "spot": false,                 // spot instance
      "cpu": 1, "memory": 1,         // GB
      "replicas": 2                  // omit → defaults to 1
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

Response: array with full deployment record including `id`, `deploying`
(build session id), and the echoed `request`.

### Project create

```
POST /project
Body: {"scope": "myspace", "name": "test", "displayName": null, "cluster": "gke-exp-0"}
```

## Preset 권장 options (검증됨)

주요 preset 별로 실제 다루는 options 세트:

| preset | request.app | 필수 options | docbase | 블드 산출물 위치 |
|---|---|---|---|---|
| `html`        | `web`              | `docbase`, `spa`, `ports` | `/` | — (정적) |
| `vue`         | `web`              | `docbase`, `spa`, `ports`, `nodeversion`, `install`, `build`, `buildenv[]` | **`/dist`** | `dist/` |
| `vanilla-vite`| `web` (추정)     | (vue와 유사, 미검증)         | `/dist` (권장) | `dist/` |
| `node`        | `node@<ver>`       | `ports`, `env[]`, `install`, `start` | — | — |
| `postgresql`  | `postgresql@<ver>` | `rootusername`, `rootpassword`, `database` | — | — (블드 없음) |

**골딜**: vue/vite 계열은 docbase 기본값이 `/` → prod build asset(`dist/index.html`)이 아닌
repo 루트의 `index.html` (소스 원본)을 서빙함. **반드시 `docbase: "/dist"` 명시 필요.**

## Multi-deployment 내부 통신 (검증됨)

같은 `stage` 안의 deployment끼리는 **deployment name이 그대로 내부 hostname**:
- 예: backend 속에서 `PGHOST=meeting-db`, `PGPORT=5432` 로 접속 성공
- 외부 공개 URL이 아니라 내부 cluster 네트워크 경유
- 프론트는 build-time에 백엔드 public URL을 env로 받아서 번들에 굳어넣는 식 권장 (예: Vite의 `VITE_*`)

## Monorepo / 서브디렉토리 배포 (✅ 검증됨)

**정답 키: `context.git.path`** (subpath 아님 — 처음 견 함정)

- KB(`cloudtype-kb.md` 줄 1470, "서브 디렉토리 설정")에 명시:
  ```yaml
  context:
    git:
      path: /pathname
  ```
- 레포 루트 기준 절대 경로 스타일 (`/backend`, `/frontend`).
- 검증 케이스: 같은 monorepo (`alerundev/demo-meeting-room`)에서
  `path: /backend` 으로 node@20 배포 해서 `/api/rooms` 200 OK 확인.
- **함정**: `subpath`라는 키도 서버가 응답에 echo 하지만 실제 빌드에는 무시됨.
  → `subpath` 어떤 버전의 하위 호환 키입을 수 있으나, **API의 공식 이름은 `path`**.
- SDK는 `path` 사용을 원칙으로.

## Env vars 응답 마스킹 (검증됨)

- GET deployment 응답에서는 env value의 끝 4자 + `len=0` 표기 수준으로 가리움 (실제는 이상한 표기이지만 핵심은 value 제대로 안 돌려줌).
- 빌드 로그 "Build env is {...}" 출력에선 앞 1자 + `*` 길이 만큼 으로 masking.
- **실제 값은 컨테이너 내에서는 평문으로 존재.** (동작 검증으로 확인)
- → SDK는 env 값을 응답으로 재확인하지 말고, 설정 의도를 때론로 자체 보관하거나 동작 테스트로 검증.

## PUT 응답의 stale spec (주의)

PUT 직후 응답에서 **이전 spec이 echo 될 수 있음** (예: git url 교체 후에도 올드 git url 표시).
하지만 `deploying` 필드는 새 build session id로 갱신됨 → **PUT 성공 여부는 `deploying`이 이전와 다른지로 판단**.
실제 적용된 spec은 빌드 로그의 `repository` 메타에서 확인.

## Field Quirks (검증 중 발견)

- **`request.app` 필드는 preset 이름이 아니라 `preset.config[0].app` 값.**
  예: preset `html`의 config app은 `"web"`. preset 이름을 그대로 `app`에 넣으면
  `app "<name>" in "<deployment>" does not exist` (50401 ServiceError).
  → preset 메타에서 `config[0].app`을 꺼내서 써야 함.
- **`prefer` 필드 2개 존재:**
  - `deployment.prefer` — 사용자 의도 (`"start"` / `"stop"`)
  - `deployment.stat.prefer` — 현재 컨트롤러 상태 (생성 직후엔 잠깐 `"stop"`)
- **DELETE 후 단건 GET이 404가 아니라 `HTTP 200` + empty body.**
  → 존재 확인은 `body` 파싱 가능 여부 또는 stage의 deployment 목록으로.
- **DELETE 시 routes/entrypoints도 함께 정리됨.** 라이브 URL은 즉시 404.
- **빌드 로그 WS 정상 종료:** 빌드 끝나면 close code `1005`로 닫힘. 정상 처리.
- **html preset 빌드 시간 ≈ 19초.** Dockerfile build이지만 base 캐시 많아 가벼움.

## TODO — Endpoints to discover next

- [x] ~~Events / History~~ — `/stage/{stage}/events?deployment={name}`
- [x] ~~Live metrics~~ — inside `/resource/service`
- [x] ~~**Runtime logs**~~ — `wss://.../project/logs`
- [x] ~~**Build logs**~~ — `wss://.../project/build/logs`
- [x] ~~**Terminal**~~ — `wss://.../project/attach`
- [x] ~~**Start/Restart**~~ — `PUT .../deployment/{name}/start`
- [x] ~~**Delete deployment**~~ — `DELETE .../deployment/{name}`
- [x] ~~**Create deployment**~~ — `PUT .../deployment` (with full spec)
- [x] ~~**Create project**~~ — `POST /project`
- [x] ~~**Stop**~~ — `PUT .../deployment/{name}/stop` ✅ verified
- [x] ~~**Redeploy**~~ — same `PUT .../deployment` re-fires build ✅ verified
- [x] ~~**Env vars update**~~ — same PUT with changed env (implicit, same path)
- [x] ~~**Scale**~~ — same PUT with changed resources (implicit, same path)
- [x] ~~**Delete deployment 검증**~~ — `DELETE` 200, body empty, route 자동 정리 ✅
- [x] ~~**HTML preset 생성 e2e**~~ — alerundev/demo-fruit-shop → fruit-shop deployment ✅ (2026-05-26)
- [ ] **Delete project / stage**
- [ ] **Webhooks / GitHub integration setup** (out of scope for v1)
