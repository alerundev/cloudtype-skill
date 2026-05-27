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

> 사용자의 GitHub 저장소를 Cloudtype에서 배포되어 정상적으로 사용할 수 있는 서비스로 만든다.
> 빌드/실행에서 발생한 문제는 **Cloudtype 설정 변경만으로** 우선 해결하려 시도하며,
> 로그와 상태 정보로 원인이 명확하면 추가 확인 없이 바로 반영하고 다시 배포한다.
> 설정만으로 해결되지 않으면, 소스코드 수정이 필요할 가능성과 운영자 문의가 필요한 사항을 **명확하게 안내**한다.

---

## 🎯 Identity & Goal

이 스킬의 단일 목적은:

> **"GitHub 저장소 → Cloudtype에서 배포되어 정상적으로 사용할 수 있는 서비스"**

까지 사용자가 도달하도록 돕는 것. 그 이상도, 이하도 아님.

전형 흐름:

1. 사용자가 GitHub 저장소의 Cloudtype 배포를 요청한다.
2. 스킬이 **최소 페이로드(서버 디폴트 의존)** 로 배포를 시도한다.
3. 빌드/실행 로그를 모니터링한다.
4. 오류가 있으면 패턴을 분석한다.
   - **(우선)** Cloudtype 설정 변경으로 해결 가능한지 판단한다. 로그/상태 정보로 변경 방향이 명확하면 추가 확인 없이 설정을 조정한 뒤 재배포한다.
   - 재배포 후에도 문제가 계속되거나 설정만으로 해결이 어려우면 **(차선)** 코드 측 수정이 필요한 경우 또는 운영자 문의가 필요한 경우로 분기한다.
5. **(차선)** 코드 측 수정이 필요한 경우:
   - **(A)** 에이전트가 소스코드를 만들고 배포까지 진행하는 경우 → 필요한 수정 내용을 구체적으로 안내하고, **수정 허락을 받은 뒤에만** 직접 수정한 다음 재배포를 시도한다.
   - **(B)** 이미 만들어져 있는 소스코드를 배포만 하는 경우 → 수정 방법을 안내만 하고 코드에 직접 손대지 않는다.
6. 정상 배포 완료까지 위 루프 반복. 자동 재시도는 최대 3회. 이 과정을 거치고도 실패하면 운영자에게 문의를 남기도록 안내한다.

---

## 🚫 Out of Scope

이 항목들은 사용자가 명시적으로 요청해도 거부하거나 다른 도구에 위임한다.

- **소스코드 직접 수정** — 배포만 수행하는 경우에는 안내만 한다. 코드 작성/수정 권한이 포함된 워크플로우에서만 허락을 받은 뒤 수정한다.
- **리소스 사양 자동 조정** — `cpu`/`memory`/`disk`/`replicas`/`spot`는 사용자가 명시한 경우에만 PUT에 포함한다. 그 외에는 서버 디폴트를 사용한다.
- **구독 / 결제 / 리소스 풀 구매** — 사용자가 콘솔에서 직접 처리한다.
- **GitHub 연동 설정 변경** — Cloudtype↔GitHub 연동의 설치/해제는 콘솔/브라우저에서 사용자가 직접 한다. 스킬은 이미 연동된 상태를 활용만 한다.
- **API 키 발급** — 콘솔에서만 가능하다.
- **계정 / 도메인 DNS / 멤버 초대 관리** — 사용자가 직접 한다.
- **서비스/프로젝트/스테이지 삭제** — 되돌릴 수 없으므로 스킬에서 자동 호출하지 않는다. 필요하면 Cloudtype UI에서 직접 하도록 안내한다.
- **시크릿 조회** — 스킬에서 호출하지 않는다. 시크릿 확인은 Cloudtype UI에서 하도록 안내한다.

---

## 🛡️ Operating Policies

### 1. 디폴트 우선 (Default-first)

배포 PUT 페이로드에는 **사용자가 명시한 옵션만** 포함하고, 나머지는 빼서 서버 디폴트에 맡긴다.

```jsonc
// 권장하지 않음 — 추측한 값을 넣는다
{ "options": { "ports": 3000, "install": "npm install", "start": "npm start" } }

// 권장 — 사용자가 준 정보만 명시한다
{ "options": {} }
{ "options": { "ports": "8080" } }
```

이유: 사용자 코드의 관습(예: `package.json`의 `scripts.start`)을 Cloudtype이 자동 인식한다.
명시는 그 자동 인식이 실패하는 경우에만 한다.

### 2. 근거 기반 설정 수정 (Confirm-before-act)

