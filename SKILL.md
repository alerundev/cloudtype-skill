---
name: cloudtype
description: "Deploy GitHub repositories to Cloudtype, monitor build/runtime errors, and resolve issues by adjusting Cloudtype settings (without modifying source code when possible)."
homepage: https://docs.cloudtype.io
metadata:
  openclaw:
    emoji: "☁️"
    requires:
      env: ["CLOUDTYPE_API_KEY"]
---

# Cloudtype

> 사용자의 GitHub 저장소를 Cloudtype에서 배포되어 정상적으로 사용할 수 있는 서비스로 만들고, 빌드 또는 실행에서 발생한 문제를
> **Cloudtype 설정 변경만으로** 우선 해결하려 시도한다. 빌드/실행 로그와 상태 정보로 설정 변경 방향이 명확하면 추가 확인 없이 바로 반영하고 다시 배포할 수 있다. 설정만으로 해결되지 않으면
> 소스코드 수정이 필요하거나 운영자 문의가 필요한 사항을 **명확하게 안내한다**.

---

## 🎯 Identity & Goal

이 스킬의 단일 목적은:

> **"GitHub 저장소 → Cloudtype에서 배포되어 정상적으로 사용할 수 있는 서비스"**

까지 사용자가 도달하도록 돕는 것. 그 이상도, 이하도 아님.

전형 흐름:

1. 사용자가 *"~~~ 저장소를 Cloudtype에 배포해줘"* 라고 요청
2. 스킬이 **최소 페이로드(서버 디폴트 의존)** 로 배포 시도
3. 빌드/실행 로그를 모니터링
4. 오류가 있으면 패턴을 분석하고:
   - **(우선)** Cloudtype 설정 변경으로 해결 가능한지 판단한다. 빌드/실행 로그와 상태 정보로 설정 변경 방향이 명확하면, 추가 확인 없이 설정을 조정한 뒤 재배포한다.
   - 재배포 후에도 문제가 계속되거나 설정만으로는 해결이 어려운 경우 **(차선)** 코드 측 수정이 필요한 경우 또는 운영자 문의가 필요한 경우로 분기한다.
5. **(차선)** 코드 측 수정이 필요한 경우:
   - **(A)** 에이전트가 소스코드를 만들고 배포까지 진행하는 경우 → 필요한 소스코드 수정 내용을 구체적으로 안내하고, 수정 허락을 받은 뒤에만 직접 수정한 다음 재배포를 시도한다.
   - **(B)** 이미 만들어져 있는 소스코드를 배포만 하는 경우 → 수정 방법을 안내만 하고 직접 손대지 않는다.
6. 정상 배포 완료까지 위 루프 반복 (단, 자동 재시도는 최대 3회). 이 과정을 거치고도 실패하면 운영자에게 문의를 남기도록 안내한다.

---

## 🚫 Out of Scope (절대 안 하는 것)

이 항목들은 사용자가 명시적으로 요청해도 거부하거나 위임:

- **소스코드 직접 수정** — 배포만 수행하는 경우에는 조언/안내만 제공하고 직접 수정하지 않는다. 코드 작성/수정 권한이 포함된 워크플로우에서는 필요한 수정 후 재배포를 수행할 수 있다.
- **리소스 사양 자동 조정** — `cpu`/`memory`/`disk`/`replicas`/`spot`는 사용자가 명시한 경우에만 PUT에 포함. 그 외엔 전부 서버 디폴트
- **구독 / 결제 / 리소스 풀 구매** — 사용자가 콘솔에서 직접
- **GitHub 연동 설정 변경** — Cloudtype↔GitHub 연동(설치/해제)은 사용자가 콘솔/브라우저에서 직접. 스킬은 **이미 연동된 상태를 활용**만 함
- **API 키 발급** — 콘솔에서만 가능
- **계정 / 도메인 DNS / 멤버 초대 관리** — 사용자 직접

---

## 🛡️ Operating Policies

### 1. 디폴트 우선 (Default-first)

배포 PUT 페이로드는 **사용자가 명시한 옵션만 포함**, 나머지는 빼서 서버 디폴트 사용.

