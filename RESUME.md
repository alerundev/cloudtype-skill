# RESUME.md — Cloudtype Skill Project

> **새 세션이 이 파일을 보면 작업을 이어갈 수 있도록 작성됨.**
> 마지막 업데이트: **2026-05-27 11:47 KST**
>
> 지금 상태:
> - `SKILL.md` 2차 반영 완료 (정책/흐름/진단 필드 일괄 정리).
> - `reference/diagnose-patterns.md` 추가 (보조 진단 문서).
> - 다음 작업: `scripts/cloudtype_client.py` / `cloudtype_actions.py` / `cloudtype_logs.py` 구현, 이후 e2e 검증 및 패키징/푸시.

## ✨ 지금 바로 어디서 이어가야 하나? (핵심)

**운영자가 SKILL.md 1차 초안을 확인함. 코멘트는 며칠 뒤에 주기로 함.**

새 세션이 일어나면 운영자(james_cloud17) 다음 메시지를 기다릴 것.
운영자가 SKILL.md에 대한 코멘트를 주면 그 피드백을 몇 단계 반영해서 **2차** 작성.

운영자가 아무 말 없이 "이어가자" 하면:
1. 먼저 `cloudtype/SKILL.md` 읽으라고 안내
2. 코멘트 받아서 수정
3. 그 후 다음 단계 (아래 "다음 작업" 세션 참조)

## 다음 작업 (SKILL.md 코멘트 이후)

1. **SKILL.md 2차** — 운영자 피드백 반영
2. **scripts/cloudtype_client.py** 짤기 — HTTP + auth + base API 래퍼 (명세 다 있음)
3. **scripts/cloudtype_actions.py** — start/stop/redeploy/create/delete 동사들
4. **scripts/cloudtype_logs.py** — WS 로그 스트리밍 헬퍼
5. **reference/diagnose-patterns.md** — SKILL.md의 진단 트리를 더 자세한 세부 파일로
6. 운영자 권장 시나리오 e2e 검증 (예: 일부러 깨진 repo 배포 → 진단 루프)

## 🎯 이 프로젝트가 뭐였더라?

운영자(james_cloud17, Cloudtype 개발사 측)와 함께 **OpenClaw `cloudtype` 스킬**을
만드는 중. 운영자는 Cloudtype 본인 개발사 사람이고, 테스트 계정의 API 키로 직접
검증하며 작업 중.

**최종 목표:** 어떤 에이전트(Claude Code, Cursor, OpenClaw 등)에 이 스킬만
얹으면 **자연어로 클라우드타입을 완전히 제어**할 수 있게 만드는 것.
**"바이브 코딩 + 바이브 배포" 통합**이 운영자의 큰 그림.

## ⚠️ 절대 건드리지 말 것 (다른 작업과의 분리)

이 워크스페이스에는 **Cloutype AI 디스코드 봇** 관련 자산이 따로 있음. 그 봇은
이 메인 세션과 완전 별개로 디스코드에서 운영 중. 절대 변경 금지:

- `cloudtype-kb.md`, `cloudtype-kb.md.bak.*` — 디스코드 봇 KB
- `cloudtype-docs-src/` — 원본 docs 소스
- `cloutype-ai*.patch.json5`, `cloutype-ai-prompt.patch.json` — 봇 설정 패치
- `knowledge/` 폴더 전체 — FAQ + CHANGELOG
- `build-cloudtype-kb.py`, `build-prompt-patch.py`, `clean-kb.py`, `fix-kb-envvars.py`
- `typing-patch.json5`

**이 프로젝트의 작업 폴더는 `cloudtype/` 하나뿐.** 그 안에서만 작업할 것.

## v1 스코프 (최종 확정, 2026-05-26 17:17)

**목적: 바이브 코딩 + 바이브 배포 통합.** AI가 코드 짜고 → 배포까지 끝내고 → 로그 보고 진단.

