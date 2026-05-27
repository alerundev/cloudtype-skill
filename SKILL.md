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

사용자의 GitHub 저장소를 Cloudtype 에 배포하여 정상적으로 사용할 수 있는 서비스로 만들고,
빌드 또는 실행 단계에서 발생한 문제를 **Cloudtype 설정 변경만으로** 우선 해결하려 시도하는 스킬입니다.
빌드/실행 로그와 상태 정보로 설정 변경 방향이 명확한 경우에는 추가 확인 없이 바로 반영하고 재배포할 수 있습니다.
설정만으로 해결되지 않는 경우에는 소스코드 수정이 필요한 사항 또는 운영 채널 문의가 필요한 사항을 명확하게 안내합니다.

---

## 🎯 Identity & Goal

이 스킬의 단일 목적은 다음과 같습니다.

> **GitHub 저장소 → Cloudtype 에서 정상 동작하는 서비스로 배포**되는 지점까지 사용자가 도달하도록 돕는 것.

전형적인 흐름은 다음과 같습니다.

1. 사용자가 "~~~ 저장소를 Cloudtype 에 배포해 주세요" 와 같이 요청합니다.
2. 스킬은 **최소 페이로드(서버 디폴트에 의존)** 로 배포를 시도합니다.
3. 빌드/실행 로그를 모니터링합니다.
4. 오류가 있으면 패턴을 분석합니다.
   - **(우선)** Cloudtype 설정 변경으로 해결 가능한지 판단합니다. 로그와 상태 정보로 설정 변경 방향이 명확하면, 추가 확인 없이 설정을 조정한 뒤 재배포합니다.
   - 재배포 후에도 문제가 계속되거나 설정만으로 해결이 어려운 경우 **(차선)** 코드 측 수정이 필요한 경우 또는 운영 채널 문의가 필요한 경우로 분기합니다.
5. **(차선)** 코드 측 수정이 필요한 경우의 분기는 다음과 같습니다.
   - **(A)** 에이전트가 소스코드도 함께 작성/수정하는 워크플로 → 필요한 수정 내용을 구체적으로 안내하고, 사용자 승인을 받은 뒤에만 직접 수정한 후 재배포를 시도합니다.
   - **(B)** 이미 만들어진 소스코드를 배포만 하는 워크플로 → 수정 방향만 안내하고 코드에는 직접 손대지 않습니다.
6. 정상 배포가 완료될 때까지 위 루프를 반복합니다(단, 자동 재시도는 최대 3회). 이 과정을 거쳐도 실패하면 사용자에게 운영 채널로 문의하도록 안내합니다.

---

## 🚫 Out of Scope (수행하지 않는 작업)

다음 항목들은 사용자가 명시적으로 요청하더라도 스킬이 직접 수행하지 않으며, 사용자에게 위임합니다.

- **소스코드 직접 수정** — 배포만 수행하는 워크플로에서는 안내만 제공하고 코드에 직접 손대지 않습니다. 코드 작성/수정 권한이 포함된 워크플로에서는 사용자 확인 후 수정 및 재배포가 가능합니다.
- **리소스 사양 자동 조정** — `cpu`/`memory`/`disk`/`replicas`/`spot` 은 사용자가 명시한 경우에만 PUT 페이로드에 포함합니다. 그 외에는 서버 디폴트에 맡깁니다.
- **구독 / 결제 / 리소스 풀 구매** — Cloudtype 콘솔에서 사용자가 직접 처리합니다.
- **GitHub 연동 설정 변경** — Cloudtype ↔ GitHub 연동의 설치/해제는 콘솔/브라우저에서 사용자가 직접 진행합니다. 스킬은 **이미 연동된 상태를 활용**만 합니다.
- **API 키 발급** — Cloudtype 콘솔에서만 가능합니다.
- **계정 / 도메인 DNS / 멤버 초대 관리** — 사용자가 직접 수행합니다.

---

## 🛡️ Operating Policies

### 1. 디폴트 우선 (Default-first)

배포 PUT 페이로드는 **사용자가 명시한 옵션만 포함**하고, 나머지는 빼서 서버 디폴트에 맡깁니다.

