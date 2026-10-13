#!/usr/bin/env bash
# Simulate the air-gapped deployment end to end on one machine. CONNECTED build machine.
#
#   ./scripts/build-bundle.sh            # first
#   ./scripts/airgap-simulate.sh         # then
#
# Starts a fresh Docker-in-Docker "server" on an internal network (no route to the internet),
# copies the bundle in, and runs, inside it: the archive checksum, extraction, offline-install.sh
# (which loads images and restores the model) and airgap-test.sh --require-offline-host. The inner
# Docker daemon starts empty: if anything tried to pull an image or a model, it would fail.
#
# This is a simulation of a separate server, not a replacement for testing on real hardware: the
# kernel, CPU and memory are this machine's. docs/offline-deployment.md has the manual procedure.

source "$(dirname "$0")/lib.sh"

VERSION="$(env_value APP_VERSION 1.0.0)"
case "$(docker info --format '{{.Architecture}}')" in x86_64 | amd64) ARCH=amd64 ;; *) ARCH=arm64 ;; esac
NAME="local-ai-demo-bundle-${VERSION}-linux-${ARCH}"
DIST="$ROOT/dist"
SERVER="${PROJECT}-airgap-server"
NETWORK="${PROJECT}-airgap"
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

[ -f "$DIST/$NAME.tar" ] || die "$DIST/$NAME.tar not found: run ./scripts/build-bundle.sh first"

cleanup() {
  if [ "$KEEP" -eq 0 ]; then
    docker rm -f -v "$SERVER" >/dev/null 2>&1 || true
    docker network rm "$NETWORK" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

step "Prepare the simulated server image (connected, like installing OS packages)"
docker build -q -t local-ai-demo-airgap-server:test "$ROOT/tests/airgap" >/dev/null
ok "local-ai-demo-airgap-server:test"

step "Start it on an internal network (no internet)"
docker rm -f -v "$SERVER" >/dev/null 2>&1 || true
docker network rm "$NETWORK" >/dev/null 2>&1 || true
docker network create --internal "$NETWORK" >/dev/null
docker run -d --privileged --name "$SERVER" --hostname offline-server --network "$NETWORK" \
  -e DOCKER_TLS_CERTDIR= local-ai-demo-airgap-server:test >/dev/null
for _ in $(seq 1 60); do docker exec "$SERVER" docker info >/dev/null 2>&1 && break; sleep 1; done
docker exec "$SERVER" docker info >/dev/null 2>&1 || die "the inner Docker daemon did not start"
ok "inner Docker $(docker exec "$SERVER" docker version --format '{{.Server.Version}}'), images: $(docker exec "$SERVER" docker images -q | wc -l)"

step "Copy the bundle to the server (the 'USB drive')"
docker exec "$SERVER" mkdir -p /opt/transfer
docker cp "$DIST/$NAME.tar" "$SERVER:/opt/transfer/"
docker cp "$DIST/$NAME.tar.sha256" "$SERVER:/opt/transfer/"
ok "copied $(human "$(size_of "$DIST/$NAME.tar")")"

step "On the server: verify, extract, install, prove"
docker exec "$SERVER" bash -euo pipefail -c "
  cd /opt/transfer
  sha256sum -c $NAME.tar.sha256
  tar -xf $NAME.tar -C /opt
  cd /opt/$NAME
  ./scripts/offline-install.sh --skip-smoke
  ./scripts/airgap-test.sh --require-offline-host
"
ok "the bundle installed and answered questions on a server with no internet"

# Keep the evidence: the acceptance report written on the simulated server.
REPORT="$DIST/airgap-report-simulated.log"
docker exec "$SERVER" sh -c "cat /opt/$NAME/airgap-report-*.log" > "$REPORT"
ok "report saved to $REPORT"
if [ "$KEEP" -eq 1 ]; then
  info "kept running: docker exec -it $SERVER bash   (remove: docker rm -f -v $SERVER)"
fi
