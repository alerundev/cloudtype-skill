# Deployment Lifecycle — State Machine

> Cloudtype deployment의 상태 흐름과 에이전트의 진단 절차 정리.
> SKILL.md의 정책과 함께 읽는 보조 문서.

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

### 2. starting에서 멈춤
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

## 🔌 readiness vs liveness

Cloudtype은 K8s 기반이라 두 probe를 함께 본다:

- **Readiness** — “이 컨테이너가 트래픽 받을 준비 됐어?” 실패하면 ready=0 (running 안 됨)
- **Liveness** — “살아있어?” 실패하면 컨테이너 재시작 (BackOff 원인)

대부분의 `starting → 멈춤`은 readiness probe 미통과 또는 컨테이너 즉시 크래시.

## 📋 진단 절차

1. `GET .../deployment/{name}` → 현재 status, ready/replicas 확인
2. status에 따라 분기:
   - `building` → build logs 스트리밍
   - `error` → build logs 마지막 라인 분석
   - `starting`(시간 측정 필요) → events + 실행 로그 동시 확인
   - `running` but ready=0/N → readiness/port 의심
3. `GET .../events?deployment={name}` → K8s 이벤트 패턴 매칭
4. WS `/project/logs` → 마지막 50~200줄, 에러 패턴 스캔
5. WS `/project/build/logs` → 필요 시 (빌드 단계 의심)
6. 종합해 **원인 → 조치 옵션** 형태로 정리

## 🎯 스킬의 역할과 한계

이 스킬은 **Cloudtype 쪽 상태와 설정을 다루는 도구**다. 사용자의 소스코드를 보지 않으며,
코드 수정은 SKILL.md의 정책에 따른다.

- **Cloudtype 설정 변경(예: `options.build`, `options.ports`, env, `docbase`, healthz, replicas 등)**
  은 로그/상태 근거가 명확하면 스킬이 직접 수정 후 재배포한다.
- **코드 수정**은
  - 코드 작성 권한이 포함된 워크플로우라면 **수정안을 제시하고 허락을 받은 뒤** 반영하고 재배포한다.
  - 배포만 담당하는 워크플로우라면 **수정 방향만 안내**하고 코드에 직접 손대지 않는다.
- 위 과정을 거치고도 동일 실패가 지속되면 운영자에게 문의를 남기도록 안내한다.

## 진단 결과 권장 출력 (JSON 예시)

```jsonc
{
  "status": "starting",
  "duration_in_state": "3m 12s",
  "replicas": "0/1",
  "last_build": {
    "id": "mpm...",
    "result": "success",
    "commit": "2a9e0c5",
    "image_digest": "sha256:9eb0fc..."
  },
  "recent_events": [
    {"reason": "BackOff", "count": 5, "message": "Back-off restarting failed container"},
    {"reason": "Pulled", "ok": true}
  ],
  "last_runtime_log_lines": [
    "Error: Cannot find module '/app/dist/mcp-server.js'",
    "code: 'MODULE_NOT_FOUND'"
  ],
  "likely_cause_pattern": "container_crash_loop",
  "confidence": "high",
  "suggested_settings_change": {
    "options.build": "npm run build"
  }
}
```

- `likely_cause_pattern` / `confidence` 로 분류 근거를 드러내고,
- `suggested_settings_change` 처럼 **Cloudtype 설정 변경 제안**은 함께 제공할 수 있다.
- 코드 변경이 필요한 경우엔 위치/이유만 명확히 적고, 적용 권한 여부에 따라 안내 또는 수정 후 재배포로 이어진다.