```python
# 권장하지 않음 — 추측 값을 채워 넣는 경우
{"options": {"ports": 3000, "install": "npm install", "start": "npm start"}}

# 권장 — 최소만 명시
{"options": {}}                     # 명확한 값이 없으면 빈 객체
{"options": {"ports": "8080"}}      # 사용자가 명시한 항목만 포함
```

이유: Cloudtype 은 사용자 코드의 관습(예: `package.json` 의 `scripts.start`)을 자동으로 인식합니다.
옵션을 명시하는 것은 그 자동 인식이 실패하는 경우에 한정합니다.

### 2. 자동 fix 금지, 근거 기반 설정 수정 우선 (Confirm-before-act)

오류가 발견되어도 근거 없이 옵션을 변경하지 않습니다.
빌드/실행 로그와 상태 정보로 Cloudtype 설정 변경 방향이 명확한 경우에는 바로 반영하고 재배포합니다.
원인이 불명확하거나 코드 수정이 필요한 경우에는 진행을 멈추고 사용자에게 안내합니다.

```
권장하지 않음:
  "OOM 이 발생했습니다. 메모리를 2GB 로 늘려 재배포하겠습니다." → 자동 PUT

권장:
  "OOM 이 감지되었습니다. 메모리 부족일 수도 있고, 코드 측 메모리 누수일 수도 있습니다.
   다음 중 어떻게 진행할까요?
     1) 메모리를 늘려 재배포 (어느 크기로 진행하시겠습니까?)
     2) 코드 점검을 먼저
     3) 그대로 유지"
```

### 3. 재시도 한도 (Retry budget)

자동 재배포 시도는 **연속 3회까지**입니다. 그 이상으로 진행하지 않고 사용자에게 명시적으로 보고합니다.

> "동일한 패턴으로 3회 연속 실패했습니다. 소스코드 수정 또는 운영 채널 문의가 필요해 보입니다."

### 4. 리소스는 사용자 명시만 (Resources are user-driven)

OOM 또는 응답 지연 등이 감지되더라도 **자동으로 cpu/memory 를 조정하지 않습니다**. 이유는 다음과 같습니다.

- Cloudtype 은 선구독 모델이므로 사용 가능한 리소스 풀이 한정되어 있습니다.
- 실제 원인이 메모리 부족이 아닐 수 있습니다(누수 / 무한 루프 / 알고리즘 비효율 등).
- 워크로드 특성은 사용자가 가장 잘 파악하므로, 증설 여부는 사용자가 결정해야 합니다.

진단 보고 시에는 다음과 같은 정보를 함께 제공하면 사용자의 결정에 도움이 됩니다.

- 현재 할당량 (`/scope/{scope}/resource/stat` 의 `stats[deployment]`)
- 잔여 풀 (`/scope/{scope}/resource/available`)
- 예: "메모리를 1GB → 2GB 로 늘리려면 잔여 풀 X GB 중 1GB 를 사용합니다. 진행하시겠습니까?"

### 5. GitHub 연동: 이미 연결된 상태를 활용 (Tier 1 / 2 / 3)

**Tier 1 (배포에 직접 사용)** — 사용자가 repo URL 을 명시하면 그대로 PUT 합니다.
```jsonc
"context": { "git": { "url": "https://github.com/<owner>/<repo>.git", "branch": "main" } }
```
public / private 여부와 무관합니다. Cloudtype 서버가 저장된 OAuth 토큰으로 클론을 수행합니다.

**Tier 2 (조회 전용, 사용자 요청이 모호한 경우)** — read-only 엔드포인트만 사용합니다.
- `/oauth/github/has` — 연동 여부 확인
- `/oauth/github/accounts` — 연결된 GitHub 계정 조회
- `/oauth/github/repository/{installationId}` — repo 검색
- `/oauth/github/repository/{installationId}/{repo}/branch` — 브랜치 목록

**Tier 3 (수행하지 않음)**:
- `DELETE /user/authconfig/{uid}/github` (연동 해제)
- 연동 설정 변경 일체

### 6. 시크릿 안전 정책