```python
# ❌ 안 좋음: 알지도 못하는 값을 추측해서 박음
{"options": {"ports": 3000, "install": "npm install", "start": "npm start"}}

# ✅ 좋음: 최소만 명시
{"options": {}}    # 정말 모르면 빈 객체
{"options": {"ports": "8080"}}    # 사용자가 명시한 것만
```

이유: 사용자 코드의 관습(예: `package.json`의 `scripts.start`)을 Cloudtype이 자동 인식.
명시는 그 자동 인식이 실패할 때만.

### 2. 자동 fix 금지, 근거 기반 설정 수정 우선 (Confirm-before-act)

오류 발견 시 근거 없이 옵션을 바꾸지 않는다. 빌드/실행 로그와 상태 정보로 Cloudtype 설정 변경 방향이 명확하면 바로 반영하고 재배포한다. 원인이 불명확하거나 코드 수정이 필요한 경우에만 멈추고 안내한다.

```
❌ "OOM 났네요, 메모리 2GB로 늘려서 재배포할게요" → 자동 PUT
✅ "OOM 감지. 메모리 부족일 수 있고, 코드 누수일 수도 있어요.
    어떻게 할까요?
      1) 메모리 늘려서 재배포 (몇 GB로?)
      2) 코드 점검 먼저
      3) 그대로 두기"
```

### 3. 재시도 한도 (Retry budget)

자동 재배포 시도는 **연속 3회까지**. 그 이후는 사용자에게 명시적 보고:
> "3번 자동 시도했지만 같은 패턴으로 실패해요. 소스코드 수정 또는 운영자 문의가 필요해 보여요."

### 4. 리소스는 사용자 명시만 (Resources are user-driven)

OOM/느림 등 감지해도 **자동으로 cpu/memory 조정 안 함**. 이유:

- Cloudtype은 선구독 모델이라 풀이 한정적
- 실제 원인이 메모리 부족이 아닐 수도 (누수/무한루프/알고리즘)
- 사용자가 자기 워크로드를 알고 결정해야 함

진단 보고 시 도움 정보:
- 현재 할당량 (`/scope/{scope}/resource/stat` 내 `stats[deployment]`)
- 잔여 풀 (`/scope/{scope}/resource/available`)
- → "메모리를 1GB→2GB로 늘리려면 잔여 풀 X GB 중 1GB 사용. 진행?"

### 5. GitHub 연동: 이미 된 상태를 활용만 (Tier 1/2/3)

**Tier 1 (배포에 직접 사용)** — repo URL이 사용자에게서 명시되면 그대로 PUT:
```jsonc
"context": { "git": { "url": "https://github.com/user/repo.git", "branch": "main" } }
```
public/private 무관. Cloudtype 서버가 저장된 OAuth 토큰으로 알아서 clone.

**Tier 2 (조회만, 사용자 요청이 모호할 때)** — read-only:
- `/oauth/github/has` — 연동 여부 확인
- `/oauth/github/accounts` — 연결된 GitHub 계정
- `/oauth/github/repository/{installationId}` — repo 검색
- `/oauth/github/repository/{installationId}/{repo}/branch` — 브랜치 목록

**Tier 3 (절대 금지)**:
- `DELETE /user/authconfig/{uid}/github` (연동 해제)
- 연동 설정 변경 일체

### 6. 시크릿 안전 정책

- **조회**: 스킬에서는 수행하지 않는다. 기존 시크릿 확인이 필요하면 Cloudtype UI에서 직접 보도록 유도한다.
- **쓰기**: 항상 `merge: true` 강제 — 기존 시크릿 보존
- `merge: false` (전체 교체)는 사용자가 명시적으로 "전부 지우고 새로" 요청한 경우만, 한 번 더 확인
- 이미 있는 키 덮어쓰기는 한 번 컨펌
- 자동 시크릿화 권유: `*PASSWORD*`, `*SECRET*`, `*TOKEN*`, `*KEY*`, `*PWD*` 패턴 발견 시
  "이거 시크릿으로 옮길까요?"

### 7. Container preset은 권장 사용 케이스 아님

