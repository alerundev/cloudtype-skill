# Cloudtype API Spec

이 문서는 Cloudtype 스킬이 사용하는 HTTP/WebSocket API의 핵심 표면을 정리한 것이다.
검증된 동작과 키 이름 위주로 정리했으며, SKILL.md 정책과 일관되게 작성됐다.

## Base URLs

| 환경 | Console | API |
|---|---|---|
| Production | `https://app.cloudtype.io` | `https://api.cloudtype.io` |
| Development | `https://app.cloudtype.dev` | `https://api.cloudtype.dev` |

환경변수 `CLOUDTYPE_API_BASE`로 베이스 URL을 오버라이드할 수 있다.

## Authentication

- 방식: `Authorization: Bearer <JWT_API_KEY>`
- 쿼리 파라미터 `?token=<KEY>` 도 동일하게 동작
- API 키는 콘솔에서 사용자가 직접 발급한다(스킬은 발급하지 않음)
- 인증 시 `/auth` 응답에 `provider: "apikey"`가 포함된다

## Resource Hierarchy

```
User (uid)
 └── Scope (= space)              ← 과금/쿼터 경계
      └── Project
           └── Stage              ← 브랜치/환경 (보통 main)
                └── Deployment    ← 실제 실행 단위
```

## Read API

### Auth / User
| Method | Path |
|---|---|
| GET | `/auth` |
| GET | `/userscope/{uid}/scopes` |
| GET | `/user/byuid?uid={uid}` |
| GET | `/user/authconfig/{uid}` |
| GET | `/user/authconfig/{uid}/github` |

### Scope
| Method | Path |
|---|---|
| GET | `/scope/{scope}` |
| GET | `/scope/{scope}/members` |
| GET | `/scope/{scope}/resource/limit` |
| GET | `/scope/{scope}/resource/stat` |
| GET | `/scope/{scope}/resource/available` |
| GET | `/scope/{scope}/cluster?onlyScoped=true` |
| GET | `/scope/{scope}/cluster/{cluster}` |

리소스 3종의 관계: `available = limit - stat`.
주요 필드: `cpu`, `memory`, `disk`, `running`, `maxReplicas`, `maxCPUPerService`,
`maxMemoryPerService`, `maxDiskPerService`, `spot.*`, `ephemeral.*`,
`service`, `servicePerStage`, `project`, `stage`, `maxImageSize`, `logRetention`,
`deploymentRetention`.

### Project / Stage
| Method | Path |
|---|---|
| GET | `/project?uid={uid}` |
| GET | `/project/{scope}` |
| GET | `/project/{scope}/{project}` |
| GET | `/project/{scope}/{project}/stage` |
| GET | `/project/{scope}/{project}/stage/{stage}` |
| GET | `/project/{scope}/{project}/stage/{stage}/stat` |
| GET | `/project/{scope}/{project}/stage/{stage}/cluster` |
| GET | `/project/{scope}/{project}/stage/{stage}/deployment` |
| GET | `/project/{scope}/{project}/stage/{stage}/events?deployment={name}` |
| GET | `/project/{scope}/{project}/stage/{stage}/vars` |
| GET | `/project/{scope}/{project}/stage/{stage}/route` |

> 시크릿 GET (`/project/{scope}/{project}/stage/{stage}/secret`) 은 평문을 반환하므로
> 스킬에서는 호출하지 않는다. 시크릿 확인이 필요하면 Cloudtype UI에서 직접 본다.

### Deployment
| Method | Path |
|---|---|
| GET | `.../deployment/{name}` |
| GET | `.../deployment/{name}/stat` |
| GET | `.../deployment/{name}/session` |
| GET | `.../deployment/{name}/session/latest` |
| GET | `.../deployment/{name}/resource/service` |
| GET | `.../deployment/{name}/resource/route` |
| GET | `.../deployment/{name}/resource/volume` |

### Catalog
| Method | Path |
|---|---|
| GET | `/app/presets` |
| GET | `/app/presets?offset=0&limit=200` |
| GET | `/app/metadata` |

## Write / Action API

### Project
| Method | Path | Notes |
|---|---|---|
| POST | `/project` | Body: `{ "scope": "...", "name": "...", "displayName": null, "cluster": "..." }` |

### Deployment

배포 생성/업데이트/재배포는 **같은 PUT 엔드포인트**를 사용한다.

| Method | Path | 용도 |
|---|---|---|
| PUT | `/project/{scope}/{project}/stage/{stage}/deployment` | 생성 / 업데이트 / 재배포 |
| PUT | `/project/{scope}/{project}/stage/{stage}/deployment/{name}/start` | 정지된 deployment 시작 |
| PUT | `/project/{scope}/{project}/stage/{stage}/deployment/{name}/stop` | 실행 중 deployment 정지 |

