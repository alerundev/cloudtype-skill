#!/usr/bin/env bash
# verify.sh — Cloudtype skill 환경/접근권 빠른 검증
#
# 사용법:
#   bash cloudtype/scripts/verify.sh
#
# 환경변수 (우선순위):
#   CLOUDTYPE_API_KEY      (운영용 표준)
#   CLOUDTYPE_TESTAPIKEY   (테스트/호환)
#
# 종료 코드:
#   0 = OK
#   1 = API 키 없음 또는 인증 실패
#   2 = 네트워크 문제

set -euo pipefail

API="${CLOUDTYPE_API_BASE:-https://api.cloudtype.io}"
TOK="${CLOUDTYPE_API_KEY:-${CLOUDTYPE_TESTAPIKEY:-}}"

echo "=== Cloudtype skill — environment check ==="
echo "API base : $API"
echo

if [ -z "$TOK" ]; then
  echo "❌ API key 환경변수가 없습니다 (CLOUDTYPE_API_KEY 또는 CLOUDTYPE_TESTAPIKEY)."
  exit 1
fi
echo "✅ API key 환경변수 존재 (길이: ${#TOK})"

echo
echo "=== JWT payload ==="
python3 - <<'PY' || true
import base64, json, os, sys
tok = os.environ.get('CLOUDTYPE_API_KEY') or os.environ.get('CLOUDTYPE_TESTAPIKEY') or ''
parts = tok.split('.')
if len(parts) != 3:
    print('  (not a JWT)'); sys.exit(0)
def b64d(s):
    s += '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)
try:
    p = json.loads(b64d(parts[1]))
    print(json.dumps(p, indent=2, ensure_ascii=False))
except Exception as e:
    print(f'  decode failed: {e}')
PY

echo
echo "=== /auth ==="
http=$(curl -sS -o /tmp/.cloudtype-verify.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOK" \
  -H "Accept: application/json" \
  "$API/auth") || { echo "❌ curl 실패 — 네트워크?"; exit 2; }

if [ "$http" = "200" ]; then
  echo "✅ HTTP 200 — 인증 OK"
  python3 - <<'PY'
import json
d = json.load(open('/tmp/.cloudtype-verify.json'))
print(f"  uid:      {d.get('uid')}")
print(f"  provider: {d.get('provider')}")
print(f"  scope:    {d.get('name')}")
roles = d.get('roles', [])
for r in roles:
    print(f"  role:     {r.get('target')} / {r.get('role')}")
PY
else
  echo "❌ HTTP $http — 인증 실패"
  cat /tmp/.cloudtype-verify.json || true
  exit 1
fi

rm -f /tmp/.cloudtype-verify.json
echo
echo "✅ 환경 검증 완료."
