# Diagnose Patterns (보조 자료)

이 문서는 SKILL.md 의 실패 대응 절차를 보조하는 **참조용 사례 모음**입니다.
의사결정의 기반은 SKILL.md 의 원칙입니다.

- 같은 deployment 의 로그/이벤트로 원인 파악
- 원인이 명확한 Cloudtype 설정 문제면 옵션을 조정하고 같은 deployment 에 같은 PUT 재호출
- 자동 재시도는 같은 처방으로 최대 3회
- 다른 preset 으로 갈아타거나 새 서비스 생성 같은 우회는 사용자 승인 후에만

여기에 정리되지 않은 패턴은 빌드/실행 로그 / 상태 정보 / API_SPEC / 공식 문서를 바탕으로 추론하여 처리합니다.
새로 확인된 패턴은 이 문서에 누적하면 다음 작업에서 더 빠르게 대응할 수 있습니다.

## 빌드 단계 (build logs)

### `package.json not found` / `COPY ... not found`
- 원인: 빌드 컨텍스트 루트에 파일이 없음 (일반적으로 monorepo 구조)
- 해결 (설정): `context.git.path` 에 하위 디렉토리 경로 지정 (예: `/backend`)
- 코드 수정 필요 여부: 없음

### `Module not found` (빌드 시)
- 원인 A: `dependencies` 에 빠진 모듈
- 원인 B: 같은 preset 내 런타임 버전 불일치
- 해결 (설정): 원인 B 의 경우 `options.nodeversion` 같은 같은 preset 내 버전 옵션을 조정합니다.
- 코드 수정 필요 여부: 원인 A 의 경우 `package.json` 의 `dependencies` 에 누락 모듈을 추가하고 push 가 필요합니다.

### `npm ERR! 401 Unauthorized` (private 패키지)
- 원인: private npm registry 인증
- 해결 (설정): `options.npmrc` 에 .npmrc 내용을 주입 (auth token 포함)
- 코드 수정 필요 여부: 없음 (단, .npmrc 토큰은 시크릿화 권장)

### 빌드 명령 불일치 (예: pnpm 프로젝트가 yarn 으로 빌드되는 경우)
- 해결 (설정): `options.install`, `options.build`, `options.start` 를 프로젝트에 맞게 명시
- 예: `install: "pnpm install"`, `build: "pnpm build"`, `start: "pnpm start"`

### Vite / Webpack 빌드 결과가 노출되지 않음 (소스 HTML 그대로 보임)
- 원인: web preset 의 `docbase` 가 기본값(`/`) 으로 설정됨
- 해결 (설정): `options.docbase` 를 `/dist` 또는 `/build` 로 지정
- 코드 수정 필요 여부: 없음

### 이미지 / 빌드 산출물 5GB 초과 (플랜 제한)
- Hobby 플랜 기준 이미지 5GB 제한이 적용됩니다.
- 우선 시도할 수 있는 방향:
  - 더 가벼운 base image 또는 멀티스테이지 빌드 적용
  - `.dockerignore` 정비, 불필요 파일 제외
  - 정적 산출물 분리 또는 번들 분할
- 위 방향으로 해소되지 않으면 운영 채널 문의를 안내합니다.

## 실행 단계 (runtime logs / k8s events)

### `EADDRINUSE` / `listen EACCES`
- 원인: 포트 충돌 또는 권한 문제
- 해결 (설정): `options.ports` 를 앱이 실제 listen 하는 포트와 일치시킵니다.
- 코드가 `process.env.PORT` 를 따르도록 변경하는 방향(코드 측 표준 컨벤션)도 권장 가능합니다.

### 컨테이너 즉시 종료 (CrashLoopBackOff)
- 로그를 자세히 살펴 원인을 분류합니다.
  - `Error: Cannot find module 'xxx'` → 런타임 의존성 누락 (코드 측)
  - `Error: connect ECONNREFUSED 127.0.0.1:5432` → DB 호스트가 localhost 로 하드코딩됨 (코드 측)
  - `MissingEnvironmentError: DATABASE_URL` → 환경변수 누락 (설정으로 해결 가능: env 추가)

