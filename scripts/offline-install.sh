#!/usr/bin/env bash
# Install or update the stack from an extracted bundle. Needs NO network access.
#
#   ./scripts/offline-install.sh                # install or update, then run the smoke test
#   ./scripts/offline-install.sh --bind 0.0.0.0 # serve the web UI on every interface
#   ./scripts/offline-install.sh --skip-smoke   # install only
#
# What it does, in order: check prerequisites, verify every checksum, `docker load` each image
# and compare its ID to the manifest, restore the model into the model volume and re-hash it,
# write .env (a random database password on first install), start Compose with --pull never and
# --no-build, then run the smoke test. It never pulls an image, downloads a model, or calls any
# external service. Re-running it with a newer bundle is how you update; your data volumes stay.

source "$(dirname "$0")/lib.sh"

SMOKE=1
BIND=""
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-smoke) SMOKE=0 ;;
    --bind) BIND="$2"; shift ;;
    -h | --help) sed -n '2,15p' "$0"; exit 0 ;;
    *) die "unknown option: $1 (see --help)" ;;
  esac
  shift
done

BUNDLE="$ROOT"
MANIFEST="$BUNDLE/manifest.json"
[ -f "$MANIFEST" ] || die "manifest.json not found: run this from an extracted bundle"
field() { grep -o "\"$1\": *\"[^\"]*\"" "$MANIFEST" | head -n 1 | cut -d'"' -f4; }

printf '%sInstalling %s%s\n' "$C_B" "$(field bundle)" "$C_0"

step "1/6 Prerequisites"
"$BUNDLE/scripts/check-prereqs.sh" || exit 1

step "2/6 Verify the bundle"
"$BUNDLE/scripts/verify-bundle.sh" > /dev/null || { "$BUNDLE/scripts/verify-bundle.sh"; exit 1; }
ok "every file matches SHA256SUMS and manifest.json"

step "3/6 Load images (docker load: no registry is contacted)"
grep -o '"ref": *"[^"]*", "id": *"[^"]*"[^}]*"file": *"[^"]*"' "$MANIFEST" | while read -r entry; do
  ref="$(printf '%s' "$entry" | cut -d'"' -f4)"
  id="$(printf '%s' "$entry" | cut -d'"' -f8)"
  file="$(printf '%s' "$entry" | grep -o '"file": *"[^"]*"' | cut -d'"' -f4)"
  if [ "$(docker image inspect --format '{{.Id}}' "$ref" 2>/dev/null)" = "$id" ]; then
    ok "$ref already loaded"
    continue
  fi
  docker load -i "$BUNDLE/$file" > /dev/null || die "docker load failed for $file"
  loaded="$(docker image inspect --format '{{.Id}}' "$ref" 2>/dev/null || true)"
  [ "$loaded" = "$id" ] || die "$ref loaded with ID $loaded, the manifest says $id"
  ok "$ref ($id)"
done

step "4/6 Restore the model"
MODEL="$(field name)"
MODEL_FILE="$(grep -o '"model": {[^}]*' "$MANIFEST" | grep -o '"file": *"[^"]*"' | cut -d'"' -f4)"
MANIFEST_PATH="$(grep -o '"manifest": *"[^"]*"' "$MANIFEST" | cut -d'"' -f4)"
OLLAMA_VERSION="$(grep -o '"ollama_version": *"[^"]*"' "$MANIFEST" | cut -d'"' -f4)"
OLLAMA_IMAGE="local-ai-demo-ollama:$OLLAMA_VERSION"
mapfile -t BLOBS < <(grep -o '"blobs": *\[[^]]*\]' "$MANIFEST" | grep -o 'sha256-[0-9a-f]\{64\}')

create_volume "$MODEL_VOLUME" ollama-models
create_volume "$DATA_VOLUME" postgres-data
# Runs as the image's unprivileged user (uid 10001), with no network at all.
docker run --rm -i --network none -v "$MODEL_VOLUME:/models" --entrypoint tar "$OLLAMA_IMAGE" \
  -C /models -xf - < "$BUNDLE/$MODEL_FILE" || die "could not extract $MODEL_FILE into $MODEL_VOLUME"
if docker run --rm --network none -v "$MODEL_VOLUME:/models:ro" --entrypoint sh "$OLLAMA_IMAGE" -c \
  'cd /models/blobs && for f in "$@"; do echo "${f#sha256-}  $f"; done | sha256sum -c --quiet' sh "${BLOBS[@]}"; then
  ok "$MODEL restored to $MODEL_VOLUME; ${#BLOBS[@]} blobs re-hashed on disk"
else
  die "a restored blob does not match its SHA-256"
fi
docker run --rm --network none -v "$MODEL_VOLUME:/models:ro" --entrypoint test "$OLLAMA_IMAGE" -f "/models/$MANIFEST_PATH" \
  || die "model manifest $MANIFEST_PATH missing after restore"
if model_loads_read_only "$MODEL_VOLUME" "$OLLAMA_IMAGE" "$MODEL"; then
  ok "Ollama loads $MODEL from the read-only volume with no network, as the stack will"
else
  die "Ollama cannot use the restored model read-only; see the output above"
fi

step "5/6 Configure (.env)"
if [ ! -f "$BUNDLE/.env" ]; then
  cp "$BUNDLE/.env.example" "$BUNDLE/.env"
  chmod 600 "$BUNDLE/.env"
  # 24 random bytes from the kernel as 48 hex characters. `od -N` reads a fixed count, so nothing
  # is cut off mid-pipe (`tr < /dev/urandom | head` dies of SIGPIPE under `set -o pipefail`).
  password="$(od -An -tx1 -N24 /dev/urandom | tr -d ' \n')"
  set_env_value POSTGRES_PASSWORD "$password"
  ok "created .env with a random POSTGRES_PASSWORD (kept in $BUNDLE/.env, mode 600)"
else
  ok "keeping the existing .env"
  if [ "$(env_value POSTGRES_PASSWORD)" = "change-me-local-only" ]; then
    warn "POSTGRES_PASSWORD is still the example value; change it before the database is first created"
  fi
fi
set_env_value APP_VERSION "$(field app_version)"
set_env_value OLLAMA_VERSION "$OLLAMA_VERSION"
set_env_value OLLAMA_MODEL "$MODEL"
[ -n "$BIND" ] && set_env_value WEB_BIND "$BIND"
ok "APP_VERSION=$(env_value APP_VERSION) OLLAMA_MODEL=$MODEL WEB_BIND=$(env_value WEB_BIND) WEB_PORT=$(env_value WEB_PORT)"

step "6/6 Start (--pull never --no-build)"
# Every image Compose needs must already be here; refuse to continue rather than let anything
# try a registry.
for image in $(compose config --images); do
  docker image inspect "$image" > /dev/null 2>&1 || die "image $image is not loaded and will not be pulled"
done
if ! log="$(compose up -d --pull never --no-build --wait --wait-timeout 300 2>&1)"; then
  printf '%s\n' "$log" | tail -n 20 >&2
  fail "the stack did not become healthy"
  fix "./scripts/diagnose.sh"
  exit 1
fi
compose ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}'
ok "running"

if [ "$SMOKE" -eq 1 ]; then
  "$BUNDLE/scripts/smoke-test.sh"
fi

printf '\n%sDone.%s Open http://%s:%s\n' "$C_B" "$C_0" "$(env_value WEB_BIND 127.0.0.1 | sed 's/^0.0.0.0$/<this-server>/')" "$(env_value WEB_PORT 3000)"
