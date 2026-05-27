# Cloudtype Skill

이 디렉토리는 다른 에이전트(Claude Code, Cursor, OpenClaw 등)에 그대로 얹어
**GitHub 저장소 → Cloudtype 배포 → 로그/진단 → 재배포** 전 과정을 자연어로 제어할 수 있도록 하는 스킬 패키지입니다.

## 구성

```
cloudtype/
├── SKILL.md                  # 에이전트가 따르는 정책/흐름 정의 (진입점)
├── API_SPEC.md               # Cloudtype API 명세
├── reference/
│   ├── diagnose-patterns.md  # 빌드/실행 오류 진단 보조 문서
│   └── state-machine.md      # deployment 상태 머신 정리
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
  --secret DB_PASSWORD=<value>
```

## 정책 요약 (자세한 내용은 SKILL.md)

- 배포만 수행하는 경우: **소스코드 직접 수정 금지**, 안내만 제공합니다.
- 코드 작성 권한이 있는 경우: 수정안을 제시하고 사용자 승인 후 수정 → 재배포합니다.
- 빌드/실행 로그로 원인이 명확한 Cloudtype 설정 수정은 추가 확인 없이 반영합니다.
- 자동 재시도는 **최대 3회**. 실패가 지속되면 사용자에게 운영 채널 문의를 안내합니다.
- **시크릿 조회는 UI 에서** 수행합니다. 스킬은 조회하지 않습니다.
- **삭제(Service / Project / Stage) 는 UI 에서** 수행합니다. 스킬은 자동으로 수행하지 않습니다.
- 리소스(`cpu` / `memory` / `disk` / `replicas` / `spot`) 자동 조정은 수행하지 않습니다.

## 의존성

- Python 3.10 이상
- `cloudtype_logs.py` 만 `websockets` 패키지가 필요합니다: `pip install websockets`
- 그 외는 표준 라이브러리만 사용합니다.

## 다른 에이전트에 적용하는 방법

1. 이 `cloudtype/` 디렉토리를 에이전트의 스킬 디렉토리(또는 작업 디렉토리)에 복사합니다.
2. 환경변수 `CLOUDTYPE_API_KEY` 를 설정합니다.
3. 에이전트의 시스템 프롬프트나 도구 설명에 "Cloudtype 관련 작업 시 `cloudtype/SKILL.md` 정책을 따른다"고 명시합니다.
4. CLI 가 필요하면 `python3 cloudtype/scripts/cloudtype_actions.py ...` 형태로 호출합니다.