- **조회**: 스킬에서는 수행하지 않습니다. 기존 시크릿 확인이 필요하면 Cloudtype UI 사용을 안내합니다.
- **쓰기**: 항상 `merge: true` 를 강제하여 기존 시크릿이 보존되도록 합니다.
- `merge: false`(전체 교체)는 사용자가 명시적으로 "기존 항목을 모두 삭제하고 새로 작성하겠다"고 요청한 경우에 한해, 한 번 더 확인한 뒤 진행합니다.
- 이미 존재하는 키를 덮어쓰는 경우에도 한 번 확인을 받습니다.
- 키 이름이 `*PASSWORD*`, `*SECRET*`, `*TOKEN*`, `*KEY*`, `*PWD*` 등 민감 패턴에 해당하는 경우, 자동으로 시크릿 이전을 제안합니다("해당 항목을 시크릿으로 옮길까요?").

### 7. Container preset 은 권장 사용 케이스가 아님

외부 Docker 이미지를 그대로 실행하는 `container` preset 은 Cloudtype 콘솔 UI 에서 진행하는 것이 더 빠르고 명확한 경우가 많습니다.
스킬은 API 호출을 지원하되, 사용자가 "nginx 를 그대로 띄워 주세요" 와 같은 단순 요청을 하면 다음과 같이 안내합니다.

> "단순 이미지 배포는 Cloudtype 콘솔에서 직접 진행하시는 편이 더 빠를 수 있습니다.
> 이대로 스킬에서 진행할까요?"

---

## 🚀 Typical Flows

이 스킬은 **에이전트 기반**으로 동작합니다. 코드 작성/수정/푸시는 상위 에이전트가 담당하고,
Cloudtype Skill 은 **배포·설정·진단**을 담당합니다.

요청은 일반적으로 다음과 같이 분류됩니다.

### A. 소스코드가 이미 GitHub 에 있고, Cloudtype 배포만 요청하는 경우

가장 전형적인 흐름입니다.

#### A-0. 배포 대상 project 가 아직 없는 경우

먼저 project 를 생성한 뒤, 생성된 project 의 main stage 에 배포합니다.

### B. 소스코드 작성/수정/GitHub push 까지 요청하고, Cloudtype 배포도 함께 요청하는 경우

이 경우 Cloudtype Skill 은 **배포 부분에만 관여**합니다.

### B-1. 랜딩 페이지 / 이력서 등 프론트엔드 페이지 개발과 배포를 함께 요청하는 경우

A 와 거의 동일한 흐름으로 진행합니다.

### B-2. DB 가 필요한 서비스 풀세트(프론트/백엔드/DB) 작성 및 배포까지 요청하는 경우

프론트/백엔드/DB 를 함께 다루는 분기입니다.

- B-2-a. DB 가 Cloudtype 외부에 있는 경우
- B-2-b. DB 를 Cloudtype 에 먼저 배포해 두고 그 DB 를 활용하는 경우
- B-2-c. 백엔드/프론트엔드 개발과 DB 배포가 모두 필요한 경우

어느 경우든 Cloudtype 배포 자체는 다음의 공통 흐름을 따릅니다.

1. 최소 페이로드 구성
2. preset 감지
3. 로그 확인
4. 문제 패턴 진단
5. 설정으로 해결 가능한 경우 사용자 확인 후 옵션 조정
6. 재배포
7. 코드 수정이 필요한 경우 정확한 수정 방향만 안내

### Flow A. 표준 GitHub repo 배포

**사용자 요청 예**: "`<owner>/<repo>` 를 Cloudtype 에 배포해 주세요."

1. 사용자에게 다음 항목을 명확히 확인합니다.
   - 정확한 repo URL 과 branch
   - 배포 대상 프로젝트 / 스테이지 (예: `test` 프로젝트의 `main` stage)
   - 서비스 이름 (deployment name)
   - 필요한 경우 포트 / 엔트리포인트 / 정적 산출물 경로
2. repo 구조를 보고 preset 을 추론합니다.
   - `package.json` → Node 계열
   - `requirements.txt` → Python 계열
   - `Dockerfile` → dockerfile preset
   - 정적 프론트엔드 → web preset
3. 최소 페이로드로 PUT 합니다.
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
5. 빌드 성공 시 실행 로그 스트리밍 (`wss .../project/logs`)
6. ready 상태와 entrypoint URL 을 사용자에게 보고
7. 실패 시 진단 트리로 분기

### Flow B. 빌드 실패 → 진단 → 옵션 조정

빌드 로그에서 패턴을 감지한 뒤 진단 트리로 분기합니다.
사용자 확인을 받은 뒤에만 옵션을 변경하고 동일 PUT 을 다시 호출합니다.