규칙:
- 같은 `name` + 같은 spec → 재배포 (새 빌드 세션)
- 같은 `name` + env/resources/branch 변경 → 업데이트 + 재배포
- 다른 `name` → 생성

> 서비스 삭제(`DELETE .../deployment/{name}`)는 되돌릴 수 없으므로
> 스킬에서 자동 호출하지 않고 Cloudtype UI에서 직접 수행하도록 안내한다.

### Stage-level secrets

| Method | Path | Body |
|---|---|---|
| PUT | `/project/{scope}/{project}/stage/{stage}/secret` | `{ "secrets": { "<key>": "<value>" }, "merge": true }` |

- 기본 `merge: true` 강제 — 기존 시크릿 보존
- `merge: false`(전체 교체)는 사용자가 명시적으로 요청한 경우에만 호출자가 전달
- GET 은 스킬에서 호출하지 않는다(위 Read API 주의 참고)

### Deployment request body

```jsonc
{
  "request": [
    {
      "name": "<service-name>",
      "app": "<preset.config[0].app>",         // 예: "node@20", "web", "dockerfile", "container", "postgresql@16"
      "options": {
        "ports": "8080",
        "env": [
          { "name": "NODE_ENV", "value": "production" },
          { "name": "DB_PASSWORD", "secret": "<stage-secret-key>" }
        ],
        "buildenv": []
      },
      "resources": {
        "spot": false,
        "cpu": 1,
        "memory": 1,
        "disk": 10,
        "replicas": 1
      },
      "context": {
        "preset": "<preset-name>",
        "git": {
          "url": "https://github.com/<owner>/<repo>.git",
          "branch": "main",
          "path": "/backend"
        }
      }
    }
  ],
  "owner": "<uid>"
}
```

핵심 주의:
- `request.app`은 preset 이름이 아니라 **preset metadata의 `config[0].app` 값**이다.
  preset 이름을 그대로 넣으면 `app "<name>" in "<deployment>" does not exist` 오류가 난다.
- 서브 디렉토리는 `context.git.path` 사용 (`subpath`가 아님).
- 빈/디폴트 값은 가능한 한 보내지 않는다 (서버 디폴트 + 사용자 코드 컨벤션을 신뢰).

## WebSocket Endpoints

세 엔드포인트 모두 같은 `prepare` envelope 핸드셰이크를 쓴다.

| Endpoint | 용도 |
|---|---|
| `wss://api.cloudtype.io/project/build/logs` | 빌드 로그 스트림 |
| `wss://api.cloudtype.io/project/logs` | 런타임 stdout/stderr 스트림 |
| `wss://api.cloudtype.io/project/attach` | 인터랙티브 셸 (pty) |

핸드셰이크 (클라이언트 → 서버 첫 메시지):

```json
{
  "type": "prepare",
  "params": {
    "scope": "<scope>",
    "project": "<project>",
    "stage": "<stage>",
    "deployment": "<deployment>",
    "options": {
      "follow": true,
      "pretty": false,
      "tailLines": 500,
      "previous": false,
      "timestamps": true
    }
  },
  "headers": {
    "Authorization": "Bearer <API_KEY>",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*"
  }
}
```

서버가 `"accept"`를 답하면 그 뒤로 텍스트 프레임이 흐른다.

- 런타임 로그 라인 포맷: `<RFC3339 nano timestamp> <stdout/stderr text>`
  (`timestamps: false`이면 타임스탬프 생략)
- 빌드 로그는 자유 텍스트 + 진행 표시(emoji)
- 빌드가 끝나면 서버가 close code `1005`로 정상 종료
- `/project/attach`는 `{ "r": 60, "c": 128 }` 같은 리사이즈 제어 메시지를 받을 수 있고
  서버는 raw pty 출력을 흘려보낸다

## Preset 정리

| Preset 종류 | `app` 값 패턴 | 예시 |
|---|---|---|
| Framework (node / python / java …) | `<runtime>@<version>` | `node@20`, `python@3.11`, `openjdk@17` |
| Web (빌드 결과 정적 서빙) | `web` | html, vue, react 등 |
| Dockerfile | `dockerfile` | repo 안 Dockerfile 빌드 (또는 `dockerfiletext` 인라인) |
| Container | `container` | 외부 도커 이미지 그대로 실행 |
| DB | `<engine>@<version>` | `postgresql@16`, `mariadb@10`, `redis@7` |

