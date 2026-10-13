#!/usr/bin/env bash
# Prove the offline claims against the running stack, and write the evidence to a report.
#
#   ./scripts/airgap-test.sh                        # container isolation + smoke test (any machine)
#   ./scripts/airgap-test.sh --require-offline-host # ALSO require that this host has no internet
#
# Part 1  Host. With --require-offline-host, the test fails unless this machine cannot resolve or
#         reach public hosts: run it after you disconnect the server (pull the cable, disable the
#         interface, or block egress at the firewall).
# Part 2  Containers. Whatever the host can do, backend and ollama must have no route out: DNS
#         lookups and TCP connections to public addresses fail, and `ollama pull` fails.
# Part 3  The application, under those conditions: a record is written to PostgreSQL and the local
#         model answers a question about it (the smoke test, including a full restart).

source "$(dirname "$0")/lib.sh"

STRICT=0
[ "${1:-}" = "--require-offline-host" ] && STRICT=1
REPORT="$ROOT/airgap-report-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee "$REPORT") 2>&1

printf 'Air-gap test  %s  host %s  strict-host=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(uname -n)" "$STRICT"
FAILED=0
PUBLIC_HOSTS="registry.ollama.ai ollama.com registry-1.docker.io pypi.org"
PUBLIC_IPS="1.1.1.1 8.8.8.8"

step "Part 1: this host"
host_online=0
if command -v ip >/dev/null 2>&1; then
  if [ -n "$(ip route show default 2>/dev/null)" ]; then info "default route: $(ip route show default | head -n 1)"
  else info "no default route"; fi
fi
for h in $PUBLIC_HOSTS; do
  if getent hosts "$h" >/dev/null 2>&1; then info "resolves $h"; host_online=1; fi
done
for ip in $PUBLIC_IPS; do
  if timeout 4 bash -c "exec 3<>/dev/tcp/$ip/443" 2>/dev/null; then info "TCP $ip:443 reachable"; host_online=1; fi
done
if [ "$host_online" -eq 0 ]; then
  ok "this host cannot resolve or reach public internet hosts"
elif [ "$STRICT" -eq 1 ]; then
  fail "this host can still reach the internet"
  fix "disconnect it first (unplug, 'sudo ip link set <iface> down', or a firewall egress block), then re-run"
  FAILED=1
else
  warn "this host has internet access: Part 1 not proven (use --require-offline-host on a disconnected server)"
fi

step "Part 2: containers on the private network"
for service in backend ollama postgres; do
  network="$(docker inspect --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$(compose ps -q "$service")")"
  info "$service networks: $network"
done
internal="$(docker network inspect --format '{{.Internal}}' "${PROJECT}_private")"
if [ "$internal" = "true" ]; then
  ok "network ${PROJECT}_private is internal (no gateway to the outside)"
else
  fail "network ${PROJECT}_private is not internal"
  FAILED=1
fi

PROBE='
import socket, sys
failures = 0
for host in sys.argv[1].split():
    try:
        socket.getaddrinfo(host, 443)
        print(f"  FAIL  {host} resolves from inside the container"); failures += 1
    except OSError as e:
        print(f"  ok    DNS lookup of {host} fails: {e.strerror or e}")
for ip in sys.argv[2].split():
    try:
        socket.create_connection((ip, 443), timeout=4).close()
        print(f"  FAIL  TCP {ip}:443 connects from inside the container"); failures += 1
    except OSError as e:
        print(f"  ok    TCP {ip}:443 fails: {e.strerror or e}")
sys.exit(1 if failures else 0)
'
printf '  backend:\n'
compose exec -T backend python -c "$PROBE" "$PUBLIC_HOSTS" "$PUBLIC_IPS" || FAILED=1

printf '  ollama:\n'
if compose exec -T ollama ollama pull qwen3:0.6b >/dev/null 2>&1; then
  fail "ollama pull succeeded from the running stack"; FAILED=1
else
  ok "ollama pull fails (no route out, and the model store is mounted read-only)"
fi
if compose exec -T ollama sh -c 'touch /models/write-test' >/dev/null 2>&1; then
  fail "the model volume is writable at runtime"; FAILED=1
else
  ok "the model volume is read-only at runtime"
fi

step "Part 3: the application works under these conditions"
"$ROOT/scripts/smoke-test.sh" || FAILED=1

step "Result"
if [ "$FAILED" -eq 0 ]; then
  if [ "$host_online" -eq 0 ]; then ok "PASSED with no internet on the host or in the containers"
  else ok "PASSED for container isolation (the host itself was online)"; fi
else
  fail "FAILED: see above"
fi
printf '  report: %s\n' "$REPORT"
exit "$FAILED"
