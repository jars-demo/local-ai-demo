#!/usr/bin/env bash
# Checks that this machine can build (connected) or run (offline target) the stack.
#
#   ./scripts/check-prereqs.sh            # target checks: run the stack
#   ./scripts/check-prereqs.sh --build    # build machine checks: also GNU tar, git, internet
#
# Hard requirements fail (exit 1). Recommendations warn. Every failure prints how to fix it.

source "$(dirname "$0")/lib.sh"

MODE="target"
[ "${1:-}" = "--build" ] && MODE="build"
FAILED=0
bad() { fail "$1"; fix "$2"; FAILED=1; }

MIN_MEM_MB=4096    # stack used ~1.3 GB with the model loaded; the OS and page cache need the rest
REC_MEM_MB=8192
MIN_DISK_MB=4000   # images (~670 MB loaded) + model (523 MB) + data, with headroom for updates

step "Operating system and architecture"
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64 | amd64) ARCH=amd64 ;;
  aarch64 | arm64) ARCH=arm64 ;;
esac
if [ "$OS" = "Linux" ]; then ok "Linux $(uname -r)"
elif [ "$MODE" = "build" ]; then warn "$OS: fine for building and the core workshop (Docker Desktop); the offline target must be Linux"
else bad "$OS is not Linux" "deploy to a Linux server; Docker Desktop works for the workshop, not for the air-gapped target"; fi
if [ "$ARCH" = "amd64" ]; then ok "architecture amd64 (tested)"
elif [ "$ARCH" = "arm64" ]; then warn "architecture arm64: images build for it, but this project tests amd64 only"
else bad "architecture $ARCH is not supported" "use an x86_64 (amd64) server"; fi

# A bundle states the architecture it was built for; it must match this machine.
if [ -f "$ROOT/manifest.json" ]; then
  bundle_arch="$(grep -o '"architecture": *"[a-z0-9]*"' "$ROOT/manifest.json" | head -n 1 | sed 's/.*"\([a-z0-9]*\)"$/\1/')"
  if [ "$bundle_arch" = "$ARCH" ]; then ok "bundle architecture $bundle_arch matches this machine"
  else bad "bundle is linux/$bundle_arch, this machine is $ARCH" "build the bundle on (or for) linux/$ARCH"; fi
fi

step "Docker and Compose"
if command -v docker >/dev/null 2>&1; then
  if server="$(docker version --format '{{.Server.Version}}' 2>/dev/null)"; then
    major="${server%%.*}"
    if [ "$major" -ge 24 ] 2>/dev/null; then ok "Docker Engine $server"
    else bad "Docker Engine $server is too old" "install Docker Engine 24 or newer"; fi
  else
    bad "the Docker daemon is not reachable" "start Docker (sudo systemctl start docker) and add your user to the docker group"
  fi
  if compose_version="$(docker compose version --short 2>/dev/null)"; then
    compose_major="${compose_version#v}"; compose_major="${compose_major%%.*}"
    compose_minor="${compose_version#v}"; compose_minor="${compose_minor#*.}"; compose_minor="${compose_minor%%.*}"
    if [ "$compose_major" -ge 3 ] || { [ "$compose_major" -eq 2 ] && [ "$compose_minor" -ge 24 ]; }; then
      ok "Docker Compose $compose_version"
    else
      bad "Docker Compose $compose_version is too old" "install the Compose v2 plugin 2.24 or newer (needs --wait, --pull never)"
    fi
  else
    bad "the Docker Compose v2 plugin is missing" "install docker-compose-plugin (the 'docker compose' command, not docker-compose)"
  fi
else
  bad "docker is not installed" "install Docker Engine: https://docs.docker.com/engine/install/ (on an offline server, from your OS's offline packages)"
fi

step "CPU, memory and disk"
CPUS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc 2>/dev/null || echo 0)"
if [ "$CPUS" -ge 4 ]; then ok "$CPUS CPU cores"
elif [ "$CPUS" -ge 2 ]; then warn "$CPUS CPU cores: works, answers are slower (4+ recommended)"
else bad "$CPUS CPU core(s)" "use a machine with at least 2 cores"; fi
if [ -r /proc/cpuinfo ]; then
  if grep -qm1 avx2 /proc/cpuinfo; then ok "AVX2 available (faster CPU inference)"
  else warn "no AVX2: Ollama falls back to a slower CPU path"; fi
fi

if [ -r /proc/meminfo ]; then
  MEM_MB=$(( $(awk '/MemTotal/ {print $2}' /proc/meminfo) / 1024 ))
  if [ "$MEM_MB" -ge "$REC_MEM_MB" ]; then ok "$MEM_MB MB memory"
  elif [ "$MEM_MB" -ge "$MIN_MEM_MB" ]; then warn "$MEM_MB MB memory: enough, $REC_MEM_MB MB recommended"
  else bad "$MEM_MB MB memory" "the stack needs at least $MIN_MEM_MB MB"; fi
else
  info "memory: not readable here (Docker Desktop: check Settings > Resources)"
fi

if command -v docker >/dev/null 2>&1 && DOCKER_ROOT="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null)"; then
  check_dir="$DOCKER_ROOT"
  [ -d "$check_dir" ] || check_dir="$ROOT"   # Docker Desktop: the root is inside its VM
  FREE_MB=$(df -Pm "$check_dir" | awk 'NR == 2 {print $4}')
  if [ "$FREE_MB" -ge "$MIN_DISK_MB" ]; then ok "$FREE_MB MB free for Docker ($check_dir)"
  else bad "only $FREE_MB MB free in $check_dir" "free at least $MIN_DISK_MB MB for images, the model and data"; fi
fi

step "Tools"
for tool in tar gzip awk sed grep; do
  if command -v "$tool" >/dev/null 2>&1; then ok "$tool"; else bad "$tool is missing" "install it from your OS packages"; fi
done
if command -v sha256sum >/dev/null 2>&1 || command -v shasum >/dev/null 2>&1; then ok "sha256sum"
else bad "sha256sum is missing" "install coreutils"; fi
if command -v curl >/dev/null 2>&1; then ok "curl (optional)"; else info "curl not found: optional, the scripts fall back to bash"; fi

if [ "$MODE" = "build" ]; then
  if tar --version 2>/dev/null | grep -q "GNU tar"; then ok "GNU tar (needed for a reproducible archive)"
  else bad "tar is not GNU tar" "macOS: brew install gnu-tar and put gnubin first in PATH"; fi
  if command -v git >/dev/null 2>&1; then ok "git"; else bad "git is missing" "install git"; fi
  step "Internet access (build machine only)"
  if ! command -v curl >/dev/null 2>&1; then
    warn "curl not found: cannot check access to registry.ollama.ai (needed to download the model)"
  elif curl -sS --retry 2 --retry-all-errors --max-time 15 https://registry.ollama.ai/v2/ > /dev/null; then
    ok "can reach registry.ollama.ai (model download)"
  else
    bad "cannot reach registry.ollama.ai" "the build machine needs internet access (or a proxy) to download the model"
  fi
fi

step "Result"
if [ "$FAILED" -eq 0 ]; then ok "this machine meets the requirements ($MODE)"; else fail "fix the items above, then run this again"; exit 1; fi