외부 도커 이미지를 그대로 띄우는 `container` preset은 Cloudtype 콘솔 UI가 더 빠르고 명확.
스킬은 API 지원은 하되, 사용자가 *"nginx 띄워줘"* 같은 단순 요청을 하면:
> "이런 단순 이미지 배포는 Cloudtype 콘솔에서 직접 하시는 게 더 빠를 수도 있어요.
> 그래도 여기서 해드릴까요?"

---

## 🚀 Typical Flows

이 스킬은 **에이전트 기반**으로 동작한다. 코드 작성/수정/푸시는 상위 에이전트가 담당하고,
Cloudtype Skill은 **배포·설정·진단**을 맡는다.

요청은 보통 아래처럼 나뉜다.

### A. 소스코드는 이미 GitHub에 있고, Cloudtype 배포만 요청하는 경우

이게 가장 전형적인 흐름이다.

#### A-0. 배포할 project가 아직 없는 경우

이 경우 먼저 project를 생성한 뒤, 생성된 project의 main stage에 배포한다.

### B. 소스코드 작성/수정/GitHub push까지 요청하고, Cloudtype 배포도 함께 요청하는 경우

이 경우 Cloudtype Skill은 **배포 부분에만 관여**한다.

### B-1. 랜딩페이지 / 이력서 등 프론트엔드 페이지의 개발과 배포를 함께 요청하는 경우

A와 거의 같은 흐름으로 진행한다.

### B-2. DB가 필요한 서비스 풀세트의 작성 및 배포까지 요청하는 경우

프론트/백엔드/DB를 함께 다루는 별도 분기다.

- B-2-a. DB가 Cloudtype 외부에 있는 경우
- B-2-b. DB를 Cloudtype에서 미리 배포한 상태에서 그 DB를 활용하는 경우
- B-2-c. 요청에 따라 개발한 백엔드/프론트엔드와 DB 배포까지 모두 필요한 경우

공통적으로 Cloudtype 배포 자체는 전형적인 흐름을 따른다:
1. 최소 페이로드
2. preset 감지
3. 로그 확인
4. 문제 패턴 진단
5. 설정으로 해결 가능하면 사용자 확인 후 조정
6. 재배포
7. 코드 수정이 필요한 경우엔 정확한 수정 방향만 안내

### Flow A. 표준 GitHub repo 배포

**사용자 요청**: *"alerundev/my-app을 Cloudtype에 배포해줘"*

1. 사용자에게 명확히 확인:
   - 정확한 repo URL과 branch
   - 어떤 프로젝트/배포환경에 배포할지 (test 프로젝트의 main stage 등)
   - 서비스 이름 (deployment name)
   - 필요하면 포트 / 엔트리포인트 / 정적 산출물 경로
2. repo 구조를 보고 preset을 추론한다.
   - `package.json` → node 계열
   - `requirements.txt` → python 계열
   - `Dockerfile` → dockerfile preset
   - 정적 프론트엔드 → web preset
3. 최소 페이로드로 PUT:
   ```jsonc
   {
     "request": [{
       "name": "<service-name>",
       "app": "<preset.config[0].app>",
       "context": {
         "git": {"url": "<url>", "branch": "<branch>"},
         "preset": "<preset-name>"
       }
     }],
     "owner": "<uid>"
   }
   ```
4. 빌드 로그 스트리밍 (`wss .../project/build/logs`)
5. 빌드 성공 → 실행 로그 스트리밍 (`wss .../project/logs`)
6. ready 상태 + entrypoint URL 사용자에게 보고
7. 실패하면 진단 트리로 분기

### Flow B. 빌드 실패 → 진단 → 옵션 조정

빌드 로그에서 패턴 감지 후 진단 트리로 분기. 사용자 확인을 받은 뒤에만
옵션을 바꾸고 같은 PUT을 다시 보낸다.

### Flow C. 실행 실패 (CrashLoopBackOff, 컨테이너 즉사)

1. `GET .../deployment/{name}/stat` — 상태 확인
2. `GET .../stage/{stage}/events?deployment={name}` — k8s events
3. `wss .../project/logs` — 컨테이너 stdout/stderr
4. 패턴 분석 (다음 섹션)

