# Cloudtype Skill

다른 에이전트(Claude Code, Cursor, OpenClaw 등) 에 얹어
**GitHub 저장소를 Cloudtype 에 배포하고, 실패 시 같은 deployment 의 로그와 설정만으로 해결을 시도**하는 스킬 패키지입니다.

설계 원칙은 단순합니다.

- 배포는 본질적으로 "최소 페이로드 PUT" 한 번
- 실패하면 **같은 deployment** 의 로그를 보고 옵션만 조정
- 다른 preset 으로 갈아타거나 새 서비스를 만드는 우회는 사용자 승인 후에만
- 소스코드 수정은 위치/방향만 안내, 직접 수행하지 않음

자세한 정책은 [`SKILL.md`](./SKILL.md) 를 참조합니다.

## 구성

```
cloudtype/
├── SKILL.md                  # 에이전트가 따르는 정책/흐름 (진입점)
├── API_SPEC.md               # Cloudtype API 명세
├── reference/
│   ├── diagnose-patterns.md  # 빌드/실행 오류 패턴 (보조 자료)
│   └── state-machine.md      # deployment 상태 머신
└── scripts/
    ├── verify.sh             # 환경/인증 검증
    ├── cloudtype_client.py   # HTTP 래퍼 (stdlib only)
    ├── cloudtype_actions.py  # CLI: project / deploy / start / stop / ...
    └── cloudtype_logs.py     # CLI: build / run / attach 로그 스트리밍 (websockets)
```

## 환경변수

| 이름                  | 용도                                            |
| --------------------- | ----------------------------------------------- |
| `CLOUDTYPE_API_KEY`   | API 키 (Bearer JWT) **— 필수**                  |
| `CLOUDTYPE_API_BASE`  | HTTP base URL (기본 `https://api.cloudtype.io`) |
| `CLOUDTYPE_WS_BASE`   | WS base URL (기본 `wss://api.cloudtype.io`)     |

## 빠른 검증

```bash
bash cloudtype/scripts/verify.sh
```

## CLI 사용 예

```bash
# 0. 인증 확인
python3 cloudtype/scripts/cloudtype_actions.py whoami

# 1. project 가 없는 경우 자동 생성하면서 web 배포
python3 cloudtype/scripts/cloudtype_actions.py deploy \
  --scope myspace --project demo --stage main \
  --name web --app web --preset html \
  --git https://github.com/<owner>/<repo>.git --branch main \
  --option docbase=/ --option spa=true --option ports=8080 \
  --ensure-project

# 2. 빌드 로그 스트리밍
python3 cloudtype/scripts/cloudtype_logs.py build \
  --scope myspace --project demo --stage main --deployment web

# 3. 시크릿 저장 (기본 merge=true)
python3 cloudtype/scripts/cloudtype_actions.py put-secrets \
  --scope myspace --project demo --stage main \
  --secret ***
```

## 정책 요약 (자세한 내용은 SKILL.md)

- **실패는 같은 deployment 안에서** 해결을 시도합니다. 다른 preset 으로 갈아타거나 새 서비스를 만드는 우회는 사용자 승인 후에만 수행합니다.
- 사용자에게 세세한 사항을 일일이 묻지 않습니다. 다음은 자동 추론합니다.
  - branch: 명시 없으면 `main`
  - project: 명시 없으면 repo 이름 (없으면 생성)
  - stage: 명시 없으면 `main`
  - deployment 이름: 명시 없으면 repo 이름 (식별자 규칙에 맞게 정규화)
  - preset: repo 구조에서 한 번 추론 (초기 1회)
- 같은 이름의 deployment 가 이미 존재하면 배포를 중단하고 사용자에게 확인합니다.
- 빌드/실행 로그로 원인이 명확한 Cloudtype 설정 수정은 사용자에게 보고한 뒤 같은 PUT 으로 재호출합니다.
- 자동 재시도는 **같은 처방으로 최대 3회** 입니다.
- **시크릿 조회 / 삭제(Service / Project / Stage) 는 UI 에서** 수행합니다.
- 리소스(`cpu` / `memory` / `disk` / `replicas` / `spot`) 자동 조정은 수행하지 않습니다.
- Dockerfile 자동 생성/주입은 수행하지 않습니다. 사용자가 dockerfile preset 을 명시한 경우에만 사용합니다.

## 의존성

- Python 3.10 이상
- `cloudtype_logs.py` 만 `websockets` 패키지가 필요합니다: `pip install websockets`
- 그 외는 표준 라이브러리만 사용합니다.

## 다른 에이전트에 적용하는 방법

1. 이 `cloudtype/` 디렉토리를 에이전트의 스킬 디렉토리 또는 작업 디렉토리에 복사합니다.
2. 환경변수 `CLOUDTYPE_API_KEY` 를 설정합니다.
3. 에이전트의 시스템 프롬프트 또는 도구 설명에 "Cloudtype 관련 작업 시 `cloudtype/SKILL.md` 정책을 따른다" 고 명시합니다.
4. CLI 가 필요하면 `python3 cloudtype/scripts/cloudtype_actions.py ...` 형태로 호출합니다.