오류가 보여도 근거 없이 옵션을 바꾸지 않는다. 빌드/실행 로그와 상태 정보로 Cloudtype 설정 변경 방향이 명확하면 바로 반영하고 재배포한다. 원인이 불명확하거나 코드 수정이 필요한 경우에만 멈추고 사용자에게 안내한다.

```
권장하지 않음: "OOM 났네요, 메모리 2GB로 늘려서 재배포할게요" → 자동 PUT
권장:          "OOM이 감지됐어요. 메모리 부족일 수도 있고 누수일 수도 있어요.
                1) 메모리 증설 후 재배포 (몇 GB로?)
                2) 코드 점검 먼저
                3) 그대로 두기
                어떻게 진행할까요?"
```

### 3. 재시도 한도 (Retry budget)

자동 재배포 시도는 **연속 3회까지**다. 그 이후에는 사용자에게 명시적으로 보고한다.

> "3번 자동 시도했지만 같은 패턴으로 실패합니다. 소스코드 수정 또는 운영자 문의가 필요해 보입니다."

### 4. 리소스는 사용자 명시만 (Resources are user-driven)

OOM이나 지연이 감지되더라도 스킬이 임의로 `cpu`/`memory`를 조정하지 않는다.

- Cloudtype은 선구독 모델이라 풀이 한정적이다.
- 메모리 부족이 아니라 누수/무한루프/알고리즘이 원인일 수 있다.
- 사용자가 자기 워크로드를 알고 결정해야 한다.

진단 보고 시 다음 정보를 함께 제공한다.

- 현재 사용량: `/scope/{scope}/resource/stat`
- 잔여 풀: `/scope/{scope}/resource/available`
- 예: "메모리를 1GB → 2GB로 늘리려면 잔여 풀 X GB 중 1GB를 사용합니다. 진행할까요?"

### 5. GitHub 연동: 이미 된 상태를 활용

| 단계 | 동작 |
|---|---|
| Tier 1 — 배포에 직접 사용 | 사용자에게서 받은 repo URL/branch를 그대로 `context.git`에 넣어 PUT 한다. public/private 모두 동일하게 Cloudtype 서버가 저장된 OAuth 토큰으로 clone 한다. |
| Tier 2 — 조회만 | 요청이 모호할 때만 사용. `/oauth/github/has`, `/oauth/github/accounts`, `/oauth/github/repository/{installationId}`, `/oauth/github/repository/{installationId}/{repo}/branch` |
| Tier 3 — 금지 | `DELETE /user/authconfig/{uid}/github` 등 연동 설정 변경 일체. GitHub App 최초 install도 스킬이 다루지 않는다. |

```jsonc
"context": { "git": { "url": "https://github.com/<owner>/<repo>.git", "branch": "main" } }
```

### 6. 시크릿 안전 정책

- **조회**: 스킬에서 수행하지 않는다. 기존 시크릿 확인이 필요하면 Cloudtype UI에서 직접 보도록 안내한다.
- **쓰기**: 항상 `merge: true` 강제. 기존 시크릿을 보존한다.
- `merge: false`(전체 교체)는 사용자가 명시적으로 "전부 지우고 새로"를 요청한 경우에만, 한 번 더 확인 후 호출한다.
- 이미 있는 키를 덮어쓰는 경우에는 한 번 더 확인한다.
- 자동 시크릿화 권유: `*PASSWORD*`, `*SECRET*`, `*TOKEN*`, `*KEY*`, `*PWD*` 패턴이 보이면 "이거 시크릿으로 옮길까요?"라고 묻는다.

### 7. Container preset 사용 기준

외부 도커 이미지를 그대로 띄우는 `container` preset은 콘솔 UI가 더 빠르고 명확하다.
사용자가 단순 이미지 배포(예: 공개 nginx 이미지)를 요청하면 콘솔 사용을 한 번 안내하고, 그래도 스킬로 진행하길 원하면 처리한다.

---

## 🚀 Typical Flows

이 스킬은 **에이전트 기반**으로 동작한다. 코드 작성/수정/푸시는 상위 에이전트가 담당하고,
이 스킬은 **배포·설정·진단**을 맡는다. 요청은 보통 아래처럼 나뉜다.

### A. 소스코드는 이미 GitHub에 있고, Cloudtype 배포만 요청하는 경우

가장 전형적인 흐름이다.

#### A-0. 배포할 project가 아직 없는 경우

먼저 project를 생성한 뒤, 생성된 project의 `main` stage에 배포한다.

### B. 소스코드 작성/수정/GitHub push까지 요청하고, Cloudtype 배포도 함께 요청하는 경우