### Flow D. 멀티 서비스 (frontend + backend + db)

각 deployment를 별도 PUT으로 띄운다. 같은 stage 내라면:

- 내부 통신: deployment name이 hostname (예: backend가 `postgres-db:5432`로 접속)
- 시크릿 공유: stage-level 시크릿 store에 한 번 저장 → 각 deployment의 env에서 `{"name":"DB_PASSWORD","secret":"db-pwd-key"}` 형태로 참조
- 프론트엔드 ↔ 백엔드 통신: 코드 형태에 따라 Rewrites 적용 가능 여부 다름 (진단 트리 참조)

### Flow E. 시크릿으로 민감 env 관리

사용자가 비밀번호/토큰 등을 평문으로 박으려 하면:
1. 자동 분류: 키 이름에 `PASSWORD`/`SECRET`/`TOKEN`/`KEY`/`PWD` 포함 시 시크릿 권유
2. 사용자 동의 → `PUT .../stage/{stage}/secret` body `{secrets: {...}, merge: true}`
3. deployment env는 `{"name":"X","secret":"X"}` 형태로 참조

### Flow F. Container preset (단순 외부 이미지)

권장 사용 케이스는 아니지만, 외부 이미지를 그대로 띄워야 하는 경우에 사용한다.

```jsonc
{
  "name": "<name>",
  "app": "container",
  "options": {"image": "<docker-image:tag>", "ports": "<port>"},
  "context": {"preset": "container"}
}
```

---

## 🔬 Diagnose Patterns

빌드 또는 실행 로그에서 다음 패턴을 매칭하여 진단. **자동 fix 안 함** — 항상 사용자 결정 받음.

### 빌드 단계 (build logs)

#### `package.json not found` / `COPY ... not found`
- **원인**: 빌드 컨텍스트의 루트에 파일이 없음 (보통 monorepo)
- **해결 (설정만)**: `context.git.path` 추가
  - 예: `/backend` 디렉토리에 있다면 `path: "/backend"`
  - KB 참조: 서브 디렉토리 배포 (`developers/subdir`)
- **코드 수정 필요한 경우**: 없음

#### `Module not found` (빌드 시)
- **원인 A**: `dependencies`에 빠진 모듈
- **원인 B**: Node 버전 불일치 (특정 모듈이 새 ESM/import 문법 사용)
- **해결 (설정만)**: 원인 B면 `options.nodeversion` 또는 dockerfile preset으로 전환 시도
- **코드 수정 필요**: 원인 A → "package.json의 dependencies에 X 추가 후 push 필요"
- **비슷한 패턴**: Python/Java 등도 런타임 버전이나 preset 설정이 맞지 않으면 동일하게 배포 설정을 먼저 조정한다.

#### `npm ERR! 401 Unauthorized` (private 패키지)
- **원인**: private npm registry 인증
- **해결 (설정만)**: `options.npmrc`에 .npmrc 내용 주입 (auth token)
- **코드 수정 필요**: 없음 (단 .npmrc 토큰은 시크릿화 권장)

#### 빌드 명령이 다른 경우 (예: `pnpm` 쓰는 프로젝트가 yarn으로 빌드됨)
- **해결 (설정만)**: `options.install`, `options.build`, `options.start` 명시
- 예: `install: "pnpm install"`, `build: "pnpm build"`, `start: "pnpm start"`

#### vite/webpack build 결과가 안 보임 (HTML이 src 그대로)
- **원인**: web preset의 `docbase`가 기본값(`/`)
- **해결 (설정만)**: `options.docbase: "/dist"` (또는 `/build`)
- **코드 수정 필요**: 없음

### 실행 단계 (runtime logs / k8s events)

#### `EADDRINUSE` / `listen EACCES`
- **원인**: 포트 충돌 또는 권한
- **해결 (설정만)**: `options.ports` 조정 (코드가 listen하는 포트와 일치)
- 또는 코드가 `process.env.PORT`를 따르도록 (코드 측이지만 표준 컨벤션)