✅ v1에 포함:
- 조회 (상태/이벤트/세션/리소스)
- 로그 스트림 (실행/빌드/터미널)
- 생명주기 (start/stop/delete)
- **배포 생성** (PUT .../deployment with full spec)
- **재배포** (같은 PUT 명령으로 자동 재빌드)
- **프로젝트 생성** (POST /project)
- 애드-온 수정 (env, replicas, resources — 다 같은 PUT으로)

❌ v1 제외:
- 도메인 연결 (DNS는 사람이)
- 결제/구독
- API 키 발급
- GitHub OAuth 초기 연동
- 계정 관련

## 📁 이 프로젝트의 파일들

```
cloudtype/
├── RESUME.md          ← 이 파일 (새 세션 진입점)
├── API_SPEC.md        ← 발견한 API 명세 (살아있는 문서)
├── captures/          ← 운영자가 보내준 HAR 캡처 (gzip/zip)
│   ├── 01-initial-recon.har.gz          (첫 정찰, 27 reqs)
│   ├── 02-deployment-tour.har.zip       (배포 상세, 266 reqs)
│   ├── 03-logs-attempt.har.zip          (로그 시도, 377 reqs)
│   └── 04-websocket-logs.har.gz         (WS 잡힌 골드 캡처)
│   (※ #6 har는 GitHub releases — alerundev/releases — 너무 커서 워크스페이스엔 안 둠)
└── scripts/
    └── verify.sh      ← 환경/인증 검증 한 줄 명령
```

## 🔐 환경변수

- `CLOUDTYPE_API_KEY` — JWT API 키 (Bearer 인증용) **필수**
  - uid: `mm8nufqy98769b8f`, scope: `myspace` (Hobby), exp 없음
  - 처음에 채팅 평문 노출되어 폐기 권장했으나, 현재 환경변수 값으로 동작 검증됨
  - (이전엔 `CLOUDTYPE_TESTAPIKEY`로 받았으나 표준 이름으로 통일 — 로컬에서 `export CLOUDTYPE_API_KEY=$CLOUDTYPE_TESTAPIKEY` 한 번 해두면 됨)
- `CLOUDTYPE_API_BASE` (선택) — HTTP base URL 오버라이드, 기본 `https://api.cloudtype.io`
- `CLOUDTYPE_WS_BASE` (선택) — WS base URL 오버라이드, 기본 `wss://api.cloudtype.io`

빠른 검증: `bash cloudtype/scripts/verify.sh`

## ✅ 지금까지 완성한 것 (v1 API 거의 다)

### 인증 ✅
- HTTP: `Authorization: Bearer <key>` 또는 `?token=<key>`
- WebSocket: prepare envelope의 `headers.Authorization`

### 리소스 계층
```
User (uid) → Scope (space) → Project → Stage → Deployment
```

### Read API ✅ (자세한 건 API_SPEC.md)
- `/auth`, `/userscope/{uid}/scopes`
- `/scope/{scope}{,/members,/resource/{limit,stat,available},/cluster,/cluster/{name}}`
- `/project?uid=`, `/project/{scope}`, `/project/{scope}/{project}{,/stage{,/{stage}{,/stat,/cluster,/secret,/vars,/route,/events,/deployment{,/{name}{,/stat,/session{,/latest},/resource/{service,route,volume}}}}}}`
- `/app{,/presets,/categories,/metadata}`

### WebSocket ✅ (검증 완료, 핵심 성과)
- `wss://api.cloudtype.dev/project/logs` — 실행 로그
- `wss://api.cloudtype.dev/project/build/logs` — 빌드 로그
- `wss://api.cloudtype.dev/project/attach` — 터미널 (pty)

핸드셰이크: `{type:"prepare", params:{...}, headers:{Authorization:...}}` JSON
→ 서버 `"accept"` → 텍스트 프레임 스트림.

