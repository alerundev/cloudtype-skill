# Deployment Lifecycle — State Machine

배포(deployment)의 상태 흐름과, 각 상태에서의 진단 절차를 정리한 보조 문서입니다.
SKILL.md의 진단 결정 트리가 참조하는 기반 자료입니다.

## 정상 흐름

```
[create / redeploy 트리거]
        ↓
   building       — 빌드 단계 (이미지 빌드 및 푸시)
        ↓
   starting       — 컨테이너 시작 및 readiness probe 통과 대기
        ↓
   running        — 1/N replicas ready
```

## 실패 흐름

### 1. 빌드 실패

```
building → error
```

빌드 단계에서 실패하면 `starting`으로 진행하지 않고 곧바로 `error` 상태가 됩니다.
이 경우 **빌드 로그**의 마지막 실패 라인(`Build job failed` 등)부터 확인합니다.

### 2. starting 상태에서 지연 또는 정체

```
building → starting → ... (오랫동안 멈춰 있음)
```

빌드는 성공했지만 `running`으로 넘어가지 않는 상태입니다.
가능한 원인은 다음과 같습니다(체크 순서 권장):

| 원인 | 확인 위치 | 대표 시그널 |
|---|---|---|
| 컨테이너가 즉시 종료됨 (BackOff) | K8s events + 실행 로그 | `BackOff restarting failed container`, 런타임 스택트레이스 |
| 포트 불일치 | 배포 설정 + 실행 로그 | 설정 port 와 앱이 listen 하는 포트가 다름 → readiness 실패 |
| 앱이 listen 을 시작하지 못함 | 실행 로그 | DB 연결 실패, 필수 환경변수 누락, 의존성 문제 등 |
| Readiness probe 경로 오류 | 배포 설정 | 설정 경로가 앱에 존재하지 않음 |
| 이미지 풀 실패 | K8s events | `ImagePullBackOff`, `ErrImagePull` |
| 노드 리소스 부족 | K8s events | `0/N nodes available`, `OutOfMemory` |
| Pod Sandbox 생성 실패 | K8s events | `FailedCreatePodSandBox` (일시적인 경우 재시도로 해소되는 사례가 있음) |

### 3. running 상태에서의 전환

```
running → error 또는 stopped
```

런타임 크래시 또는 OOM 등이 원인일 수 있습니다.
실행 로그의 마지막 라인과 K8s events(`OOMKilled`, `BackOff` 등)를 함께 확인합니다.

## 진단 결정 트리

```
status?
├── building       → 빌드 로그 추적
├── error          → 빌드 로그 마지막 실패 라인 분석
├── starting (지연)
│   ├── BackOff 이벤트 존재          → 실행 로그에서 크래시 원인 분석
│   ├── ImagePullBackOff             → 이미지 경로/권한 확인
│   ├── FailedCreatePodSandBox 반복   → 잠시 대기 후 재시도 권장
│   ├── pending                      → 노드 리소스 부족 (`0/N nodes available`)
│   └── 특이 이벤트 없음             → 포트 또는 readiness 경로 불일치 의심
├── running, ready 0/N → readiness probe 실패. 실행 로그로 앱 상태 확인
└── stopped            → 사용자가 정지했거나 정책에 의해 중단된 상태
```

## Readiness vs Liveness

Cloudtype은 Kubernetes 기반으로 동작하며, 두 종류의 헬스체크가 존재합니다.

- **Readiness probe** — 컨테이너가 트래픽을 받을 준비가 되었는지 확인합니다.
  실패하면 ready 카운트가 올라가지 않아 `running`으로 전환되지 않습니다.
- **Liveness probe** — 컨테이너가 살아 있는지 확인합니다.
  실패하면 컨테이너가 재시작되며, 반복되면 `BackOff` 상태로 이어집니다.

`starting` 상태에서 정체가 일어나는 사례의 대부분은
readiness probe 미통과 또는 컨테이너 즉시 종료가 원인입니다.

## 에이전트 진단 절차

1. `GET .../deployment/{name}` — 현재 status, ready/replicas 확인
2. status 에 따라 분기:
   - `building` → 빌드 로그 스트리밍
   - `error` → 빌드 로그 마지막 라인 분석
   - `starting` (시간 측정) → K8s events + 실행 로그 동시 확인
   - `running` 인데 ready 0/N → readiness 경로 / 포트 의심
3. `GET .../stage/{stage}/events?deployment={name}` — K8s 이벤트 패턴 매칭
4. `wss .../project/logs` — 실행 로그 마지막 부분 수집 및 에러 패턴 스캔
5. `wss .../project/build/logs` — 필요 시 빌드 단계 의심 시 사용
6. 종합하여 **원인 → 처방** 형태로 사용자에게 보고

## 스킬의 역할과 한계

이 스킬의 진단 책임은 **Cloudtype 쪽 상태와 단서를 정확하게 노출**하는 것까지입니다.
사용자 소스코드의 구체적인 수정안 제시는 스킬의 역할 범위가 아닙니다.

이유는 다음 두 가지를 고려한 것입니다.

1. 이 스킬을 사용하는 상위 에이전트가 코드 작성 컨텍스트를 보유한 경우가 많습니다.
   상위 에이전트는 "이 에러가 발생했다"는 정보만 받으면 자체적으로 코드 수정이 가능합니다.
2. 코드를 직접 다루지 않는 운영 상황에서도, "어디서 어떤 에러가 나는지"가 명확하면
   사용자나 별도 도구가 후속 조치를 진행할 수 있습니다.

스킬이 다루는 것과 다루지 않는 것은 다음과 같이 구분합니다.

- **다룸**: Cloudtype 배포 설정(build/install/start 커맨드, env, ports, healthz 등)의 변경.
  로그 근거가 명확하면 사용자 확인 후 직접 PUT 으로 적용합니다.
- **다루지 않음**: 소스코드의 직접 수정. 정확한 위치와 권장 방향만 안내합니다.

### 진단 결과 권장 출력 형태

```python
{
  "status": "starting",
  "duration_in_state": "3m 12s",
  "replicas": "0/1",
  "last_build": {
    "id": "...",
    "result": "success",
    "commit": "...",
    "image_digest": "sha256:..."
  },
  "recent_events": [
    {"reason": "BackOff", "count": 5, "message": "Back-off restarting failed container"},
    {"reason": "Pulled", "ok": true}
  ],
  "last_runtime_log_lines": [
    "Error: Cannot find module '/app/dist/server.js'",
    "code: 'MODULE_NOT_FOUND'"
  ],
  "likely_cause_pattern": "container_crash_loop",
  "confidence": "high"
}
```

원인 패턴 라벨은 부여하되, 소스코드 수정안은 포함하지 않는 형태를 권장합니다.
이러한 출력은 상위 에이전트 또는 사용자가 다음 행동을 결정하기 위한 단서로 활용됩니다.