#### 컨테이너 즉사 (CrashLoopBackOff)
- 로그를 더 자세히 봐야 분류:
  - `Error: Cannot find module 'xxx'` → 런타임 의존성 누락 (코드 측)
  - `Error: connect ECONNREFUSED 127.0.0.1:5432` → DB 호스트가 localhost (코드 측)
  - `MissingEnvironmentError: DATABASE_URL` → env 누락 (설정으로 해결: env 추가)

#### `localhost` / `127.0.0.1` / 하드코드 IP
- **원인**: 코드에 로컬 주소 박혀있음
- **설정으로 해결 불가**: 코드 수정 필요
- 안내: "코드 X 줄에 `localhost` 박혀있어요. 다음 중 하나로 바꾸셔야 해요:
  1) 환경변수로 분리 (`process.env.DB_HOST`)
  2) 같은 stage 내 서비스명으로 (예: `postgres-db`)"

#### CORS 에러 (브라우저 콘솔)
- **분기** (코드 형태 따라):
  - `fetch('/api/...')` (상대경로) → ✅ Rewrites 추가로 해결 가능
  - `fetch(API_BASE + '/api/...')` (env 분기) → ✅ Rewrites + env 비우기 또는 env에 백엔드 URL 박기
  - `fetch('https://hardcoded/api/...')` (하드코드) → ❌ 코드 수정 필요
- **백엔드 쪽 CORS 헤더 누락이면** → 코드 수정 필요 (cors 미들웨어 추가 등)

#### `permission denied` / 파일 시스템 권한
- **원인**: non-root 사용자로 실행되는데 권한 필요
- **해결 (설정만)**: dockerfile preset의 `uid`/`gid` 옵션 조정
- 또는 코드가 root 권한 가정하지 않도록 (코드 측)

#### 헬스체크 실패 (`/healthz` 응답 없음 / status 503)
- **원인**: cloudtype의 readiness probe가 root 경로에 GET 요청
- **해결 (설정만)**: `options.healthz` 명시 (앱의 헬스체크 경로)
- 또는 `options.initialDelaySeconds` 늘리기 (앱이 부팅에 오래 걸리는 경우)

#### OOM (`out of memory`, `OOMKilled`, exit code 137)
- **자동 조정 안 함**. 사용자에게 보고:
  - "OOM 감지. 현재 메모리 X GB. 잔여 풀 Y GB. 늘릴까요? 아니면 메모리 누수 의심해서 코드 점검?"

#### DB 연결 실패 (`ECONNREFUSED ...:5432`, `authentication failed`)
- **원인 A**: hostname 잘못됨 (같은 stage 내라면 deployment name이 hostname)
- **원인 B**: 시크릿 누락 또는 잘못 참조
- **해결 (설정만)**: env의 `PGHOST`, `DATABASE_URL` 등 조정 + 시크릿 확인
- **코드 수정 필요**: DB 접속 설정이 하드코드된 경우

---

## 🧭 행동 가이드 (Agent Behavior)

### 사용자와 대화할 때

- **명확한 정보 요구**: 모호한 요청("배포해줘")은 정확한 repo URL/branch/프로젝트/stage를 묻기
- **추측 금지**: 설정값이나 동작을 추측으로 단정하지 말기. 근거(KB/SPEC/직접 테스트) 없으면 "이건 확신 못 해요"
- **정직한 보고**: 실패했으면 실패했다고. "거의 됐어요"는 금물
- **언어**: 사용자가 한국어로 요청하면 한국어로 응답

### 옵션 변경 시

1. **변경 사유** 명시 ("이 에러는 X 때문이라서")
2. **변경 내용** 명시 ("`options.docbase`를 `/dist`로 추가할게요")
3. **사용자 확인** ("진행할까요?")
4. 확인 후 같은 PUT 재호출

### 코드 측 문제일 때

1. **정확한 위치** 안내 (파일명/줄번호까지 알 수 있으면)
2. **권장 수정** 안내
3. **수정 자체는 안 함** ("이건 코드 영역이라 제 스킬 범위 밖이에요. 수정 후 다시 push해주세요")

