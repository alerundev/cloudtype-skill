# Deployment Lifecycle — State Machine

> 사용자가 자주 헷갈리는 상태 흐름. v1 스킬의 진단 결정 트리 기반.
> 운영자(james_cloud17) 검증, 2026-05-26.

## 🔄 정상 흐름

```
[create/redeploy 트리거]
        ↓
   building       ← 빌드 단계 (Docker BuildKit 실행, 이미지 푸시)
        ↓
   starting       ← 컨테이너 시작 + readiness probe 통과 대기
        ↓
   running ✅      ← 1/N replicas ready
```

## ❌ 실패 흐름

### 1. 빌드 실패 → 즉시 error
```
building → error  (빌드에서 깨지면 starting까지 못 감)
```
→ **빌드 로그**를 본다. 마지막 ❌ 또는 `Build job failed` 라인 위주.

### 2. starting에서 멈춤 (가장 흔한 사용자 질문!)
```
building → starting → ... (오래 멈춤)
```

증상: 빌드는 성공했는데 `running`으로 안 넘어감. 분 단위, 심하면 무한대.

진짜 가능성 (우선순위 순):

| 의심 | 어디서 확인 | 대표 시그널 |
|---|---|---|
| 컨테이너가 즉시 죽음 (BackOff) | K8s events + 실행 로그 | `BackOff restarting failed container`, Node `Error:`, Python `Traceback` |
| Port 미스매치 | settings + 실행 로그 | 배포 설정 port=3000인데 앱은 8080에서 listen → readiness 영원히 실패 |
| 앱이 listen을 시작 못 함 | 실행 로그 | DB 연결 실패, env var 누락, 의존성 누락 |
| Readiness probe 경로 잘못됨 | settings | `/health` 인데 앱엔 그 경로 없음 |
| 이미지 풀 실패 | K8s events | `ImagePullBackOff`, `ErrImagePull` |
| 리소스 부족 | K8s events | `0/N nodes available`, `OutOfMemory` |
| FailedCreatePodSandBox | K8s events | 네트워크 셋업 실패 (보통 일시적, 재시도하면 풀림) |

### 3. running → error / stopped 전환

런타임 크래시 또는 OOM:
- 실행 로그 마지막 라인 + K8s events `OOMKilled`, `BackOff`

## 🩺 진단 결정 트리

```
status?
├── building       → 빌드 로그 따라가기 (보통 자연스럽게 진행)
├── error          → 빌드 로그 마지막 ❌ 라인 분석
├── starting (오래)→ 
│   ├── K8s events에 BackOff 있나?  → 실행 로그에서 크래시 원인
│   ├── K8s events에 ImagePullBackOff? → 이미지 레지스트리 권한/존재 확인
│   ├── FailedCreatePodSandBox 반복? → 잠깐 대기 후 재시도 (일시적)
│   ├── pending? → 노드 리소스 부족 (`0/N nodes available`)
│   └── 별 이벤트 없음 → port/readiness 미스매치 의심
├── running but 0/N → readiness probe 실패. 실행 로그 보고 앱이 정말 살았는지
└── stopped        → 사용자가 stop 했거나 정책상 멈춤
```

## 🔌 readiness vs liveness (사용자가 자주 모름)

Cloudtype은 K8s를 쓰니까:
- **Readiness** = "이 컨테이너가 트래픽 받을 준비 됐어?" — 실패하면 ready=0 (running 안 됨)
- **Liveness** = "살아있어?" — 실패하면 컨테이너 재시작 (BackOff 원인)

대부분의 `starting → 멈춤` 케이스는 readiness probe 미통과 또는 컨테이너 즉시 크래시.

## 📋 에이전트가 따라야 할 진단 절차 (v1)

1. `GET .../deployment/{name}` → 현재 status, ready/replicas
2. **status에 따라 분기:**
   - `building` → build logs stream
   - `error` → build logs (last lines)
   - `starting` (시간 측정 필요) → 이벤트 + 실행 로그 동시 확인
   - `running` but ready=0/N → readiness/port 의심
