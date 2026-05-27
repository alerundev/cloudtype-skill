# Diagnose Patterns (보조 문서)

이 문서는 진단을 위한 **참조용 패턴 모음**입니다.
여기에 정리되지 않은 문제도, 에이전트는 빌드/실행 로그와 상태 정보,
`API_SPEC.md`, 그리고 Cloudtype 공식 문서를 바탕으로 추론하여 처리할 수 있습니다.
새로 확인된 패턴은 이 문서에 추가하면 다음 작업에서 더 빠르게 대응할 수 있습니다.

## 사용 원칙

- **자동 fix 금지** — 근거 없는 추측 변경은 하지 않습니다.
- **로그와 상태 정보로 원인이 명확한 경우**에 한해 Cloudtype 설정을 수정하고 재배포합니다.
- **자동 재시도는 최대 3회**까지 수행합니다.
- **리소스(`cpu`/`memory`/`disk`/`replicas`/`spot`) 자동 조정은 금지**합니다.
- **코드 수정**은 코드 권한이 있는 워크플로에서만, 사용자 확인을 받은 뒤에 수행합니다.
- 모든 단계에서 막히면 **사용자가 운영 채널로 문의를 남기도록 안내**합니다.

## 빌드 단계 (build logs)

### `package.json not found` / `COPY ... not found`
- 원인: 빌드 컨텍스트 루트에 파일이 없음 (대표적으로 monorepo 구조).
- 해결: `context.git.path` 에 하위 디렉토리 경로 지정 (예: `/backend`).

### `Module not found`
- 원인 A: `dependencies` 에 빠진 모듈 → 코드 수정 필요.
- 원인 B: 런타임 버전 불일치(예: Node ESM/import 문법) → 배포 설정으로 우선 시도 가능.
  - Node: `options.nodeversion` 조정 또는 dockerfile preset 으로 전환.
  - Python/Java 등 다른 런타임도 동일하게 **preset 또는 런타임 버전 설정**을 먼저 맞춰봅니다.

### `npm ERR! 401 Unauthorized` (private 패키지)
- `options.npmrc` 에 .npmrc 내용을 주입합니다(토큰 포함 시 시크릿 사용을 권장).

### 빌드 명령 불일치 (pnpm / yarn 등)
- `options.install`, `options.build`, `options.start` 를 프로젝트에 맞춰 명시합니다.

### Vite/Webpack 산출물이 노출되지 않음 (소스 HTML 이 그대로 보임)
- 원인: web preset 의 `docbase` 기본값(`/`) 이 적용되어 있음.
- 해결: `options.docbase` 를 `/dist` 또는 `/build` 등 빌드 산출물 경로로 지정합니다.

### 이미지 / 빌드 산출물 5GB 초과 (플랜 제한)
- Hobby 플랜 기준 이미지 5GB 제한이 적용됩니다.
- 우선 시도할 수 있는 방향:
  - 더 가벼운 base image 또는 멀티스테이지 빌드 적용
  - `.dockerignore` 정비, 불필요 파일 제외
  - 정적 산출물 분리 또는 번들 분할
- 위 방법으로 해소되지 않으면 운영 채널로 문의를 안내합니다.

## 실행 단계 (runtime logs / k8s events)

### `EADDRINUSE` / `listen EACCES`
- 원인: 포트 충돌 또는 권한 문제.
- 해결: `options.ports` 를 앱이 실제로 listen 하는 포트와 일치시키거나,
  코드가 `process.env.PORT` 를 따르도록 변경하는 방법(코드 측 대응)을 안내합니다.

### CrashLoopBackOff / 컨테이너 즉시 종료
- 실행 로그로 원인을 세분합니다.
  - 런타임 의존성 누락 → 코드 수정 필요.
  - DB 호스트가 `localhost` 또는 하드코딩된 IP → 코드 수정 필요.
  - 필수 환경변수 누락(`DATABASE_URL` 등) → 설정으로 env 추가.

### `localhost` / `127.0.0.1` / 하드코딩 IP
- 배포 설정만으로는 해결이 어려우며 코드 수정이 필요합니다.
- 안내 예시: "환경변수로 분리하거나 같은 stage 내 서비스명으로 변경해 주시기 바랍니다."

### CORS 에러 (브라우저 콘솔)
- 프론트엔드 코드 형태에 따라 분기합니다.
  - `fetch('/api/...')` 상대 경로 → Rewrites 로 해결 가능
  - `fetch(API_BASE + '/api/...')` env 분기 → Rewrites + env 조정으로 해결 가능
  - 하드코딩된 URL → 코드 수정 필요
- 백엔드 CORS 헤더 누락이 원인이면 코드 수정이 필요합니다(미들웨어 추가 등).

### `permission denied` / 파일 시스템 권한
- dockerfile preset 의 `uid` / `gid` 옵션을 조정합니다.
- 코드가 root 권한을 가정하지 않도록 변경하는 방향도 함께 안내할 수 있습니다.

### 헬스체크 실패 (`/healthz` 503 등)
- `options.healthz` 에 실제 헬스체크 경로를 명시합니다.
- 부팅이 느린 앱은 `options.initialDelaySeconds` 를 늘립니다.

### OOM (`OOMKilled`, exit code 137)
- 자동 조정은 수행하지 않습니다. 현재 사용량 및 잔여 풀을 보고하고,
  사용자에게 선택지(메모리 증설 / 코드 점검)를 제시합니다.

### DB 연결 실패 (`ECONNREFUSED ...:5432`, `authentication failed`)
- 같은 stage 내에서는 deployment name 이 hostname 역할을 합니다.
- env 의 `PGHOST` / `DATABASE_URL` 등을 정리하고 시크릿 참조를 확인합니다.
- DB 접속 정보가 코드에 하드코딩된 경우 코드 수정이 필요합니다.

## 프로젝트 / 스테이지 부재

- 배포 요청 시 project 가 없으면 **먼저 `POST /project` 로 생성**한 뒤
  생성된 project 의 main stage 에 배포합니다.
- stage 가 없는 경우도 동일하게 우선 생성 후 진행합니다.

## 시크릿 / 삭제 정책

- **시크릿 조회는 스킬에서 수행하지 않습니다.** 기존 시크릿 확인이 필요하면 Cloudtype UI 사용을 안내합니다.
- **시크릿 쓰기는 항상 `merge: true`** 가 기본입니다.
  전체 교체(`merge: false`)는 사용자의 명시적 요청이 있고 한 번 더 확인된 경우에만 수행합니다.
- **삭제(서비스 / 프로젝트 / 스테이지)는 스킬의 자동 액션으로 수행하지 않습니다.**
  삭제가 필요하면 Cloudtype UI 에서 직접 수행하도록 안내합니다.

## 운영 채널 문의로 안내하는 기준

- 자동 재시도(최대 3회) 이후에도 동일한 실패가 지속되는 경우
- 로그 근거가 부족하여 설정 변경 방향을 정하기 어렵고, 코드 수정 권한도 없는 경우
- 문서상 제한(예: 이미지 5GB)을 우회할 수 없고 사용자 측 조치도 불가능한 경우

운영 채널은 일반적으로 사용자의 소스코드에 직접 접근하지 않습니다.
문의를 안내할 때는 **배포 설정과 로그 관점의 정보**를 정리해 전달하도록 합니다.