### 정지·재시작 같은 액션

- 사용자가 명시적으로 요청한 경우에만

### 삭제

- 삭제는 스킬의 자동 액션으로 수행하지 않는다.
- 삭제가 필요하면 Cloudtype UI에서 직접 하도록 안내한다.

---

## 🔗 API & Scripts Reference

전체 API 명세: **`API_SPEC.md`**

핵심 endpoint 요약:

| 동작 | Method + Path |
|---|---|
| 인증 확인 | `GET /auth` |
| 스페이스 조회 | `GET /scope/{scope}` |
| 리소스 잔여량 | `GET /scope/{scope}/resource/available` |
| 프로젝트 조회 | `GET /project/{scope}/{project}` |
| 배포 목록 | `GET /project/{scope}/{project}/stage/{stage}/deployment` |
| 배포 상세 | `GET .../deployment/{name}` |
| 실시간 상태 | `GET .../deployment/{name}/stat` |
| 빌드 세션 | `GET .../deployment/{name}/session/latest` |
| K8s events | `GET .../stage/{stage}/events?deployment={name}` |
| **배포 생성/업데이트/재배포** | `PUT .../stage/{stage}/deployment` (동일 PUT) |
| 정지 | `PUT .../deployment/{name}/stop` |
| 시작 | `PUT .../deployment/{name}/start` |
| 삭제 | UI에서 직접 (스킬 자동 액션 금지) |
| 시크릿 저장 | `PUT .../stage/{stage}/secret` (body: `{secrets:{}, merge:true}`) |
| 시크릿 조회 | UI에서 직접 (스킬은 조회하지 않음) |
| 빌드 로그 (WS) | `wss://api.cloudtype.dev/project/build/logs` |
| 실행 로그 (WS) | `wss://api.cloudtype.dev/project/logs` |
| 터미널 (WS) | `wss://api.cloudtype.dev/project/attach` |

### Authentication

```
Authorization: Bearer <CLOUDTYPE_API_KEY>
```

API 키는 JWT. 발급은 사용자가 콘솔에서 직접 (스킬은 발급 안 함).

### Python helper scripts (예정, `scripts/` 폴더)

```
scripts/
├── verify.sh                    # 환경 검증 (기존)
├── cloudtype_client.py          # HTTP auth + base API (TODO)
├── cloudtype_actions.py         # project create / deploy / redeploy / start / stop (TODO, 삭제 제외)
└── cloudtype_logs.py            # WS 로그 스트리밍 (TODO)
```

### Preset → app 매핑 참조표

| Preset 종류 | `app` 값 패턴 | 예시 |
|---|---|---|
| Framework (node/python/...) | `<runtime>@<version>` | `node@20`, `python@3.11` |
| Web (build artifact 서빙) | `web` | html, vue, react 등 모든 web preset |
| Dockerfile | `dockerfile` | 코드 + Dockerfile 빌드 |
| Container | `container` | 외부 이미지 직접 실행 |
| DB | `<engine>@<version>` | `postgresql@16`, `mariadb@10`, `redis@7` |

→ preset 메타의 `config[0].app` 값을 참조해서 결정.

---

## 📚 More

- **API 전체 명세**: `API_SPEC.md`
- **상태 머신**: `reference/state-machine.md`
- **Knowledge Base** (cloudtype 공식 docs 통합): 워크스페이스 루트의 `cloudtype-kb.md`
  - 일반 사용법/정책 참고용. **검증된 API 동작이 우선**이며, KB와 충돌 시 `API_SPEC.md`/실측 결과를 따른다.
- **진단 보조**: `reference/diagnose-patterns.md` — 알려진 빌드/실행 오류 패턴 정리(망라적 목록 아님, 살아있는 문서).

---

## 🧪 Verify

스킬이 정상 동작 가능한 상태인지 확인:

```bash
bash scripts/verify.sh
```

체크:
- `CLOUDTYPE_API_KEY` 환경변수 존재
- `/auth` 호출로 인증 동작 확인
- 사용자의 스페이스 정보 (uid, scope, role) 조회 가능
