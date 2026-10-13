#!/usr/bin/env bash
# Acceptance test for a running stack: health, a note in PostgreSQL, real local inference, then a
# full stop and start of every container to prove the note and the model survive.
#
#   ./scripts/smoke-test.sh                 # with the restart (containers are recreated)
#   ./scripts/smoke-test.sh --no-restart    # quick: no restart
#
# The HTTP checks run inside the backend container against http://web:8080, so the host needs
# only Docker and bash. The final check also confirms the published port answers from the host.

source "$(dirname "$0")/lib.sh"

RESTART=1
[ "${1:-}" = "--no-restart" ] && RESTART=0

PORT="$(env_value WEB_PORT 3000)"
BIND="$(env_value WEB_BIND 127.0.0.1)"
[ "$BIND" = "0.0.0.0" ] && BIND=127.0.0.1
SMOKE="$ROOT/scripts/smoke_test.py"

up() {
  local log
  if ! log="$(compose up -d --wait --wait-timeout 300 --pull never --no-build 2>&1)"; then
    printf '%s\n' "$log" | tail -n 20 >&2
    fail "the stack did not become healthy after the restart"
    fix "./scripts/diagnose.sh"
    exit 1
  fi
}

host_port_answers() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 5 "http://$BIND:$PORT/healthz" > /dev/null
  else
    # No curl on the host: bash can open the TCP connection itself.
    (exec 3<>"/dev/tcp/$BIND/$PORT" && printf 'GET /healthz HTTP/1.0\r\n\r\n' >&3 && grep -q "200" <&3)
  fi
}

step "Containers"
compose ps --format 'table {{.Service}}\t{{.Status}}'
for service in web backend postgres ollama; do
  state="$(compose ps --format '{{.Health}}' "$service" 2>/dev/null || true)"
  [ "$state" = "healthy" ] || { fail "$service is '${state:-not running}'"; fix "./scripts/diagnose.sh"; exit 1; }
done
ok "all four services are healthy"

step "Published port"
if host_port_answers; then ok "http://$BIND:$PORT answers from the host"
else fail "nothing answers on http://$BIND:$PORT"; fix "check WEB_BIND and WEB_PORT in .env, and the host firewall"; exit 1; fi

step "Create a note and ask the local model about it"
output="$(compose exec -T backend python - create < "$SMOKE")" || { printf '%s\n' "$output"; exit 1; }
printf '%s\n' "$output" | grep -v '^NOTE_ID='
note_id="$(printf '%s\n' "$output" | sed -n 's/^NOTE_ID=//p')"

if [ "$RESTART" -eq 1 ]; then
  step "Stop and remove every container, then start again (volumes stay)"
  compose down >/dev/null 2>&1
  info "containers removed; starting from the same images and volumes"
  up
  ok "stack is healthy again"
  step "Persistence after the restart"
  compose exec -T backend python - verify "$note_id" < "$SMOKE"
else
  compose exec -T backend python - verify "$note_id" < "$SMOKE" | grep -v "survived"
fi

step "Result"
ok "smoke test passed: notes persist and answers come from the local model"