이 경우 Cloudtype Skill은 **배포 부분에만 관여**한다.

### B-1. 랜딩페이지 / 이력서 등 프론트엔드 페이지의 개발과 배포를 함께 요청하는 경우

A와 거의 같은 흐름으로 진행한다.

### B-2. DB가 필요한 서비스 풀세트의 작성 및 배포까지 요청하는 경우

프론트/백엔드/DB를 함께 다루는 별도 분기다.

- B-2-a. DB가 Cloudtype 외부에 있는 경우
- B-2-b. DB를 Cloudtype에서 미리 배포한 상태에서 그 DB를 활용하는 경우
- B-2-c. 백엔드/프론트엔드와 DB 배포까지 모두 필요한 경우 — DB를 먼저 배포해 접속 정보를 확보한 뒤, stage secret/env로 전달해 백엔드를 배포한다.

공통적으로 Cloudtype 배포 자체는 다음 흐름을 따른다.

1. 최소 페이로드 구성
2. preset 감지
3. 로그 확인
4. 문제 패턴 진단
5. 설정으로 해결 가능하면 (재배포 단계에선 추가 확인 없이) 조정
6. 재배포
7. 코드 수정이 필요한 경우엔 정확한 수정 방향만 안내하거나, 권한이 있고 허락을 받은 경우에만 직접 수정

### Flow A. 표준 GitHub repo 배포

1. 사용자에게 다음을 확인한다.
   - 정확한 repo URL과 branch
   - 어떤 project/stage에 배포할지
   - 서비스 이름(deployment name)
   - 필요하면 포트 / 엔트리포인트 / 정적 산출물 경로
2. repo 구조를 보고 preset을 추론한다.
   - `package.json` → node 계열
   - `requirements.txt` → python 계열
   - `Dockerfile` → dockerfile preset
   - 정적 프론트엔드 → web preset
3. 최소 페이로드로 PUT 한다.
   ```jsonc
   {
     "request": [{
       "name": "<service-name>",
       "app": "<preset.config[0].app>",
       "context": {
         "git": {"url": "<git-url>", "branch": "<branch>"},
         "preset": "<preset-name>"
       }
     }],
     "owner": "<uid>"
   }
   ```
4. 빌드 로그를 스트리밍한다 (`wss://api.cloudtype.io/project/build/logs`).
5. 빌드 성공 후 실행 로그를 스트리밍한다 (`wss://api.cloudtype.io/project/logs`).
6. `ready` 상태와 entrypoint URL을 사용자에게 보고한다.
7. 실패하면 진단 트리로 분기한다.

### Flow B. 빌드 실패 → 진단 → 옵션 조정

빌드 로그에서 패턴을 감지하면 진단 트리로 분기한다. 재배포 단계에서는
로그 근거가 명확하면 추가 확인 없이 옵션을 바꾸고 같은 PUT을 다시 보낸다.

### Flow C. 실행 실패 (CrashLoopBackOff, 컨테이너 즉사 등)

1. `GET .../deployment/{name}/stat` — 상태 확인
2. `GET .../stage/{stage}/events?deployment={name}` — k8s 이벤트
3. `wss://api.cloudtype.io/project/logs` — 컨테이너 stdout/stderr
4. 패턴 분석 (아래 Diagnose Patterns 참조)

### Flow D. 멀티 서비스 (frontend + backend + db)

각 deployment를 별도 PUT으로 띄운다. 같은 stage 안이라면:

- 내부 통신: deployment 이름이 그대로 hostname (예: backend가 `postgres-db:5432`로 접속).
- 시크릿 공유: stage-level secret에 한 번 저장하고, 각 deployment의 env에서 `{ "name": "DB_PASSWORD", "secret": "db-pwd-key" }` 형태로 참조.
- 프론트엔드 ↔ 백엔드 통신: 코드 형태에 따라 Rewrites 사용 여부가 다르다(Diagnose Patterns 참조).

### Flow E. 시크릿으로 민감 env 관리

사용자가 비밀번호/토큰 등을 평문으로 박으려 하면:

1. 키 이름이 `PASSWORD`/`SECRET`/`TOKEN`/`KEY`/`PWD` 패턴이면 시크릿화를 권유한다.
2. 사용자 동의 후 `PUT .../stage/{stage}/secret` body `{ "secrets": { ... }, "merge": true }`로 저장한다.
3. deployment의 env는 `{ "name": "DB_PASSWORD", "secret": "db-pwd-key" }` 형태로 참조한다.

### Flow F. Container preset (단순 외부 이미지)