→ preset metadata의 `config[0].app` 값을 그대로 `request.app`에 넣는다.

### 주요 옵션 요약 (`options`)

| Key | 타입 | 용도 |
|---|---|---|
| `ports` | string\|int | 서비스 포트 |
| `env` | array | 런타임 환경변수 (`{name, value}` 또는 `{name, secret}`) |
| `buildenv` | array | 빌드 타임 환경변수 |
| `install` / `build` / `start` | string | 프레임워크 preset의 명시 명령 |
| `healthz` | string | 헬스체크 HTTP 경로 |
| `initialDelaySeconds` | string\|int | 헬스체크 시작 전 대기 |
| `strategy` | string | `rolling` 또는 `recreate` |
| `npmrc` | string | private npm registry 인증용 .npmrc 내용 |
| `docbase` | string | (web) 정적 산출물 루트 — vue/vite는 `/dist` 권장 |
| `spa` | bool | (web) SPA 폴백 |
| `nodeversion` | int | (web) 빌드용 Node 버전 |
| `rewrites` | array | (web) 리버스 프록시 규칙 |
| `dockerfile` / `dockerfiletext` | string | (dockerfile) 파일 경로 또는 인라인 내용 |
| `commands`, `uid`, `gid`, `shell`, `args`, `labels` | various | (dockerfile/container) 컨테이너 레벨 제어 |
| `image` | string | (container) 외부 도커 이미지 (`org/name:tag`) |
| `rootusername` / `rootpassword` / `database` / `config` / `tz` | string | (DB preset) |

### Multi-deployment 내부 통신

같은 stage 안의 deployment 끼리는 **deployment name이 내부 hostname**이 된다.

- 예: backend에서 `PGHOST=postgres-db`, `PGPORT=5432` 로 내부 접속
- 외부 공개 URL이 아니라 클러스터 네트워크 경유
- 프론트가 빌드 타임에 백엔드 URL을 묶어 넣어야 한다면 `buildenv`의 `VITE_*` 같은 값을 사용

### 서브 디렉토리 / Monorepo

- 정답 키는 `context.git.path` (예: `/backend`, `/frontend`)
- `subpath`라는 키는 서버 응답에 echo 되더라도 빌드에서 무시될 수 있으므로 사용 금지

### Rewrites (web preset)

프론트 코드가 자신을 호출하도록 작성된 경우 backend로 프록시할 수 있다.

| 코드 형태 | Rewrites 적용 가능? | 조치 |
|---|---|---|
| `fetch('/api/...')` 상대경로 | 가능 | rewrites 추가 |
| `fetch(API_BASE + '/api/...')` env 분기 | 가능 | env를 빈 문자열로 + rewrites 추가 |
| `fetch('https://hardcoded/...')` | 불가 | 코드 측 수정 필요 |

```jsonc
"options": {
  "rewrites": [
    { "from": "/api/*", "to": "backend:3000" }
  ]
}
```

## Resources 정책

- `cpu`, `memory`, `disk`, `replicas`, `spot` 는 **사용자가 명시한 경우에만** PUT에 포함한다.
- OOM/느림이 관측되더라도 스킬이 자동으로 리소스를 증설하지 않는다.
- 진단 시에는 `/scope/{scope}/resource/available` 의 값을 함께 알려 사용자가 의사결정하도록 돕는다.

## Known Plan Limits (Hobby 기준 참고치)

- Max image size: 5 GB
- Log retention: 15 days
- Deployment retention: 15 versions
- Concurrent deploy: 3
- Daily deploy count: 100
- Per-service: 최대 4 vCPU / 16 GB / 1000 GB disk
- Projects: 15
- Stages per project: 8
- Services per stage: 32

플랜에 따라 실제 한도는 다르며, `/scope/{scope}/resource/limit` 응답이 최종 기준이다.

## 응답/동작상의 주의점

- **PUT 직후 응답의 spec은 stale 할 수 있음.** 실제 적용 여부는 응답의 `deploying`
  (새 build session id)이 이전과 달라졌는지로 판단하고, 빌드 로그 메타에서 최종 확인한다.
- **GET deployment 응답의 env value는 마스킹된다.** 실제 컨테이너 안에서는 평문으로
  존재하며, 스킬은 응답으로 env 값을 재확인하려고 하지 않는다.
- **DELETE 후 단건 GET이 200 + empty body로 응답**할 수 있다. 존재 여부는 stage의
  deployment 목록 등으로 판단한다.
- **빌드 로그 WS는 빌드 종료 시 close code 1005로 정상 종료**된다.
