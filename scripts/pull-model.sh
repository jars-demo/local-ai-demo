#!/usr/bin/env bash
# Download the model into the model volume. CONNECTED machines only.
#
#   ./scripts/pull-model.sh              # the model named in .env (OLLAMA_MODEL)
#   ./scripts/pull-model.sh qwen3:0.6b
#
# The running stack cannot do this, by design: its Ollama sits on an internal network with no
# route out, and its model volume is mounted read-only. So this script starts a short-lived,
# separate Ollama container on Docker's default bridge network (which can reach the internet),
# mounts the same volume read-write, runs `ollama pull` (which verifies every blob's SHA-256),
# then removes the container.

source "$(dirname "$0")/lib.sh"

MODEL="${1:-$(env_value OLLAMA_MODEL qwen3:0.6b)}"
IMAGE="local-ai-demo-ollama:$(env_value OLLAMA_VERSION 0.40.3)"
HELPER="${PROJECT}-model-pull"

need docker "Install Docker Engine 24+ with the Compose plugin."

step "Pulling $MODEL into the volume $MODEL_VOLUME"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  info "image $IMAGE not found, building it (docker compose build ollama)"
  compose build ollama
fi

create_volume "$MODEL_VOLUME" ollama-models
docker rm -f "$HELPER" >/dev/null 2>&1 || true
trap 'docker rm -f "$HELPER" >/dev/null 2>&1 || true' EXIT

docker run -d --name "$HELPER" --network bridge \
  -v "$MODEL_VOLUME:/models" -e OLLAMA_NO_CLOUD=1 "$IMAGE" >/dev/null
for _ in $(seq 1 30); do
  docker exec "$HELPER" ollama list >/dev/null 2>&1 && break
  sleep 1
done
docker exec "$HELPER" ollama list >/dev/null 2>&1 || die "the temporary Ollama did not start: docker logs $HELPER"

if ! docker exec "$HELPER" ollama pull "$MODEL"; then
  fail "ollama pull $MODEL failed"
  fix "check this machine's internet access and the model name on https://ollama.com/library"
  exit 1
fi

step "Installed models"
docker exec "$HELPER" ollama list
ok "$MODEL is in $MODEL_VOLUME. The running stack sees it without a restart."
