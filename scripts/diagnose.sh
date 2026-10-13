#!/usr/bin/env bash
# Collect what you need to debug the stack, and say what to do about each problem found.
# Read-only: it changes nothing, needs no network, and never prints the database password.
#
#   ./scripts/diagnose.sh                # report to the terminal
#   ./scripts/diagnose.sh > report.txt   # to attach to an issue (review it first)

source "$(dirname "$0")/lib.sh"
set +e
PROBLEMS=0
problem() { fail "$1"; fix "$2"; PROBLEMS=$((PROBLEMS + 1)); }

step "Versions"
info "host: $(uname -srm)"
info "docker: $(docker version --format '{{.Server.Version}}' 2>&1)"
info "compose: $(docker compose version --short 2>&1)"
[ -f "$ROOT/manifest.json" ] && info "bundle: $(grep -o '"bundle": *"[^"]*"' "$ROOT/manifest.json" | cut -d'"' -f4)"
info ".env: APP_VERSION=$(env_value APP_VERSION) OLLAMA_MODEL=$(env_value OLLAMA_MODEL) WEB_BIND=$(env_value WEB_BIND) WEB_PORT=$(env_value WEB_PORT)"
[ -f "$ROOT/.env" ] || problem "no .env file" "cp .env.example .env and set POSTGRES_PASSWORD (the offline installer does this for you)"

step "Images"
for image in $(compose config --images 2>/dev/null); do
  if docker image inspect "$image" >/dev/null 2>&1; then ok "$image"
  else problem "$image is missing" "offline: ./scripts/offline-install.sh loads it from the bundle; connected: docker compose build / docker compose pull"; fi
done

step "Containers"
compose ps -a --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}'
for service in postgres ollama backend web; do
  state="$(compose ps -a --format '{{.State}} {{.Health}}' "$service" 2>/dev/null)"
  case "$state" in
    "running healthy") ;;
    "") problem "$service does not exist" "docker compose up -d --pull never --no-build --wait" ;;
    *) problem "$service is '$state'" "docker compose logs --tail 50 $service" ;;
  esac
done

step "Volumes"
for volume in "$MODEL_VOLUME" "$DATA_VOLUME"; do
  if docker volume inspect "$volume" >/dev/null 2>&1; then ok "$volume"
  else problem "volume $volume is missing" "the model volume is restored by ./scripts/offline-install.sh; the data volume is created by Compose"; fi
done

step "Readiness (through the backend container)"
if [ "$(compose ps --format '{{.State}}' backend 2>/dev/null)" = "running" ]; then
  ready="$(compose exec -T backend python -c "import urllib.request as u
try:
    print(u.urlopen('http://127.0.0.1:8000/api/ready', timeout=10).read().decode())
except Exception as e:
    print(getattr(e, 'read', lambda: str(e).encode())().decode())" 2>&1)"
  info "$ready"
  case "$ready" in
    *'"model":"missing'*) problem "the model is not installed" "./scripts/offline-install.sh restores it from the bundle (connected: ./scripts/pull-model.sh)" ;;
    *'"database":"error'*) problem "the backend cannot use PostgreSQL" "see the backend and postgres logs below" ;;
    *'"ollama":"error'*) problem "the backend cannot reach Ollama" "see the ollama logs below" ;;
  esac
fi

step "Ollama's own view of the model store"
if compose ps --format '{{.State}}' ollama 2>/dev/null | grep -q running; then
  if models="$(compose exec -T ollama ollama list 2>&1)"; then
    ok "ollama list: $(printf '%s\n' "$models" | tail -n +2 | awk '{print $1, $3, $4}' | paste -sd ',' -)"
  else
    # A running Ollama whose API errors (HTTP 500) is invisible in its logs: ask it directly.
    problem "ollama list fails: $models" "the model volume is read-only at runtime; restore it again with ./scripts/offline-install.sh (it re-checks that Ollama can load it read-only)"
  fi
else
  info "ollama is not running"
fi

step "Recent errors in the logs"
for service in postgres ollama backend web; do
  lines="$(compose logs --tail 200 "$service" 2>&1 | grep -iE 'error|fatal|panic|denied|refused' | grep -vE 'level=INFO|"level": "(info|debug)"' | tail -n 5)"
  [ -z "$lines" ] && { ok "$service: no recent errors"; continue; }
  warn "$service:"
  printf '%s\n' "$lines" | sed 's/^/        /'
  case "$lines" in
    *"password authentication failed"*)
      problem "PostgreSQL rejects the password" "the data volume was created with another POSTGRES_PASSWORD: put the original back in .env (removing $DATA_VOLUME deletes all notes)" ;;
    *"permission denied"* | *"Permission denied"*)
      problem "$service hit a permission error" "a volume may have been created by another user; check: docker run --rm -v <volume>:/v alpine ls -ln /v" ;;
    *"out of memory"* | *"OOM"* | *"killed"*)
      problem "$service ran out of memory" "raise OLLAMA_MEMORY_LIMIT in .env or add RAM; check: docker stats --no-stream" ;;
  esac
done

step "Resources"
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null | grep -E "NAME|$PROJECT"
available_kb="$(awk '/MemAvailable/ {print $2}' /proc/meminfo 2>/dev/null)"
if [ -n "$available_kb" ]; then info "host memory available: $((available_kb / 1024)) MB"; fi
root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null)"
[ -d "$root" ] && info "disk free for Docker: $(df -Pm "$root" | awk 'NR == 2 {print $4}') MB"

step "Summary"
if [ "$PROBLEMS" -eq 0 ]; then ok "no problems found"; else fail "$PROBLEMS problem(s) found; each has a 'fix:' line above"; fi
exit 0
