#!/usr/bin/env bash
# Shared helpers for the scripts in this directory. Sourced, never run directly.
#
# Works in two places: the repository (connected build machine) and an extracted offline bundle
# (target server). Both have compose.yaml and .env.example at the root, next to scripts/.

set -euo pipefail

# Git Bash on Windows rewrites arguments that look like paths (/models -> C:/Program Files/Git/models)
# before Docker sees them. Turn that off; it does nothing on Linux or macOS.
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'

# `pwd -W` exists only in Git Bash: it gives E:/path, which both bash and Docker Desktop accept.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && { pwd -W 2>/dev/null || pwd; })"
PROJECT="local-ai-demo"
# Used by the scripts that source this file.
# shellcheck disable=SC2034
MODEL_VOLUME="local-ai-demo-ollama-models"
# shellcheck disable=SC2034
DATA_VOLUME="local-ai-demo-postgres-data"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_OK=$'\033[32m' C_WARN=$'\033[33m' C_ERR=$'\033[31m' C_DIM=$'\033[2m' C_B=$'\033[1m' C_0=$'\033[0m'
else
  C_OK="" C_WARN="" C_ERR="" C_DIM="" C_B="" C_0=""
fi

step() { printf '\n%s==> %s%s\n' "$C_B" "$*" "$C_0"; }
ok()   { printf '  %sok%s    %s\n' "$C_OK" "$C_0" "$*"; }
info() { printf '  %s..%s    %s\n' "$C_DIM" "$C_0" "$*"; }
warn() { printf '  %swarn%s  %s\n' "$C_WARN" "$C_0" "$*" >&2; }
fail() { printf '  %sFAIL%s  %s\n' "$C_ERR" "$C_0" "$*" >&2; }
die()  { fail "$*"; exit 1; }

# fix "message": a hint shown under a failure, so every error says what to do next.
fix()  { printf '        %sfix:%s %s\n' "$C_B" "$C_0" "$*" >&2; }

need() {
  command -v "$1" >/dev/null 2>&1 || die "'$1' is not installed. $2"
}

# Reads KEY from .env (or .env.example when there is no .env yet), without sourcing the file.
env_value() {
  local key="$1" default="${2:-}" file="$ROOT/.env" value=""
  [ -f "$file" ] || file="$ROOT/.env.example"
  if [ -f "$file" ]; then
    value="$(grep -E "^${key}=" "$file" | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)"
  fi
  printf '%s' "${value:-$default}"
}

# Sets KEY=value in .env, replacing an existing line or appending one.
set_env_value() {
  local key="$1" value="$2" file="$ROOT/.env"
  if grep -qE "^${key}=" "$file"; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "$file" && rm -f "$file.bak"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

# docker compose, always from the root, always the runtime file. In the repository the
# development override (build steps) is picked up automatically; a bundle does not have it.
compose() {
  (cd "$ROOT" && docker compose "$@")
}

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

size_of() {
  wc -c < "$1" | tr -d ' '
}

human() {
  awk -v b="$1" 'BEGIN { split("B KB MB GB TB", u); i = 1; while (b >= 1000 && i < 5) { b /= 1000; i++ } printf (i == 1 ? "%d %s" : "%.1f %s"), b, u[i] }'
}

# Creates a named volume the way Compose would (same labels), so `docker compose up` adopts it
# instead of warning that it "was not created by Docker Compose".
create_volume() {
  local name="$1" key="$2"
  docker volume inspect "$name" >/dev/null 2>&1 && return 0
  docker volume create "$name" \
    --label "com.docker.compose.project=$PROJECT" \
    --label "com.docker.compose.volume=$key" >/dev/null
}

# Model name "qwen3:0.6b" -> manifest path inside the model volume, and a file-safe name.
model_manifest_path() {
  local name="${1%%:*}" tag="${1##*:}"
  [ "$name" = "$1" ] && tag="latest"
  case "$name" in
    */*) printf 'manifests/registry.ollama.ai/%s/%s' "$name" "$tag" ;;
    *)   printf 'manifests/registry.ollama.ai/library/%s/%s' "$name" "$tag" ;;
  esac
}
model_slug() { printf '%s' "$1" | tr ':/' '__'; }

# Ollama 0.40+ also keeps a "v2" manifest: a symlink to a blob that holds the manifest. It creates
# it on first read, which fails on a read-only volume, so the bundle ships it ready-made.
model_manifest_v2_path() {
  local name="${1%%:*}" tag="${1##*:}"
  [ "$name" = "$1" ] && tag="latest"
  case "$name" in
    */*) printf 'manifests-v2/ollama.com/%s/%s' "$name" "$tag" ;;
    *)   printf 'manifests-v2/ollama.com/library/%s/%s' "$name" "$tag" ;;
  esac
}

# model_loads_read_only VOLUME IMAGE MODEL: start a throwaway Ollama exactly as the stack runs it
# (model volume read-only, no network at all) and ask it to describe the model. Succeeds only if
# the running stack will be able to use the volume as it is.
model_loads_read_only() {
  local volume="$1" image="$2" model="$3" name="${PROJECT}-model-check" result=1
  docker rm -f "$name" > /dev/null 2>&1 || true
  docker run -d --name "$name" --network none --read-only --tmpfs /tmp \
    -e OLLAMA_NO_CLOUD=1 -e OLLAMA_NOPRUNE=1 -v "$volume:/models:ro" "$image" > /dev/null || return 1
  for _ in $(seq 1 30); do
    docker exec "$name" ollama list > /dev/null 2>&1 && break
    sleep 1
  done
  if docker exec "$name" ollama show "$model" > /dev/null 2>&1; then
    result=0
  else
    docker exec "$name" ollama list >&2 || true
  fi
  docker rm -f "$name" > /dev/null 2>&1 || true
  return "$result"
}
