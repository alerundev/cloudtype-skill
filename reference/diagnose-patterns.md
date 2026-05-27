# Diagnose Patterns (보조 문서)

> 이 문서는 참조용이다. 여기 적힌 패턴에 해당하지 않는 문제도 에이전트는
> 빌드/실행 로그와 상태 정보, `API_SPEC.md`, 공식 문서를 바탕으로 추론해 처리한다.
> 새로 발견한 패턴은 이 문서에 누적해 두면 다음 세션에서 더 빠르게 대응할 수 있다.

## 사용 원칙

- **자동 fix 금지** — 근거 없는 추측 변경은 하지 않는다.
- **로그 + 상태 정보로 원인이 명확한 경우** Cloudtype 설정을 수정하고 재배포한다.
- **자동 재시도는 최대 3회**.
- **리소스(`cpu`/`memory`/`disk`/`replicas`/`spot`) 자동 조정 금지**.
- **코드 수정**은 코드 권한이 있는 워크플로우에서만, 허락을 받은 뒤에 수행한다.
- 모든 단계에서 막히면 **운영자에게 문의를 남기도록 안내**한다.

## 빌드 단계 (build logs)

### `package.json not found` / `COPY ... not found`
- 빌드 컨텍스트 루트에 파일이 없음 (보통 monorepo).
- 해결: `context.git.path`에 서브 디렉토리 지정 (`/backend` 등).

### `Module not found`
- 원인 A: `dependencies`에 빠진 모듈 → 코드 수정 필요.
- 원인 B: 런타임 버전 불일치(예: Node ESM/import 신문법) → 배포 설정으로 우선 처리.
  - Node: `options.nodeversion` 조정 또는 dockerfile preset 전환.
  - Python/Java 등도 동일하게 **preset/runtime 버전 설정**을 먼저 맞춘다.

### `npm ERR! 401 Unauthorized` (private 패키지)
- `options.npmrc`에 .npmrc 내용 주입(토큰 포함 시 시크릿 사용 권장).

### 빌드 명령 불일치 (pnpm/yarn 등)
- `options.install`, `options.build`, `options.start`를 사용자 프로젝트에 맞춰 명시.

### vite/webpack 산출물이 안 보임 (소스 HTML이 그대로 노출)
- web preset의 `docbase` 기본값(`/`) 문제.
- 해결: `options.docbase`를 `/dist` 또는 `/build`로.

### 이미지 / 빌드 산출물 5GB 초과 (플랜 제한)
- Cloudtype Hobby 기준 이미지 5GB 제한 (실제 한도는 `/scope/{scope}/resource/limit` 응답에 따른다).
- 우선 시도:
  - 더 가벼운 base image, 멀티스테이지 빌드.
  - `.dockerignore` / 불필요 파일 제외.
  - 정적 산출물 경로/번들 분할.
- 바로 운영자 문의로 넘기지 않고 빌드/이미지 최적화로 먼저 대응한다.

## 실행 단계 (runtime logs / k8s events)

### `EADDRINUSE` / `listen EACCES`
- 포트 충돌/권한.
- `options.ports`를 코드가 listen하는 포트와 일치시키거나, 코드가 `process.env.PORT`를 따르도록.

### CrashLoopBackOff / 컨테이너 즉사
- 로그로 세분:
  - 런타임 의존성 누락 → 코드 수정 필요.
  - DB 호스트가 `localhost`/하드코드 IP → 코드 수정 필요.
  - 필수 env 누락(`DATABASE_URL` 등) → 설정으로 env 추가.

### `localhost` / `127.0.0.1` / 하드코드 IP
- 설정으로는 해결 불가, 코드 수정 필요.
- 안내: 환경변수로 분리하거나 같은 stage 내 서비스명으로 변경.

### CORS 에러 (브라우저 콘솔)
- 프론트 코드 형태에 따라 분기:
  - `fetch('/api/...')` 상대경로 → Rewrites 추가로 해결 가능.
  - `fetch(API_BASE + '/api/...')` env 분기 → Rewrites + env 조정으로 해결 가능.
  - 하드코드 URL → 코드 수정 필요.
- 백엔드 CORS 헤더 누락 → 코드 수정 필요(미들웨어 등).

### `permission denied` / 파일 시스템 권한
- dockerfile preset의 `uid`/`gid` 옵션 조정.
- 혹은 코드가 root 가정을 두지 않도록(코드 측).

### 헬스체크 실패 (`/healthz` 503 등)
- `options.healthz`에 실제 헬스체크 경로 명시.
- 부팅이 느린 앱은 `options.initialDelaySeconds` 증가.

### OOM (`OOMKilled`, exit 137)
- **자동 조정 금지**. 현황 보고 + 사용자에게 선택지 제시(메모리 증설은 사용자 명시 후).

### DB 연결 실패 (`ECONNREFUSED ...:5432`, `authentication failed`)
- 같은 stage 내라면 deployment name이 hostname.
- 시크릿/`PGHOST`/`DATABASE_URL` 등 env 정리.
- 하드코드 접속 설정은 코드 수정 필요.

## 프로젝트/스테이지 부재

- 배포 요청 시 project가 없으면 **먼저 `POST /project`로 생성**한 뒤
  생성된 project의 **main stage**에 배포한다.
- stage가 없는 경우도 동일하게 우선 생성 흐름을 따른다.

## 시크릿 / 삭제 정책

- **시크릿 조회는 스킬에서 수행하지 않는다.** 기존 시크릿 확인이 필요하면 Cloudtype UI로 유도.
- **시크릿 쓰기는 항상 `merge: true`**가 기본. 전체 교체(`merge: false`)는 명시적 요청 + 재확인 시에만.
- **삭제(서비스/프로젝트/스테이지)는 스킬 자동 액션 금지.** 삭제가 필요하면 UI에서 직접 하도록 안내.

## 운영자 문의로 넘기는 기준

- 자동 재시도(최대 3회) 후에도 동일 실패가 지속될 때.
- 로그 근거가 부족해 설정 변경 방향을 정하기 어렵고, 코드 수정 권한도 없을 때.
- 문서상 제한(예: 이미지 5GB)을 우회할 수 없고 사용자 측 조치도 불가능할 때.

> Cloudtype 운영자는 사용자의 소스코드에 접근하지 않는다. 문의로 유도할 때는
> 배포 설정/로그 관점의 정보만 정리해 전달한다.
