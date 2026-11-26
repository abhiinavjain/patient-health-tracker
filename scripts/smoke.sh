#!/usr/bin/env bash
# End-to-end smoke test of the running stack (docker compose up + seed).
#   WEB=http://localhost:3000 API=http://localhost:8000 ./scripts/smoke.sh
set -euo pipefail
WEB=${WEB:-http://localhost:3000}
API=${API:-http://localhost:8000}
PASSWORD=${SEED_PASSWORD:-demo-password-123}
JAR=$(mktemp); trap 'rm -f "$JAR" "$JAR.c"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "  ok  $*"; }

for i in $(seq 1 60); do curl -sf "$API/health" >/dev/null && curl -sf -o /dev/null "$WEB/login" && break; sleep 2; done
curl -sf "$API/health" | grep -q readmission_30d || fail "API health / models not loaded"; ok "API healthy, models loaded"

code=$(curl -s -o /dev/null -w '%{http_code}' "$WEB/dashboard")
[ "$code" = 307 ] || fail "signed-out /dashboard should redirect (got $code)"; ok "signed-out users are redirected to /login"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$WEB/api/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"doctor1@demo.pht\",\"password\":\"wrong-password\"}")
[ "$code" = 401 ] || fail "bad password should be 401 (got $code)"; ok "wrong password rejected"

curl -sf -c "$JAR" -X POST "$WEB/api/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"doctor1@demo.pht\",\"password\":\"$PASSWORD\"}" | grep -q '"role":"clinician"' || fail "clinician login"
[ "$(grep -c '^#HttpOnly_.*pht_' "$JAR")" = 2 ] || fail "auth cookies must be httpOnly"; ok "login sets two httpOnly cookies"

n=$(curl -sf -b "$JAR" "$WEB/api/proxy/patients?limit=200" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
[ "$n" -gt 0 ] || fail "clinician sees no patients"; ok "proxy returns $n patients on the clinician's panel"

pid=$(curl -sf -b "$JAR" "$WEB/api/proxy/patients?limit=1" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["id"])')
curl -sf -b "$JAR" "$WEB/api/proxy/patients/$pid/risk" | python3 -c '
import sys, json
r = json.load(sys.stdin); assert {x["model"] for x in r} == {"readmission_30d", "diabetes_risk", "cvd_risk"}, r' \
  || fail "risk endpoint"; ok "risk scores returned for all three models"

curl -sf -b "$JAR" -X POST "$WEB/api/proxy/patients/$pid/notes/extract" -H 'Content-Type: application/json' \
  -d '{"note":"Known HTN. BP 150/94. Start amlodipine 5 mg OD. Review in 2 weeks."}' | python3 -c '
import sys, json
r = json.load(sys.stdin); d = r["draft"]
assert r["extractor"].startswith("local"), r
assert any(o["code"] == "bp_systolic" and o["value"] == 150 for o in d["observations"]), d
assert d["follow_up_date"], d' || fail "note extraction"; ok "local note extraction produces a draft"

for page in /dashboard /patients "/patients/$pid" /schedule; do
  code=$(curl -s -b "$JAR" -o /dev/null -w '%{http_code}' "$WEB$page")
  [ "$code" = 200 ] || fail "$page returned $code"
done; ok "clinician pages render"

code=$(curl -s -o /dev/null -w '%{http_code}' "$WEB/api/proxy/auth/me")
[ "$code" = 401 ] || fail "proxy without cookie should be 401 (got $code)"; ok "proxy rejects requests without a session"

curl -sf -c "$JAR.c" -X POST "$WEB/api/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"admin@demo.pht\",\"password\":\"$PASSWORD\"}" >/dev/null
code=$(curl -s -b "$JAR.c" -o /dev/null -w '%{http_code}' "$WEB/api/proxy/patients/$pid")
[ "$code" = 403 ] || fail "admin must not open charts (got $code)"; ok "admin cannot open individual charts"

echo "smoke test passed"