### Action API ✅ (2026-05-26 17:17 확보)
- `PUT .../deployment/{name}/start` ✅
- `PUT .../deployment/{name}/stop` ✅ (직접 검증)
- `DELETE .../deployment/{name}` ✅
- `PUT .../deployment` — 생성 / 재배포 / 업데이트 다 동일 엔드포인트 ✅
  - 같은 이름 + 같은 spec → **재배포** (새 빌드)
  - 같은 이름 + 다른 env/resources → 업데이트 + 재배포
  - 다른 이름 → 생성
- `POST /project` ✅ (프로젝트 생성)

`/redeploy`, `/apply`, `/rebuild`, `/rollout` 다 404 — **재배포 전용 엔드포인트 없음**,
같은 PUT을 다시 보내는 게 정답.

## 🚧 다음에 할 일

### 1순위: Python SDK + Skill 구조화 🔨
- `scripts/cloudtype_client.py` — auth + HTTP API
- `scripts/cloudtype_logs.py` — WS 로그 스트리밍
- `scripts/cloudtype_actions.py` — start/stop/redeploy/create/delete
- `SKILL.md` — 에이전트 진입점
- `reference/diagnose-patterns.md` — 흔한 에러 패턴 → 진단 매핑

### 2순위: 검증 시나리오
- 일부러 깨진 빌드/실행 케이스 만들어서 진단 흐름 시연
- 운영자와 함께 end-to-end "코드 변경 → 푸시 → 재배포 → 로그 확인" 테스트

### 보류 (필요시 추가)
- DELETE project / stage
- Webhook / GitHub integration setup

## 💬 운영자 정보

- Discord tag: `james_cloud17`
- 클라우드타입 본사 개발자, 한국어 (Asia/Seoul)
- 능동적이고 기술 디테일 좋아함
- 종종 "잠깐, 그런데" 식으로 방향 바꿈 — 유연하게 따라갈 것
- HAR 캡처 + 직접 실험 방식 익숙
- 가벼운 이모지 OK

## 🔍 운영자 환경 (테스트 계정, 2026-05-27 01:21 기준)