### `localhost` / `127.0.0.1` / 하드코딩된 IP
- 원인: 코드에 로컬 주소가 하드코딩되어 있음
- 설정만으로 해결이 어려우며 코드 수정이 필요합니다.
- 안내 예시: "해당 코드 위치에 `localhost` 가 하드코딩되어 있습니다. 다음 중 하나로 변경해 주시기 바랍니다.
  1) 환경변수로 분리 (`process.env.DB_HOST`)
  2) 같은 stage 내 서비스명으로 변경 (예: `postgres-db`)"

### CORS 에러 (브라우저 콘솔)
- 코드 형태에 따라 분기합니다.
  - `fetch('/api/...')` (상대 경로) → Rewrites 추가로 해결 가능
  - `fetch(API_BASE + '/api/...')` (env 분기) → Rewrites 추가와 함께 env 를 비우거나 백엔드 URL 을 env 로 설정
  - `fetch('https://hardcoded/api/...')` (하드코딩) → 코드 수정 필요
- 백엔드의 CORS 헤더 누락이 원인인 경우 코드 수정이 필요합니다 (CORS 미들웨어 추가 등).

### 헬스체크 실패 (응답 없음 또는 status 503 등)
- 원인: readiness probe 가 root 경로에 GET 요청을 수행하는데 앱에 해당 경로가 없는 경우 등
- 해결 (설정): `options.healthz` 에 앱의 실제 헬스체크 경로를 명시
- 부팅이 느린 앱은 `options.initialDelaySeconds` 를 늘립니다.

### OOM (`OOMKilled`, exit code 137)
- 자동 조정은 수행하지 않습니다. 사용자에게 다음과 같이 보고합니다.
  - "OOM 이 감지되었습니다. 현재 메모리 X GB, 잔여 풀 Y GB 입니다. 메모리를 증설할까요? 아니면 코드 측 누수 점검을 먼저 진행할까요?"

### DB 연결 실패 (`ECONNREFUSED ...:5432`, `authentication failed` 등)
- 원인 A: hostname 오류 (같은 stage 내에서는 deployment name 이 hostname)
- 원인 B: 시크릿 누락 또는 잘못된 참조
- 해결 (설정): env 의 `PGHOST`, `DATABASE_URL` 등을 조정하고 시크릿 참조를 확인합니다.
- 코드 수정 필요 여부: DB 접속 설정이 코드에 하드코딩된 경우

## 프로젝트 / 스테이지 부재

- 배포 요청 시 project 가 없으면 **먼저 `POST /project` 로 생성**한 뒤 생성된 project 의 main stage 에 배포합니다.
- stage 가 없는 경우도 동일하게 우선 생성 후 진행합니다.

## 시크릿 / 삭제 정책

- **시크릿 조회는 스킬에서 수행하지 않습니다.** 기존 시크릿 확인이 필요하면 Cloudtype UI 사용을 안내합니다.
- **시크릿 쓰기는 항상 `merge: true`** 가 기본입니다.
- **삭제(서비스 / 프로젝트 / 스테이지)는 스킬의 자동 액션으로 수행하지 않습니다.** Cloudtype UI 에서 직접 수행하도록 안내합니다.

## 운영 채널 문의로 안내하는 기준

- 자동 재시도(최대 3회) 이후에도 동일한 실패가 지속되는 경우
- 로그 근거가 부족하여 설정 변경 방향을 정하기 어렵고, 코드 수정 권한도 없는 경우
- 문서상 제한(예: 이미지 5GB)을 우회할 수 없고 사용자 측 조치도 불가능한 경우

운영 채널은 일반적으로 사용자의 소스코드에 직접 접근하지 않습니다.
문의를 안내할 때는 **배포 설정과 로그 관점의 정보**를 정리해 전달하도록 합니다.