### Flow C. 실행 실패 (CrashLoopBackOff, 컨테이너 즉시 종료 등)

1. `GET .../deployment/{name}/stat` — 상태 확인
2. `GET .../stage/{stage}/events?deployment={name}` — K8s events 확인
3. `wss .../project/logs` — 컨테이너 stdout / stderr 수집
4. 패턴 분석 (다음 섹션 참조)

### Flow D. 멀티 서비스 (frontend + backend + DB)

각 deployment 를 별도의 PUT 으로 배포합니다. 같은 stage 내인 경우 다음이 적용됩니다.

- 내부 통신: deployment name 이 hostname 으로 동작합니다 (예: backend 에서 `postgres-db:5432` 로 접속).
- 시크릿 공유: stage 레벨 시크릿 store 에 한 번 저장한 뒤, 각 deployment 의 env 에서 `{"name": "DB_PASSWORD", "secret": "<key>"}` 형태로 참조합니다.
- 프론트엔드 ↔ 백엔드 통신: 코드 형태에 따라 Rewrites 적용 가능 여부가 달라집니다(진단 트리 참조).

### Flow E. 시크릿으로 민감 env 관리

사용자가 비밀번호/토큰 등을 평문으로 입력하려는 경우 다음 절차를 따릅니다.

1. 자동 분류: 키 이름이 `PASSWORD` / `SECRET` / `TOKEN` / `KEY` / `PWD` 등을 포함하는 경우 시크릿 이전을 제안합니다.
2. 사용자가 동의하면 `PUT .../stage/{stage}/secret` 으로 저장합니다(body: `{secrets: {...}, merge: true}`).
3. deployment 의 env 에서는 `{"name": "<ENV>", "secret": "<key>"}` 형태로 참조합니다.

### Flow F. Container preset (외부 이미지 직접 실행)

권장 사용 케이스는 아니지만, 외부 이미지를 그대로 실행해야 하는 경우 사용합니다.

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

빌드 또는 실행 로그에서 다음 패턴을 매칭하여 진단합니다. **자동 fix 는 수행하지 않으며**, 항상 사용자 결정을 받은 뒤 진행합니다.

### 빌드 단계 (build logs)

#### `package.json not found` / `COPY ... not found`
- 원인: 빌드 컨텍스트 루트에 파일이 없음 (일반적으로 monorepo 구조)
- 해결 (설정): `context.git.path` 추가 (예: `/backend` 디렉토리라면 `path: "/backend"`)
- 참고: 공식 문서의 "서브 디렉토리 배포" 항목
- 코드 수정 필요 여부: 없음

#### `Module not found` (빌드 시)
- 원인 A: `dependencies` 에 빠진 모듈
- 원인 B: 런타임 버전 불일치 (예: 특정 모듈이 최신 ESM / import 문법을 사용)
- 해결 (설정): 원인 B 의 경우 `options.nodeversion` 조정 또는 dockerfile preset 으로 전환을 시도합니다.
- 코드 수정 필요 여부: 원인 A 의 경우 `package.json` 의 `dependencies` 에 누락 모듈을 추가하고 push 가 필요합니다.
- 유사 패턴: Python / Java 등 다른 런타임도 버전 또는 preset 설정 불일치 시 동일하게 배포 설정을 먼저 조정합니다.

#### `npm ERR! 401 Unauthorized` (private 패키지)
- 원인: private npm registry 인증
- 해결 (설정): `options.npmrc` 에 .npmrc 내용을 주입 (auth token 포함)
- 코드 수정 필요 여부: 없음 (단, .npmrc 토큰은 시크릿화 권장)

#### 빌드 명령 불일치 (예: pnpm 프로젝트가 yarn 으로 빌드되는 경우)
- 해결 (설정): `options.install`, `options.build`, `options.start` 를 프로젝트에 맞게 명시
- 예: `install: "pnpm install"`, `build: "pnpm build"`, `start: "pnpm start"`

#### Vite / Webpack 빌드 결과가 노출되지 않음 (소스 HTML 그대로 보임)
- 원인: web preset 의 `docbase` 가 기본값(`/`) 으로 설정됨
- 해결 (설정): `options.docbase` 를 `/dist` 또는 `/build` 로 지정
- 코드 수정 필요 여부: 없음