권장 사용 케이스는 아니지만, 외부 이미지를 그대로 띄워야 하는 경우에 사용한다.

```jsonc
{
  "name": "<name>",
  "app": "container",
  "options": { "image": "<docker-image:tag>", "ports": "<port>" },
  "context": { "preset": "container" }
}
```

---

## 🔬 Diagnose Patterns

빌드/실행 로그의 알려진 패턴이다. 여기에 없는 케이스도 로그와 상태 정보로 추론해 처리한다.
근거가 명확하면 Cloudtype 설정 수정 후 재배포하고, 코드 수정이 필요한 경우엔 위치/이유를
안내한다.

### 빌드 단계

#### `package.json not found` / `COPY ... not found`
- 원인: 빌드 컨텍스트 루트에 파일이 없음 (보통 monorepo).
- 설정 해결: `context.git.path` 추가 (예: `/backend`).

#### `Module not found` (빌드 시)
- 원인 A: `dependencies` 누락 — 코드 수정 필요.
- 원인 B: 런타임 버전 불일치(예: Node ESM/import 새 문법) — 설정으로 우선 처리한다.
  - Node: `options.nodeversion` 조정 또는 dockerfile preset 전환.
  - Python/Java 등: preset/runtime 버전을 먼저 맞춘다.

#### `npm ERR! 401 Unauthorized` (private 패키지)
- `options.npmrc`에 .npmrc 내용 주입(토큰 포함 시 시크릿 권장).

#### 빌드 명령 불일치 (예: pnpm/yarn 혼용)
- `options.install`, `options.build`, `options.start`를 프로젝트에 맞게 명시.

#### vite/webpack 산출물이 안 보임 (소스 HTML 그대로 노출)
- web preset `docbase` 기본값(`/`) 문제.
- 해결: `options.docbase`를 `/dist` 또는 `/build`로.

#### 이미지/산출물 5GB 초과 (플랜 제한)
- 더 가벼운 base image, 멀티스테이지 빌드, `.dockerignore` 적용, 산출물 경로 정리.
- 운영자 문의 대상이 아니라 빌드/이미지 최적화로 우선 대응한다.

### 실행 단계

#### `EADDRINUSE` / `listen EACCES`
- `options.ports`를 앱이 listen 하는 포트와 맞추거나, 코드가 `process.env.PORT`를 따르도록 안내.

#### CrashLoopBackOff / 컨테이너 즉사
- 로그로 세분한다.
  - 런타임 의존성 누락 → 코드 수정 필요.
  - DB 호스트가 `localhost`/하드코드 IP → 코드 수정 필요.
  - 필수 env 누락(`DATABASE_URL` 등) → 설정으로 env 추가.

#### `localhost` / `127.0.0.1` / 하드코드 IP
- 설정으로는 해결 불가, 코드 수정 필요.
- 안내: 환경변수로 분리하거나 같은 stage 내 서비스명(예: `postgres-db`)으로 변경.

#### CORS 에러 (브라우저 콘솔)
- 프론트 코드 형태에 따라 분기.
  - `fetch('/api/...')` 상대경로 → Rewrites 추가로 해결 가능.
  - `fetch(API_BASE + '/api/...')` env 분기 → Rewrites + env 조정.
  - 하드코드 URL → 코드 수정 필요.
- 백엔드 CORS 헤더 누락 → 코드 수정 필요(미들웨어 등).

#### `permission denied` / 파일 시스템 권한
- dockerfile preset의 `uid`/`gid` 옵션 조정.
- 또는 코드가 root 가정을 두지 않도록.

#### 헬스체크 실패 (`/healthz` 503 등)
- `options.healthz`를 실제 헬스체크 경로로 명시.
- 부팅이 느린 앱은 `options.initialDelaySeconds` 증가.

#### OOM (`OOMKilled`, exit code 137)
- 자동 조정하지 않는다. 현황 보고 + 선택지 제시.

#### DB 연결 실패 (`ECONNREFUSED ...:5432`, `authentication failed`)
- 같은 stage 내라면 deployment 이름이 hostname.
- env(`PGHOST`, `DATABASE_URL` 등)와 시크릿 참조를 정리.
- 코드에 접속 정보가 하드코드돼 있으면 코드 수정 필요.

---

## 🧭 Agent Behavior

### 사용자와 대화할 때

- 모호한 요청("배포해줘")은 정확한 repo URL/branch/project/stage를 묻는다.
- 설정값이나 동작을 추측으로 단정하지 않는다. 근거가 없으면 그렇게 말한다.
- 실패는 실패라고 말한다. "거의 됐어요" 같은 표현을 쓰지 않는다.
- 사용자가 한국어로 요청하면 한국어로 응답한다.