- scope: `myspace` (Hobby, owner)
- uid: `mm8nufqy98769b8f`
- projects:
  - `openclaw` (id=mpeu83cy3f5d0b66) — 운영자 실제 운영·테스트 자산
    - deployments: openclaw2, postgresqlchannel, channel-backend, meridian-global-landing, hk-materials-trading
  - `test` (id=mpmcydio324863b2) — 운영자가 시연용으로 만든 곳
    - deployments (전부 stopped, 운영자가 캡처 만들면서 생성):
      - `backend` (캡처 #5 node@20 PUT)
      - `channel-backend` (캡처 #7 dockerfile PUT, alerundev/channel-backend private repo)
      - `demo-meeting-backend` (캡처 #10 web preset PUT with secret ref)
      - `salesforce-mcp` (어제부터 stopped)
    - 주로 이 프로젝트에서 테스트. 운영자 자산이므로 함부로 DELETE 하지 말 것.

## 🆘 새 세션이 시작되면 첫 작업

1. **이 RESUME.md 끝까지 읽기** (특히 먼 상단 "지금 바로 어디서 이어가야 하나" 섹션)
2. **`SKILL.md` 읽기** — 1차 초안이 완성됨, 운영자 피드백 대기 중
3. **`API_SPEC.md` 읽기** — 현재까지의 API 명세 (몇차례 종임으로 풍부함)
4. **`memory/2026-05-26.md` 읽기** — 프로젝트 전체 컨텍스트 (361줄)
5. `bash cloudtype/scripts/verify.sh` — 환경/인증 검증
6. 운영자에게 인사 + 현재 상태 알리기 ("SKILL.md 1차 초안 끝내고 피드백 대기 중")

## 📌 기억해둘 결정사항

### 초기 결정 (2026-05-26)
1. **KB 통합본은 스킬에 안 넣음** — 운영자가 "그건 디스코드 봇 영역, 스킬은 API에만 집중" 라고 명시
2. **테스트 환경은 cloudtype.dev**, 최종 타깃은 cloudtype.io (API 구조는 동일 추정)
3. **v1 = 조회 + 로그 + 배포까지**
4. **상태 데이터는 절대 캐시 금지** (deployment status/ready 같은 휘발성 데이터는 호출 시점에 fresh로)
5. **실험은 `test` 프로젝트에서** — 운영자가 만들어둠

### 운영자 정책 (2026-05-26·27 세션에서 명시, SKILL.md에 박힘)
6. **AI는 절대로 리소스 자동 조정 하지 않음** (선구독 풀 제약 + 사용자 학습 보존 + 진단 정확성)
   - 운영자 명시: "과금 폭탄은 원인 아님 (선구독), 다른 서비스 영향도 아님 (k8s pod limit 격리)"
7. **GitHub 연동은 이미 된 상태 활용만** — Tier 1 (배포에 직접) / Tier 2 (조회) / Tier 3 (절대 금지)
8. **소스코드 수정은 스킬 범위 밖** — 조언만, 실제 수정은 상위 에이전트 담당
9. **배포는 최소 페이로드로 서버 디폴트 의존** — 사용자 코드 관습 자동 인식이 원칙
10. **자동 fix 금지** — 진단 → 옵션 제시 → 사용자 확인 후만 재배포
11. **시크릿 쓰기는 항상 `merge: true`** — 전체 교체는 사용자 명시 시만
12. **container preset은 권장 사용 케이스 아님** — 콘솔이 더 빠름. AI 가치 낮음
13. **재시도 한도 = 3회**
14. **구독·결제·도메인 DNS·계정 관리 = scope 밖**

## 📊 핵심 발견 카탈로그 (캡처 다 분석한 결과)

### 4가지 배포 모드 (모두 검증됨)
| 모드 | `app` 값 | 특징 |
|---|---|---|
| Framework | `node@20`, `python@3.11` 등 | 코드 + 자동 빌드 |
| Web | `web` | 빌드 산출물 정적 서빙 (docbase 함정 주의) |
| Dockerfile | `dockerfile` | 코드 + 직접 Dockerfile 빌드, `dockerfiletext`로 인라인도 가능 |
| Container | `container` | 외부 이미지 그대로 (`image` 필드, git 불필요) |
| DB | `postgresql@16` 등 | 컨테이너 이미지 + preset 옵션 → ENV 자동 매핑 |

### 발견된 옵션 총 30+개
- 공통: `ports`, `env`, `healthz`, `initialDelaySeconds`, `strategy`(recreate/rolling)
- Framework: `install`, `build`, `start`, `buildenv`, `npmrc`
- Web: `docbase`(⚠️기본 `/`로 두면 빌드 산출물 안 보임 — `/dist` 명시 필요), `spa`, `nodeversion`, `rewrites`
- Dockerfile: `dockerfile`, `dockerfiletext`⭐, `commands`, `uid`, `gid`, `shell`, `args`, `labels`
- Container: `image`⭐ (외부 이미지 URL)
- DB: `rootusername`, `rootpassword`, `database`, `config`, `tz`

### 시크릿 모델 (캡처 #9, #10에서 완벽 잡힘)
```
1. stage 단위 저장: PUT /stage/{stage}/secret  body {secrets:{}, merge:true}
2. 배포 시 참조: env에 {name:"DB_PWD", secret:"db-pwd-key"}
   (인라인 값 {name, value}과 같은 배열에 섞여서 OK)
```

### 함정 카탈로그 (운영자 시각 교정 받은 것 포함)
1. **`subpath` ≠ `path`** — 정답은 `context.git.path` (슬래시는 선택)
2. **`docbase` 함정** — web preset은 `/dist` 명시 안 하면 빌드 결과 안 서빙
3. **preset 이름 ≠ `app` 값** — preset 메타의 `config[0].app` 값 사용 (예: html preset의 app은 "web")
4. **DB preset은 그냥 컨테이너 이미지** — preset options이 자동 ENV 매핑 (운영자 시각 교정)
5. **자동 리소스 조정 = 안 됨** — 선구독 풀 + 사용자 학습 + 진단 정확성 (운영자 시각 교정 #2, #3)
6. **CORS 해결의 Rewrites는 조건부** — 코드가 self-referential일 때만 (운영자 시각 교정 #4)
7. **env 값은 응답에서 마스킹** — 실제 값은 잘 들어가지만 GET 응답엔 가려져서 보임
8. **PUT 응답이 stale spec echo할 수도** — 적용 여부는 `deploying` id 변경으로 확인

### KB는 정답 보물창고
`/home/openclaw/.openclaw/workspace/cloudtype-kb.md`에 cloudtype 공식 docs 통합본 있음.
GitHub Actions 섹션의 yaml 스키마가 ≈ API 키와 1:1 매핑. 막히면 KB부터 보기:
- `subpath` 정답 `context.git.path`: 줄 1470 근처
- `rewrites` 리버스 프록시: 줄 1662 근처
- 서비스 간 통신: 줄 1708 근처
- DB 접속/포트: 줄 1733+

### HAR 캡처 카탈로그 (`cloudtype/captures/`)
- 01-04: 초기 read-only (배포 흐름 + WS 핸드셰이크 검증)
- 05: 배포창 투어 + node.js PUT 페이로드 ⭐
- 06: PostgreSQL 배포 ⭐
- 07: Dockerfile 배포 ⭐
- 08: Container 이미지 배포 ⭐
- 09: 시크릿 저장 ⭐
- 10: 시크릿 참조 ⭐
- `WISHLIST.md` — 남은 캡처 가치 정리 (실패 흐름 등)

## 🎨 작업 스타일 메모

- 항상 운영자 자산 보호 우선 (cloudtype-kb 등 절대 안 건드림 — 하지만 **읽으러는 갈 것**)
- 발견한 거 즉시 명세에 반영
- 작은 한 걸음씩 확인 받으며 진행
- 운영자가 시연 자료 만들어주면 같이 더 깊이 들어감
- ⭐ **옵션/기능 막히면 KB 먼저 보기**: `cloudtype-kb.md`는 단순 디스코드 봇 자료 아니라
  **API 명세 즜명서**. 그때그때 관련 섹션 그랩하면 주로 정답 나옷.
  - `subpath`가 아니라 `context.git.path` (줄 1470, GitHub Actions 섹션)
  - `rewrites`는 리버스 프록시 (줄 1662, 개발자 가이드 기능)
  - DB 포트/접속은 줄 1733+ (데이터베이스 관리 섹션)
  - 서비스 간 통신은 줄 1708+ (connect 섹션)
- ⚠️ **추측으로 API 동작 단정 금지**: 근거 (캐처 / KB / 직접 테스트) 없이 "이렇게 될 겁니다" 하지 말 것.
  특히 k8s/docker 일반론으로 클라우드타입 실제 동작 추측 안 됨. 운영자에게 확인 필수.
- ⚠️ **기능 발견·적용에 전제 조건 빼트림 주의**: KB에 멋진 기능 있으면 "이렇게 하면 다 해결!"로 흔히 쓰는데,
  언제나 **코드·설정·동작 전제 조건**이 있음.
  예: Rewrites는 프론트엔드 코드가 self-referential (`fetch('/api/...')`)이어야 적용 가능.
  하드코드 URL이 박혀있으면 Rewrites 불가. 이런 전제를 명시적으로 소리내서 추론해야 함.
- ⚠️ **스킬 입장은 클라우드타입 배포만 다뢸**: 소스코드 분석/수정은 별도 영역.
  소스 수정 필요한 경우는 사용자에게 **서술적으로** 조언하고 스킬 자체가 수정하지는 않음.
  (코드 수정은 상위 에이전트 담당, 우리는 cloudtype 설정만 조정)
