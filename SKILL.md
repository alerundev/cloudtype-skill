---
name: cloudtype
description: "Deploy a GitHub repository to Cloudtype with a minimal payload, then resolve issues by reading the deployment's logs and adjusting its Cloudtype settings."
---

# Cloudtype

GitHub 저장소를 Cloudtype 에 배포하고, 문제가 발생하면 **같은 deployment 의 로그와 설정만** 다뤄 해결을 시도하는 스킬입니다.

배포 자체는 본질적으로 *"최소 페이로드로 PUT 한 번"* 으로 끝나는 작업입니다.
실패 시에도 다른 preset 으로 갈아타거나 새 서비스를 만들지 않고, 동일 deployment 에 같은 PUT 을 다시 호출하는 흐름으로 처리합니다.

---

## 🎯 목표

> GitHub 저장소 → Cloudtype 에서 정상 동작하는 서비스로 배포.

이 스킬의 책임은 **배포 부분에 한정**됩니다.
시스템 설계, 코드 작성, 푸시 같은 상위 작업은 상위 에이전트가 담당합니다.

---

## 🚫 절대 하지 않는 것

다음은 사용자가 명시적으로 요청하지 않은 한 스킬이 직접 수행하지 않습니다.

- **소스코드 직접 수정** — 위치와 수정 방향만 안내합니다.
- **다른 preset 으로 갈아타기** — 예: `web` 실패 → `dockerfile` 로 재배포 (금지)
- **새 deployment 이름으로 별도 서비스 생성하여 우회** — 예: `web` 실패 → `docker-web` 새로 만들기 (금지)
- **Dockerfile 자동 생성 또는 인라인 주입** — `dockerfiletext` 옵션은 사용자가 명시적으로 요청한 경우에만 사용합니다.
- **리소스 사양 자동 조정** — `cpu` / `memory` / `disk` / `replicas` 같은 세부 사양은 사용자가 명시한 경우에만 PUT 에 포함합니다. 자동 증설/축소 금지.
- **풀 종류(`spot`) 의 풀 선택은 자동 조정이 아닙니다.** 잔여 리소스 기반 자동 선택 규칙은 [🎟️ 리소스 선택](#-리소스-선택) 절을 따릅니다.
- **시크릿 조회** — 필요 시 Cloudtype UI 사용을 안내합니다.
- **삭제 (서비스 / 프로젝트 / 스테이지)** — 필요 시 Cloudtype UI 사용을 안내합니다.
- **GitHub 연동 설정 변경 (설치 / 해제)** — 이미 연결된 상태를 활용만 합니다.
- **구독 / 결제 / 리소스 풀 구매** — 사용자가 콘솔에서 직접 처리합니다.
- **API 키 발급** — Cloudtype 콘솔에서만 가능합니다.

---

## 🎟️ 리소스 선택

배포 직전에 `GET /scope/{scope}/resource/available` 로 스페이스의 잔여 리소스를 조회합니다.

응답에는 두 풀의 가용량이 들어 있습니다.

- 구독 풀: `cpu`, `memory`, `disk` (스페이스가 구독을 안 하면 모두 `0`)
- 프리티어 풀: `spot.cpu`, `spot.memory`, `spot.disk`

풀별로 다음 카운터들도 함께 확인합니다. **어느 하나라도 `0` 이면 그 풀은 가용량 없음으로 간주**합니다.

- `running` / `spot.running` — 동시 실행 가능 서비스 수
- `maxReplicas` / `spot.maxReplicas` — 한 서비스 안의 replica 수 한도

풀 공통 한도 (둘 다 부족하면 어느 풀로도 배포 불가):

- `service` — 스페이스 전체 서비스 수
- `servicePerStage` — stage 당 서비스 수

`resources` 페이로드에는 풀 종류만 명시합니다. `cpu` / `memory` / `disk` 같은 세부 사양은 사용자가 명시한 경우에만 포함합니다.

- `spot: true` → 프리티어 풀
- `spot: false` → 구독 풀

### 풀 선택 규칙

1. **사용자가 풀을 명시한 경우** → 그 풀을 그대로 사용합니다.
2. **사용자가 풀을 명시하지 않은 경우** → 잔여 가용량을 보고 자동 선택합니다.
   - 구독 풀에 가용량이 있으면 구독 풀(`spot: false`)
   - 구독 풀이 `0` 이고 프리티어 풀에 가용량이 있으면 프리티어 풀(`spot: true`)

### 리소스 부족

선택된 풀의 가용량이 배포 요구치보다 작으면 **배포를 시도하지 않고** 사용자에게 알립니다. 자동 재시도 / 다른 풀로의 자동 우회 금지.

- 프리티어 풀이 부족: "프리티어 한도를 다 썼습니다. 추가 배포에는 구독이 필요합니다." 콘솔 구독 안내.
- 구독 풀이 부족: "구독 풀이 부족합니다." 콘솔에서 구독 추가 안내.
- 풀 공통 한도(`service` / `servicePerStage`) 가 부족: "스페이스의 서비스 수 한도를 다 썼습니다." 기존 서비스 정리 또는 한도 확장 안내.

구독/결제는 스킬 범위 밖이며 사용자가 콘솔에서 직접 처리합니다.

### 완료 보고

배포 응답의 `resources.spot` 을 "프리티어 리소스" / "구독 리소스" 로 변환해 명시합니다. 사용자가 명시한 의도와 응답이 다르면 완료 보고를 보류하고 사용자에게 말합니다.

---

## 🧭 입력 추론과 디폴트

사용자가 명시하지 않은 항목은 스킬이 추론합니다. **세세한 사항을 일일이 묻지 않습니다.**

| 항목 | 디폴트 / 추론 방식 |
|---|---|
| repo | 사용자가 정확한 URL 을 주지 않은 경우 `/oauth/github/*` 로 사용자의 repo 목록을 조회하여 이름 매칭. 후보가 하나면 진행, 여러 개면 선택지 제시. |
| branch | 명시 없으면 `main` |
| project | 명시 없으면 repo 이름. 해당 project 가 없으면 생성 (`POST /project`) |
| stage | 명시 없으면 `main` |
| deployment 이름 | 명시 없으면 **repo 이름** (대문자 → 소문자, 언더스코어 → 하이픈 등 Cloudtype 식별자 규칙에 맞게 정규화) |
| 기타 옵션 | 사용자가 명시한 항목만 PUT 에 포함하고 나머지는 서버 디폴트에 맡깁니다. |

### Preset 추론

배포 직전에 `GET /app?limit=300` 으로 가능한 preset 마스터 목록을 받아옵니다. 세션 동안 1회 캐시.

사용자 요청 또는 repo 구조에서 preset 후보를 도출한 뒤 마스터 목록과 매칭합니다.

- 사용자 명시 ("Java", "Spring Boot", "MariaDB", "MongoDB", "PHP", "Laravel", "Rust", "Bun" 언급 등) → 마스터의 `name` / `displayName` / `categories` 와 매칭.
- repo 구조 신호 (사용자 명시가 없을 때만):
  - `package.json` → node 계열
  - `requirements.txt` / `pyproject.toml` → python 계열
  - `pom.xml` / `build.gradle` → java / springboot 계열
  - `Cargo.toml` → rust 계열
  - `composer.json` → php 계열
  - `Dockerfile` → dockerfile preset
  - 정적 프론트엔드 → web preset

후보가 마스터 목록에 없으면 사용자에게 알립니다 — "Cloudtype 이 X 를 지원하지 않습니다." 임의로 가까운 다른 preset 으로 갈아타지 마세요.

DB 가 필요한데 사용자가 종류를 명시하지 않은 경우는 합리적인 디폴트로 진행합니다 (예: `postgresql`). 완료 보고 시 선택한 종류를 명시합니다.

preset 추론은 **최초 배포 시점 한 번** 만 사용합니다. 실패 후 다른 preset 으로 갈아타는 근거로 사용하지 않습니다.

### Preset 옵션 채움

preset 이 확정되면 `GET /app/{preset}` 으로 옵션 스키마를 받습니다 (`stat.schema`, JSON Schema 형식).

- 스키마의 `required` 목록의 옵션만 PUT 의 `options` 에 채웁니다.
- 사용자가 명시한 옵션은 그대로 사용. 명시 없는 필수 옵션은 스키마의 `default` 값을, `default` 가 없으면 합리적인 자동 생성 값 (예: `*password*` 류는 무작위 강한 문자열) 을 채웁니다.
- 필수가 아닌 옵션은 서버 디폴트에 맡깁니다.
- 스키마에 없는 옵션을 LLM 상식으로 추가하지 않습니다.

비밀번호 / 시크릿류 옵션은 자동 생성 후 stage secret store 에 저장하고 deployment env 에서는 `secret` 참조로 연결합니다. PUT 페이로드에 평문으로 넣지 않습니다.

---

## 🛂 사전 점검

배포 전 같은 stage 에 동일 이름의 deployment 가 이미 존재하는지 확인합니다.

- 존재하지 않으면 → 그대로 배포 진행
- 존재하면 → **배포를 중단하고 사용자에게 확인**

  > "이미 같은 이름의 서비스(`<name>`)가 존재합니다. 이 서비스에 재배포할까요, 아니면 다른 이름으로 새로 만들까요?"

  사용자 결정 후 진행합니다.

---

## 🚀 배포 절차

1. 최소 페이로드로 PUT
   ```jsonc
   {
     "request": [{
       "name": "<deployment-name>",
       "app": "<preset.config[0].app>",
       "context": {
         "git": {"url": "<repo-url>", "branch": "<branch>"},
         "preset": "<preset-name>"
       }
     }],
     "owner": "<uid>"
   }
   ```
2. **PUT 성공은 요청 접수일 뿐이며 완료가 아닙니다.**
3. 빌드 / 실행 상태를 확인합니다.
   - `building` 은 **빌드 진행 중**으로 봅니다. 빌드 로그에 실패가 보일 때만 오류로 판단합니다.
   - `starting` 이 1분 이상 지속되면 실행 로그와 events 를 우선 확인합니다.
   - 실행 로그에 문제가 보이면 같은 deployment 설정을 조정합니다.
   - 실행 로그에 즉시 실패 신호가 없으면 조금 더 기다리면서 상태를 계속 봅니다.
4. 빌드 로그 스트리밍 (`wss .../project/build/logs`)
5. 빌드 성공 시 실행 로그 스트리밍 (`wss .../project/logs`)
6. **완료 조건**
   - `status == "running"`
   - `ready >= 1`
   - `entrypoints[]` 에 HTTP URL 존재
   - 해당 URL 에 HTTP GET 수행 시 2xx / 3xx 응답
7. ready 상태와 entrypoint URL 을 사용자에게 보고
8. `entrypoints` 가 먼저 생겨도 `running` 과 `ready >= 1` 전에는 완료로 보지 않습니다.

---

## 🔁 실패 대응 (핵심)

**같은 deployment** 의 빌드/실행 로그와 K8s events 만 다룹니다.

1. **로그 확인**
   - `GET .../deployment/{name}/stat` — 현재 상태
   - `GET .../stage/{stage}/events?deployment={name}` — K8s events
   - 빌드 단계 의심 시 `wss .../project/build/logs`
   - 실행 단계 의심 시 `wss .../project/logs`

2. **상태별 판단**
   - `building` 이 지속되더라도 기본적으로 **빌드 진행 중**으로 봅니다.
   - `building` 을 오류로 판단하는 시점은 **빌드 로그에 실패가 확인될 때**입니다.
   - `starting` 이 1분 이상 지속되면 실행 로그와 events 를 우선 확인합니다.
   - 실행 로그에 오류가 명확하면 같은 deployment 설정만 조정합니다.
   - 실행 로그에 즉시 실패 신호가 없으면 조금 더 기다리면서 상태를 계속 봅니다.

3. **원인이 Cloudtype 설정에서 명확한 경우**
   - 변경 사유와 내용을 사용자에게 한 줄로 보고
   - **같은 deployment 에 같은 PUT 을 다시 호출** (옵션만 조정)
   - 예: `docbase: "/dist"` 추가, `options.build: "npm run build"` 명시, `options.healthz` 변경 등

4. **원인이 코드 측이거나 불명확한 경우**
   - 위치와 수정 방향을 안내합니다 ("이 부분에 `localhost` 가 하드코딩되어 있습니다").
   - 사용자가 코드 수정을 명시적으로 요청한 경우에만 수정하고 재배포합니다.

5. **자동 재시도는 같은 처방으로 최대 3회**
   - "같은 처방" 의 정의: 동일 deployment, 동일 옵션 변경 한 묶음.
   - 처방을 바꾸는 행위(다른 preset, 새 deployment, Dockerfile 추가 등)는 재시도가 아니라 새 결정이며, 반드시 사용자 승인이 필요합니다.

6. **3회 이후에도 실패하면**
   - 사용자에게 상황을 보고하고 결정을 기다립니다.
   - "동일한 패턴으로 3회 연속 실패했습니다. 코드 수정 또는 운영 채널 문의가 필요해 보입니다."

---

## ⛔ 자동으로 분기하지 않는 결정

다음은 모두 **우회 또는 코드 수정 결정** 으로 간주하며, 사용자에게 옵션을 제시할 수 있되 **진행은 사용자 승인 후에만** 합니다.

- 다른 preset 으로 갈아타기 (`web` → `dockerfile` 등)
- Dockerfile 을 새로 작성하여 추가
- 새 deployment 이름으로 별도 서비스 생성
- 외부 이미지(`container` preset)로 대체

원칙: 실패는 **같은 deployment 의 같은 preset 안에서** 해결을 시도합니다.

---

## 🌐 멀티 서비스 (frontend + backend + DB 등)

각 서비스에 대해 위 배포 절차를 따로 적용합니다.

- 같은 stage 내부 통신: deployment name 이 hostname 으로 동작합니다. (예: 백엔드가 `postgresql:5432` 로 접속)
- 민감 env 는 stage 시크릿 store 에 저장한 뒤 참조합니다.
  - 저장: `PUT .../stage/{stage}/secret` body `{secrets: {...}, merge: true}`
  - 참조: deployment 의 env 항목을 `{"name": "<ENV>", "secret": "<key>"}` 형태로 작성
  - 키 이름이 `*PASSWORD*` / `*SECRET*` / `*TOKEN*` / `*KEY*` / `*PWD*` 등 민감 패턴이면 자동으로 시크릿 이전을 제안합니다.

---

## 🧰 GitHub 연동

이미 Cloudtype ↔ GitHub 연동이 되어 있는 상태를 전제합니다.

- 배포에 직접 사용: `context.git.url` 과 `branch` 를 그대로 PUT (public / private 무관)
- repo 또는 브랜치 조회: `/oauth/github/has`, `/oauth/github/accounts`, `/oauth/github/repository/{installationId}`, `/oauth/github/repository/{installationId}/{repo}/branch`
- 연동 설정 변경(설치 / 해제 / 토큰 갱신 등)은 수행하지 않습니다.

---

## 🔐 인증

```
Authorization: Bearer <CLOUDTYPE_API_KEY>
```

API 키는 JWT 입니다. 발급은 사용자가 Cloudtype 콘솔에서 직접 수행합니다.

---

## 📚 참조 자료

일반 배포는 본 문서(SKILL.md) 만으로 완결됩니다. 아래 자료는 **해당 상황이 실제로 발생했을 때만** 열어봅니다.

- `API_SPEC.md` — 본 문서에 없는 엔드포인트/필드를 다뤄야 할 때
- `reference/state-machine.md` — 상태 전이가 명확하지 않을 때
- `reference/diagnose-patterns.md` — 빌드/실행 실패 진단에서 옵션 조정 방향이 모호할 때

진단 패턴은 본 문서의 의사결정 기반이 아닌 **참조용 사례 모음**입니다. 본 문서의 절차(로그 확인 → 같은 deployment 설정 조정)가 우선이며, 패턴은 옵션 조정 방향을 좁히는 데 활용합니다.

---

## 🧪 동작 확인

```bash
bash scripts/verify.sh
```

- `CLOUDTYPE_API_KEY` 환경변수 존재 여부
- `/auth` 호출로 인증 동작 확인
- 사용자의 스페이스 정보 (uid, scope, role) 조회 가능 여부

---

## 🛠️ Scripts (참고)

```
scripts/
├── verify.sh                # 환경/인증 검증
├── cloudtype_client.py      # HTTP 래퍼 (stdlib only)
├── cloudtype_actions.py     # project / deploy / start / stop 등 CLI
└── cloudtype_logs.py        # WebSocket 로그 스트리밍 CLI
```