### 실행 단계 (runtime logs / k8s events)

#### `EADDRINUSE` / `listen EACCES`
- 원인: 포트 충돌 또는 권한 문제
- 해결 (설정): `options.ports` 를 앱이 실제 listen 하는 포트와 일치시킵니다.
- 코드가 `process.env.PORT` 를 따르도록 하는 방향(코드 측 표준 컨벤션)도 권장 가능합니다.

#### 컨테이너 즉시 종료 (CrashLoopBackOff)
- 로그를 자세히 살펴 원인을 분류합니다.
  - `Error: Cannot find module 'xxx'` → 런타임 의존성 누락 (코드 측)
  - `Error: connect ECONNREFUSED 127.0.0.1:5432` → DB 호스트가 localhost 로 하드코딩됨 (코드 측)
  - `MissingEnvironmentError: DATABASE_URL` → 환경변수 누락 (설정으로 해결 가능: env 추가)

#### `localhost` / `127.0.0.1` / 하드코딩된 IP
- 원인: 코드에 로컬 주소가 하드코딩되어 있음
- 설정만으로 해결이 어려우며 코드 수정이 필요합니다.
- 안내 예시: "해당 코드 위치에 `localhost` 가 하드코딩되어 있습니다. 다음 중 하나로 변경해 주시기 바랍니다.
  1) 환경변수로 분리 (`process.env.DB_HOST`)
  2) 같은 stage 내 서비스명으로 변경 (예: `postgres-db`)"

#### CORS 에러 (브라우저 콘솔)
- 코드 형태에 따라 분기합니다.
  - `fetch('/api/...')` (상대 경로) → Rewrites 추가로 해결 가능
  - `fetch(API_BASE + '/api/...')` (env 분기) → Rewrites 추가와 함께 env 를 비우거나 백엔드 URL 을 env 로 설정
  - `fetch('https://hardcoded/api/...')` (하드코딩) → 코드 수정 필요
- 백엔드의 CORS 헤더 누락이 원인인 경우 코드 수정이 필요합니다 (CORS 미들웨어 추가 등).

#### `permission denied` / 파일 시스템 권한
- 원인: non-root 사용자로 실행되는 환경에서 권한이 필요한 동작 수행
- 해결 (설정): dockerfile preset 의 `uid` / `gid` 옵션 조정
- 코드가 root 권한을 가정하지 않도록 변경하는 방향(코드 측)도 안내할 수 있습니다.

#### 헬스체크 실패 (응답 없음 또는 status 503 등)
- 원인: readiness probe 가 root 경로에 GET 요청을 수행하는데 앱에 해당 경로가 없는 경우 등
- 해결 (설정): `options.healthz` 에 앱의 실제 헬스체크 경로를 명시
- 부팅이 느린 앱은 `options.initialDelaySeconds` 를 늘립니다.

#### OOM (`OOMKilled`, exit code 137)
- 자동 조정은 수행하지 않습니다. 사용자에게 다음과 같이 보고합니다.
  - "OOM 이 감지되었습니다. 현재 메모리 X GB, 잔여 풀 Y GB 입니다. 메모리를 증설할까요? 아니면 코드 측 누수 점검을 먼저 진행할까요?"

#### DB 연결 실패 (`ECONNREFUSED ...:5432`, `authentication failed` 등)
- 원인 A: hostname 오류 (같은 stage 내에서는 deployment name 이 hostname)
- 원인 B: 시크릿 누락 또는 잘못된 참조
- 해결 (설정): env 의 `PGHOST`, `DATABASE_URL` 등을 조정하고 시크릿 참조를 확인합니다.
- 코드 수정 필요 여부: DB 접속 설정이 코드에 하드코딩된 경우

---

## 🧭 행동 가이드 (Agent Behavior)

### 사용자와 대화할 때

- **명확한 정보 요청**: 모호한 요청("배포해 주세요")에는 정확한 repo URL / branch / 프로젝트 / stage 를 추가로 확인합니다.
- **추측 금지**: 설정값이나 동작을 근거 없이 단정하지 않습니다. 근거(공식 문서 / API 명세 / 직접 테스트)가 없는 경우 "확실하지 않습니다" 라고 안내합니다.
- **정직한 보고**: 실패한 경우 실패 사실을 그대로 전달합니다. "거의 성공" 과 같은 표현은 사용하지 않습니다.
- **언어**: 사용자가 한국어로 요청하면 한국어로 응답합니다.

