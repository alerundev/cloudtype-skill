# Cloudtype Skill

이 디렉토리는 다른 에이전트(예: Claude Code, Cursor, OpenClaw)에 그대로 얹어
**GitHub 저장소 → Cloudtype 배포 → 로그/진단 → 재배포** 전 과정을 자연어로
제어할 수 있게 해주는 스킬 패키지다.

## 구성

```
cloudtype/
├── SKILL.md                  # 에이전트가 따르는 정책/흐름 정의 (진입점)
├── API_SPEC.md               # 검증된 Cloudtype API 명세
├── RESUME.md                 # 작업 컨텍스트 / 진행 메모
├── reference/
│   ├── diagnose-patterns.md  # 빌드/실행 오류 진단 보조 문서
│   └── state-machine.md      # deployment 상태 머신 정리
└── scripts/
    ├── verify.sh             # 환경/인증 검증
    ├── cloudtype_client.py   # HTTP 래퍼 (stdlib only)
    ├── cloudtype_actions.py  # CLI: project/deploy/start/stop/...
    └── cloudtype_logs.py     # CLI: build/run/attach 로그 스트리밍 (websockets)
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

## CLI 빠른 예

```bash
# 0. 인증 확인
python3 cloudtype/scripts/cloudtype_actions.py whoami

# 1. project 없는 경우 자동 생성하면서 web 배포
python3 cloudtype/scripts/cloudtype_actions.py deploy \
  --scope myspace --project demo --stage main \
  --name web --app web --preset html \
  --git https://github.com/alerundev/demo-fruit-shop.git --branch main \
  --option docbase=/ --option spa=true --option ports=8080 \
  --ensure-project

# 2. 빌드 로그 스트리밍
python3 cloudtype/scripts/cloudtype_logs.py build \
  --scope myspace --project demo --stage main --deployment web

# 3. 시크릿 저장 (기본 merge=true)
python3 cloudtype/scripts/cloudtype_actions.py put-secrets \
  --scope myspace --project demo --stage main \
  --secret DB_PASSWORD=$(openssl rand -hex 12)
```

## 정책 요약 (자세한 것은 SKILL.md)

- 배포만 하는 경우: **소스코드 직접 수정 금지**, 안내만.
- 코드 작성 권한이 있는 경우: 수정안을 제시하고 **허락받은 뒤** 수정 → 재배포.
- 빌드/실행 로그로 원인이 명확한 Cloudtype 설정 수정은 추가 확인 없이 반영.
- 자동 재시도 **최대 3회**. 실패 지속 시 운영자 문의 안내.
- **시크릿 조회는 UI**에서. 스킬은 조회하지 않음.
- **삭제(Service/Project/Stage)는 UI**에서. 스킬은 자동 수행하지 않음.
- 리소스(`cpu`/`memory`/`disk`/`replicas`/`spot`) 자동 조정 금지.

## 의존성

- Python 3.10+
- `cloudtype_logs.py`만 `websockets` 패키지가 필요하다: `pip install websockets`
- 나머지는 표준 라이브러리만 사용.

## 다른 에이전트에 얹는 방법

1. 이 `cloudtype/` 디렉토리를 에이전트의 스킬 디렉토리(또는 작업 디렉토리)에 복사.
2. 환경변수 `CLOUDTYPE_API_KEY` 설정.
3. 에이전트 시스템 프롬프트나 도구 설명에 "Cloudtype 작업 시 `cloudtype/SKILL.md` 정책을 따른다"고 명시.
4. CLI가 필요하면 `python3 cloudtype/scripts/cloudtype_actions.py ...` 호출.
