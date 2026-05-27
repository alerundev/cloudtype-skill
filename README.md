# Cloudtype Skill

이 디렉토리는 다른 에이전트(예: Claude Code, Cursor, OpenClaw)에 그대로 얹어
**GitHub 저장소 → Cloudtype 배포 → 로그/진단 → 재배포** 전 과정을 자연어로
제어할 수 있게 해주는 스킬 패키지다.

## 구성

```
cloudtype/
├── SKILL.md                  # 에이전트가 따르는 정책/흐름 정의 (진입점)
├── API_SPEC.md               # Cloudtype API 명세 요약
├── reference/
│   ├── diagnose-patterns.md  # 빌드/실행 오류 진단 보조 문서
│   └── state-machine.md      # deployment 상태 머신 정리
└── scripts/
    ├── verify.sh             # 환경/인증 검증
    ├── cloudtype_client.py   # HTTP 래퍼 (표준 라이브러리만 사용)
    ├── cloudtype_actions.py  # CLI: project/deploy/start/stop/...
    └── cloudtype_logs.py     # CLI: build/run/attach 로그 스트리밍 (websockets)
```

## 환경변수

| 이름                     | 용도                                              |
| ------------------------ | ------------------------------------------------- |
| `CLOUDTYPE_API_KEY`      | Cloudtype API 키 (Bearer JWT)                    |
| `CLOUDTYPE_API_BASE`     | HTTP base URL (기본 `https://api.cloudtype.io`)   |
| `CLOUDTYPE_WS_BASE`      | WS base URL (기본 `wss://api.cloudtype.io`)       |

> 호환 목적으로 `CLOUDTYPE_TESTAPIKEY` 도 폴백으로 인식한다. 두 값이 모두 있으면
> `CLOUDTYPE_API_KEY` 가 우선이다.

## 빠른 검증

```bash
bash cloudtype/scripts/verify.sh
```

## CLI 빠른 예

```bash
# 0. 인증 확인
python3 cloudtype/scripts/cloudtype_actions.py whoami

# 1. project 가 없으면 자동 생성하면서 web 배포
python3 cloudtype/scripts/cloudtype_actions.py deploy \
  --scope <scope> --project <project> --stage main \
  --name web --app web --preset html \
  --git https://github.com/<owner>/<repo>.git --branch main \
  --option docbase=/ --option spa=true --option ports=8080 \
  --ensure-project

# 2. 빌드 로그 스트리밍
python3 cloudtype/scripts/cloudtype_logs.py build \
  --scope <scope> --project <project> --stage main --deployment web

# 3. 시크릿 저장 (기본 merge=true)
python3 cloudtype/scripts/cloudtype_actions.py put-secrets \
  --scope <scope> --project <project> --stage main \
  --secret DB_PASSWORD=<value>
```

## 정책 요약 (자세한 것은 `SKILL.md`)

- 배포만 하는 경우: **소스코드 직접 수정 금지**, 수정 방향만 안내.
- 코드 작성/수정 권한이 있는 경우: 수정안을 보여주고 **허락받은 뒤** 수정하고 재배포.
- 빌드/실행 로그로 원인이 명확한 Cloudtype 설정 수정은 재배포 단계에서 추가 확인 없이 반영.
- 자동 재시도 **최대 3회**. 실패가 지속되면 운영자에게 문의를 남기도록 안내.
- **시크릿 조회는 UI**에서. 스킬은 조회하지 않는다.
- **삭제(Service/Project/Stage)는 UI**에서. 스킬 자동 액션 금지.
- 리소스(`cpu`/`memory`/`disk`/`replicas`/`spot`) 자동 조정 금지.

## 의존성

- Python 3.10 이상
- `cloudtype_logs.py` 만 `websockets` 패키지가 필요하다: `pip install websockets`
- 나머지는 표준 라이브러리만 사용한다.

## 다른 에이전트에 얹는 방법

1. 이 `cloudtype/` 디렉토리를 에이전트의 스킬 디렉토리(또는 작업 디렉토리)에 복사한다.
2. 환경변수 `CLOUDTYPE_API_KEY` 를 설정한다.
3. 에이전트 시스템 프롬프트나 도구 설명에 "Cloudtype 작업은 `cloudtype/SKILL.md` 정책을 따른다"고 명시한다.
4. CLI가 필요하면 `python3 cloudtype/scripts/cloudtype_actions.py ...` 를 호출한다.