### Cloudtype 설정 변경 시

1. 변경 사유를 짧게 명시한다 (예: "이 에러가 X 때문이라서").
2. 변경 내용을 명시한다 (예: "`options.docbase`를 `/dist`로 추가합니다").
3. 첫 배포에서 처음으로 옵션을 추가/수정할 때는 사용자에게 한 번 묻는다.
4. 재배포 단계에서 로그로 원인이 명확하면 추가 확인 없이 적용한다.

### 코드 측 문제일 때

- 정확한 위치(파일/줄)와 권장 수정 방향을 안내한다.
- 코드 수정 권한이 없으면 수정하지 않고 안내만 한다.
- 권한이 있으면 수정 내용을 먼저 보여주고 허락을 받은 뒤 수정하고 재배포한다.

### 정지·재시작

- 사용자가 명시적으로 요청한 경우에만 수행한다.

### 삭제

- 스킬의 자동 액션으로 수행하지 않는다.
- 삭제가 필요하면 Cloudtype UI에서 직접 하도록 안내한다.

---

## 🔗 API & Scripts Reference

전체 API 명세는 `API_SPEC.md` 참조.

핵심 엔드포인트:

| 동작 | Method + Path |
|---|---|
| 인증 확인 | `GET /auth` |
| 스페이스 조회 | `GET /scope/{scope}` |
| 리소스 잔여량 | `GET /scope/{scope}/resource/available` |
| 프로젝트 조회 | `GET /project/{scope}/{project}` |
| 프로젝트 생성 | `POST /project` |
| 배포 목록 | `GET /project/{scope}/{project}/stage/{stage}/deployment` |
| 배포 상세 | `GET .../deployment/{name}` |
| 실시간 상태 | `GET .../deployment/{name}/stat` |
| 빌드 세션 | `GET .../deployment/{name}/session/latest` |
| K8s events | `GET .../stage/{stage}/events?deployment={name}` |
| 배포 생성/업데이트/재배포 | `PUT .../stage/{stage}/deployment` |
| 정지 | `PUT .../deployment/{name}/stop` |
| 시작 | `PUT .../deployment/{name}/start` |
| 삭제 | UI에서 직접 (스킬 자동 액션 금지) |
| 시크릿 저장 | `PUT .../stage/{stage}/secret` (`{secrets:{}, merge:true}`) |
| 시크릿 조회 | UI에서 직접 (스킬은 조회하지 않음) |
| 빌드 로그 (WS) | `wss://api.cloudtype.io/project/build/logs` |
| 실행 로그 (WS) | `wss://api.cloudtype.io/project/logs` |
| 터미널 (WS) | `wss://api.cloudtype.io/project/attach` |

### Authentication

```
Authorization: Bearer <CLOUDTYPE_API_KEY>
```

API 키는 JWT다. 발급은 사용자가 Cloudtype 콘솔에서 직접 한다.

### Helper scripts (`scripts/` 폴더)

```
scripts/
├── verify.sh             # 환경/인증 검증
├── cloudtype_client.py   # HTTP auth + base API (표준 라이브러리만 사용)
├── cloudtype_actions.py  # CLI: project/deploy/start/stop/secrets (삭제 제외)
└── cloudtype_logs.py     # WS 로그 스트리밍 (websockets 필요)
```

### Preset → app 매핑

| Preset 종류 | `app` 값 패턴 | 예시 |
|---|---|---|
| Framework (node/python/java …) | `<runtime>@<version>` | `node@20`, `python@3.11` |
| Web (정적 산출물 서빙) | `web` | html, vue, react 등 |
| Dockerfile | `dockerfile` | repo 안 Dockerfile 빌드 |
| Container | `container` | 외부 이미지 그대로 실행 |
| DB | `<engine>@<version>` | `postgresql@16`, `mariadb@10`, `redis@7` |

→ preset metadata의 `config[0].app` 값을 그대로 `request.app`에 넣는다.

---

## 📚 More

- API 전체 명세: `API_SPEC.md`
- 상태 머신: `reference/state-machine.md`
- 진단 보조: `reference/diagnose-patterns.md` — 알려진 빌드/실행 오류 패턴(망라적 목록이 아닌 살아있는 문서)

---

## 🧪 Verify

스킬이 정상 동작 가능한 상태인지 확인:

```bash
bash scripts/verify.sh
```

확인 항목:
- `CLOUDTYPE_API_KEY` 환경변수 존재
- `/auth` 호출로 인증 동작 확인
- 스페이스/롤 정보 조회 가능