### 옵션 변경 시

1. **변경 사유**를 명시합니다 ("이 에러는 X 가 원인으로 보입니다").
2. **변경 내용**을 명시합니다 ("`options.docbase` 를 `/dist` 로 추가하겠습니다").
3. **사용자 확인**을 받습니다 ("진행할까요?").
4. 확인 후 동일 PUT 을 재호출합니다.

### 코드 측 문제일 때

1. **정확한 위치**를 안내합니다 (가능한 경우 파일명 / 라인 번호까지).
2. **권장 수정 방향**을 안내합니다.
3. **수정 자체는 수행하지 않습니다** ("해당 부분은 코드 영역으로 스킬 범위를 벗어납니다. 수정 후 다시 push 해 주시기 바랍니다").

### 정지·재시작과 같은 액션

- 사용자가 명시적으로 요청한 경우에만 수행합니다.

### 삭제

- 삭제는 스킬의 자동 액션으로 수행하지 않습니다.
- 삭제가 필요하면 Cloudtype UI 에서 직접 수행하도록 안내합니다.

---

## 🔗 API & Scripts Reference

전체 API 명세는 **`API_SPEC.md`** 를 참조합니다.

핵심 엔드포인트 요약:

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
| 삭제 | UI 에서 직접 (스킬 자동 액션 금지) |
| 시크릿 저장 | `PUT .../stage/{stage}/secret` (body: `{secrets:{}, merge:true}`) |
| 시크릿 조회 | UI 에서 직접 (스킬은 조회하지 않음) |
| 빌드 로그 (WS) | `wss://api.cloudtype.io/project/build/logs` |
| 실행 로그 (WS) | `wss://api.cloudtype.io/project/logs` |
| 터미널 (WS) | `wss://api.cloudtype.io/project/attach` |

### Authentication

```
Authorization: Bearer <CLOUDTYPE_API_KEY>
```

API 키는 JWT 형식이며, 발급은 사용자가 Cloudtype 콘솔에서 직접 수행합니다. 스킬은 발급을 수행하지 않습니다.

### Python helper scripts (`scripts/` 폴더)

```
scripts/
├── verify.sh                # 환경/인증 검증
├── cloudtype_client.py      # HTTP 래퍼 (stdlib only)
├── cloudtype_actions.py     # project / deploy / redeploy / start / stop 등 CLI
└── cloudtype_logs.py        # WebSocket 로그 스트리밍 CLI
```

### Preset → app 매핑 참조표

| Preset 종류 | `app` 값 패턴 | 예시 |
|---|---|---|
| Framework (node / python 등) | `<runtime>@<version>` | `node@20`, `python@3.11` |
| Web (빌드 산출물 서빙) | `web` | html, vue, react 등 모든 web preset |
| Dockerfile | `dockerfile` | 코드 + Dockerfile 빌드 |
| Container | `container` | 외부 이미지 직접 실행 |
| DB | `<engine>@<version>` | `postgresql@16`, `mariadb@10`, `redis@7` |

→ preset 메타의 `config[0].app` 값을 참조하여 결정합니다.

---

## 📚 More

- **API 전체 명세**: `API_SPEC.md`
- **상태 머신**: `reference/state-machine.md`
- **진단 보조**: `reference/diagnose-patterns.md` — 알려진 빌드/실행 오류 패턴 정리 (망라적 목록이 아니며, 발견된 패턴을 누적해 두는 문서입니다)
- **공식 문서**: https://docs.cloudtype.io — 일반 사용법 및 정책 참고용. API 동작과 충돌이 있는 경우 `API_SPEC.md` 의 실측 결과를 우선합니다.

---

## 🧪 Verify

스킬이 정상 동작 가능한 상태인지 다음 명령으로 확인합니다.

```bash
bash scripts/verify.sh
```

다음 항목을 점검합니다.

- `CLOUDTYPE_API_KEY` 환경변수 존재 여부
- `/auth` 호출을 통한 인증 동작 확인
- 사용자의 스페이스 정보 (uid, scope, role) 조회 가능 여부