3. `GET .../events?deployment={name}` → K8s 이벤트 패턴 매칭
4. WS `/project/logs` → 마지막 50~200줄 받기, 에러 패턴 스캔
5. WS `/project/build/logs` → 필요시 (build 단계 의심될 때)
6. 종합해서 **원인 → 처방** 형태로 사용자에게 안내

## 🎯 핵심 원칙 — 스킬의 역할과 한계

**v1 스킬은 "단서를 깔끔하게 노출" 까지**가 역할.
"코드 이렇게 고치세요" 같은 코드 처방은 스킬이 하지 않는다.

### 왜?
스킬이 붙는 상대 에이전트가 두 종류:

1. **주로 "바이브 코딩" 에이전트** (Claude Code, Cursor 등) — 자기가 짠 코드의
   전체 컨텍스트를 이미 가지고 있음. 스킬이 "이 에러가 났다"만 알려주면,
   자기 코드를 보고 와서 바로 고친다.
2. **운영 도움을 받는 사용자** (자기 코드 아님) — 이 경우에도 "어디서 어떤
   에러가 나는지"를 정확히 알려주면 그 다음은 다른 도구나 운영자가 처리.

즉 **스킬이 아는 건 "클라우드타입 쪽의 상태"**이고,
**스킬이 모르는 건 "사용자 코드의 내용"**이다.

### 재해석된 원칙

- **로그 라인 인용은 "최소 필요 분량"** — 핵심 에러 메시지 텍스트 자체는
  중요(`Cannot find module ...`, `connection refused`, `OOMKilled` 등).
  결정 트리 분기에 근거가 됨.
- **결정 트리에서 분기점 명시** — "status=starting + BackOff event + Error log
  패턴" 같이 구체적 단서 조합.
- **코드 처방은 권장하지 않음** — "package.json 에 prestart 추가하세요" 같은
  있면 이건 부르는 코딩 에이전트의 몫·. 스킬은 "빌드 결과물에 dist/...
  없음" 까지만.
- **하지만 클라우드타입 배포 설정 변경은 스킬이 직접 함** —
  build command, install command, env, ports, replicas, resources 등은
  PUT .../deployment 로 동적 수정 가능. 이건 **소스코드 아닌
  "클라우드타입 쪽 설정"** 이라 스킬이 처리해도 됨.
  예: "`Cannot find module .../dist/...` + spec의 build 명령 비어있음"
  패턴이면, 사용자에게 "배포 설정의 build command에 `npm run build`
  추가해서 재배포해 드릴까요?" 제안 → 동의하면 스킬이 직접 적용.
- **추측이면 추측이라고 말함** — confidence 명시.

### 대신 제공해야 할 것

```python
# diagnose() 명령의 이상적 출력
{
  "status": "starting",
  "duration_in_state": "3m 12s",   # 얼마나 멈춰 있는지
  "replicas": "0/1",
  "last_build": {
    "id": "mpm...",
    "result": "success",
    "commit": "2a9e0c5",
    "image_digest": "sha256:9eb0fc..."
  },
  "recent_events": [                # K8s events, 액션가능한 것만
    {"reason": "BackOff", "count": 5, "message": "Back-off restarting failed container"},
    {"reason": "Pulled", "ok": true}
  ],
  "last_runtime_log_lines": [        # 핵심 에러 부분
    "Error: Cannot find module '/app/dist/mcp-server.js'",
    "code: 'MODULE_NOT_FOUND'"
  ],
  "likely_cause_pattern": "container_crash_loop",   # 패턴 레이블만
  "confidence": "high"
  # → 이걸 받은 코딩 에이전트가 자기 코드 컨텍스트랑 합쳐서 추론/수정
}
```

즉 **원인 패턴 레이블은 붙이되, "당신의 코드를 이렇게 고치세요"는 하지 않는다.**
그게 이 스킬을 어떤 에이전트가 쓰더라도 맞게 동작하게 하는 방법.
