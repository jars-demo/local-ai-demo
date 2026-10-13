#!/usr/bin/env bash
# Build the offline deployment bundle. CONNECTED build machine only.
#
#   ./scripts/build-bundle.sh                  # tests, build, pull, export, package
#   ./scripts/build-bundle.sh --skip-tests     # when CI already ran them
#   ./scripts/build-bundle.sh --with-gpu       # also ship the official (CUDA) Ollama image, ~2 GB more
#
# Output, in dist/:
#   local-ai-demo-bundle-<version>-linux-<arch>.tar          everything the server needs
#   local-ai-demo-bundle-<version>-linux-<arch>.tar.sha256   checksum to verify after the transfer
#
# Inside the archive: images/*.tar.gz (docker save), models/*.tar (Ollama blobs + manifest),
# compose.yaml, .env.example, scripts/, README.md (the offline guide), manifest.json, SHA256SUMS.
#
# Reproducibility: with the same images, model and SOURCE_DATE_EPOCH (defaults to the last commit's
# time), re-running produces a byte-identical archive: files are sorted, timestamps fixed, owners
# zeroed and gzip headers carry no name or time. Rebuilding the images themselves can change their
# IDs; the manifest records the IDs that were actually packaged.

source "$(dirname "$0")/lib.sh"

SKIP_TESTS=0
WITH_GPU=0
OUT="$ROOT/dist"
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-tests) SKIP_TESTS=1 ;;
    --with-gpu) WITH_GPU=1 ;;
    --output) OUT="$2"; shift ;;
    -h | --help) sed -n '2,20p' "$0"; exit 0 ;;
    *) die "unknown option: $1 (see --help)" ;;
  esac
  shift
done

[ -f "$ROOT/compose.override.yaml" ] || die "run this from the repository, not from an extracted bundle"
need docker "Install Docker Engine 24+ with the Compose plugin."

VERSION="$(env_value APP_VERSION 1.0.0)"
OLLAMA_VERSION="$(env_value OLLAMA_VERSION 0.40.3)"
MODEL="$(env_value OLLAMA_MODEL qwen3:0.6b)"
case "$(docker info --format '{{.Architecture}}')" in
  x86_64 | amd64) ARCH=amd64 ;;
  aarch64 | arm64) ARCH=arm64 ;;
  *) die "unsupported Docker architecture: $(docker info --format '{{.Architecture}}')" ;;
esac
NAME="local-ai-demo-bundle-${VERSION}-linux-${ARCH}"
STAGE="$OUT/$NAME"
GIT_COMMIT="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo uncommitted)"
if [ -z "${SOURCE_DATE_EPOCH:-}" ]; then
  SOURCE_DATE_EPOCH="$(git -C "$ROOT" log -1 --format=%ct 2>/dev/null || true)"
  if [ -z "$SOURCE_DATE_EPOCH" ]; then
    SOURCE_DATE_EPOCH=0
    warn "no commit yet: archive timestamps use the Unix epoch (set SOURCE_DATE_EPOCH to override)"
  fi
fi
export SOURCE_DATE_EPOCH

printf '%sBuilding %s%s  (model %s, Ollama %s, commit %s)\n' "$C_B" "$NAME" "$C_0" "$MODEL" "$OLLAMA_VERSION" "$GIT_COMMIT"

# --- 1. Checks and tests ---------------------------------------------------------------------

step "1/7 Check this build machine"
"$ROOT/scripts/check-prereqs.sh" --build > /dev/null || die "./scripts/check-prereqs.sh --build reported a problem"
ok "prerequisites"
compose config --quiet && ok "compose.yaml is valid"

if [ "$SKIP_TESTS" -eq 0 ]; then
  step "2/7 Run the backend tests (unit + integration against a real PostgreSQL)"
  compose up -d --wait postgres > /dev/null 2>&1 || die "could not start postgres for the integration tests"
  if compose --profile test run --rm --build backend-test > "$OUT.test.log" 2>&1; then
    ok "$(tail -n 1 "$OUT.test.log")"
    rm -f "$OUT.test.log"
  else
    tail -n 30 "$OUT.test.log" >&2
    die "tests failed; full log: $OUT.test.log"
  fi
else
  step "2/7 Tests skipped (--skip-tests)"
fi

# --- 2. Images -------------------------------------------------------------------------------

step "3/7 Build the application images and pull the third-party ones"
compose build web backend ollama
mapfile -t IMAGES < <(compose config --images | sort -u)
for image in "${IMAGES[@]}"; do
  case "$image" in
    local-ai-demo-*) ok "built  $image" ;;
    *) docker pull --platform "linux/$ARCH" -q "$image" > /dev/null && ok "pulled $image" ;;
  esac
done
if [ "$WITH_GPU" -eq 1 ]; then
  docker pull --platform "linux/$ARCH" -q "ollama/ollama:$OLLAMA_VERSION" > /dev/null
  IMAGES+=("ollama/ollama:$OLLAMA_VERSION")
  ok "pulled ollama/ollama:$OLLAMA_VERSION (GPU)"
fi

# --- 3. Model --------------------------------------------------------------------------------

step "4/7 Make sure the model is downloaded and verified"
OLLAMA_IMAGE="local-ai-demo-ollama:$OLLAMA_VERSION"
MANIFEST_PATH="$(model_manifest_path "$MODEL")"
in_volume() { docker run --rm --network none -v "$MODEL_VOLUME:/models:ro" --entrypoint "$1" "$OLLAMA_IMAGE" "${@:2}"; }
if ! docker volume inspect "$MODEL_VOLUME" > /dev/null 2>&1 || ! in_volume test -f "/models/$MANIFEST_PATH" 2> /dev/null; then
  "$ROOT/scripts/pull-model.sh" "$MODEL"
fi
MODEL_MANIFEST_JSON="$(in_volume cat "/models/$MANIFEST_PATH")"
mapfile -t BLOBS < <(printf '%s' "$MODEL_MANIFEST_JSON" | grep -o 'sha256:[0-9a-f]\{64\}' | sort -u | sed 's/^sha256:/sha256-/')
[ "${#BLOBS[@]}" -ge 2 ] || die "the model manifest lists no blobs: $MANIFEST_PATH"
# Re-hash every blob on disk: its file name is its SHA-256. The script runs inside the container,
# hence the single quotes.
# shellcheck disable=SC2016
if in_volume sh -c 'cd /models/blobs && for f in "$@"; do echo "${f#sha256-}  $f"; done | sha256sum -c --quiet' sh "${BLOBS[@]}"; then
  ok "$MODEL: ${#BLOBS[@]} blobs, every SHA-256 matches its name"
else
  die "a model blob does not match its checksum; delete the volume and pull again"
fi

# --- 4. Export -------------------------------------------------------------------------------

step "5/7 Export images and the model"
rm -rf "$STAGE"
mkdir -p "$STAGE/images" "$STAGE/models" "$STAGE/scripts"

# `docker save` stamps some directory entries with the current time, so two saves of the same image
# differ. Re-pack the archive with sorted names and fixed timestamps; the content (and the image ID
# that `docker load` produces) is unchanged. This runs in a Linux container (GNU tar, real
# symlinks) so it behaves the same on any build host. The ${...} inside are the container's.
# shellcheck disable=SC2016
NORMALIZE='d="$(mktemp -d)" && tar -C "$d" -xf - && tar -C "$d" --sort=name --mtime="@$1" --owner=0 --group=0 --numeric-owner --format=gnu -cf - .'
IMAGE_ENTRIES=()
for image in "${IMAGES[@]}"; do
  file="images/$(printf '%s' "$image" | tr '/:' '__').tar.gz"
  docker save --platform "linux/$ARCH" "$image" \
    | docker run --rm -i --network none --entrypoint sh "$OLLAMA_IMAGE" -c "$NORMALIZE" sh "$SOURCE_DATE_EPOCH" \
    | gzip -n -6 > "$STAGE/$file"
  id="$(docker image inspect --format '{{.Id}}' "$image")"
  arch="$(docker image inspect --format '{{.Architecture}}' "$image")"
  os="$(docker image inspect --format '{{.Os}}' "$image")"
  unpacked="$(docker image inspect --format '{{.Size}}' "$image")"
  bytes="$(size_of "$STAGE/$file")"
  sum="$(sha256_of "$STAGE/$file")"
  IMAGE_ENTRIES+=("$(printf '    {"ref": "%s", "id": "%s", "os": "%s", "architecture": "%s", "file": "%s", "bytes": %s, "unpacked_bytes": %s, "sha256": "%s"}' \
    "$image" "$id" "$os" "$arch" "$file" "$bytes" "$unpacked" "$sum")")
  ok "$image -> $file ($(human "$bytes"))"
done

# Only this model's files: both manifest layouts, its blobs, and Ollama's per-blob metadata cache.
# Other models that happen to be in the volume are not exported.
MODEL_FILE="models/$(model_slug "$MODEL").tar"
MANIFEST_V2_PATH="$(model_manifest_v2_path "$MODEL")"
CANDIDATES=("$MANIFEST_PATH" "$MANIFEST_V2_PATH" "${BLOBS[@]/#/blobs/}" "${BLOBS[@]/#/metadata/}")
# shellcheck disable=SC2016
mapfile -t EXPORT_PATHS < <(in_volume sh -c 'cd /models && for p in "$@"; do
    case "$p" in metadata/*) p="$p.json" ;; esac
    if [ -e "$p" ] || [ -L "$p" ]; then echo "$p"; fi
  done' sh "${CANDIDATES[@]}")
printf '%s\n' "${EXPORT_PATHS[@]}" | grep -qx "$MANIFEST_V2_PATH" \
  || die "Ollama has not written $MANIFEST_V2_PATH; run ./scripts/pull-model.sh $MODEL again"
docker run --rm --network none -v "$MODEL_VOLUME:/models:ro" --entrypoint tar "$OLLAMA_IMAGE" \
  -C /models --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner \
  -cf - "${EXPORT_PATHS[@]}" > "$STAGE/$MODEL_FILE"
MODEL_BYTES="$(size_of "$STAGE/$MODEL_FILE")"
MODEL_SUM="$(sha256_of "$STAGE/$MODEL_FILE")"
ok "$MODEL -> $MODEL_FILE ($(human "$MODEL_BYTES"), ${#EXPORT_PATHS[@]} entries)"

# Round trip: restore the export into an empty scratch volume and load it read-only, the way the
# offline server will. This catches a model store the runtime cannot use before anyone travels.
CHECK_VOLUME="${PROJECT}-bundle-check"
docker volume rm -f "$CHECK_VOLUME" > /dev/null 2>&1 || true
docker volume create "$CHECK_VOLUME" > /dev/null
docker run --rm -i --network none -v "$CHECK_VOLUME:/models" --entrypoint tar "$OLLAMA_IMAGE" \
  -C /models -xf - < "$STAGE/$MODEL_FILE"
if model_loads_read_only "$CHECK_VOLUME" "$OLLAMA_IMAGE" "$MODEL"; then
  ok "round trip: the exported model loads from a fresh read-only volume with no network"
else
  docker volume rm -f "$CHECK_VOLUME" > /dev/null 2>&1 || true
  die "the exported model does not load from a fresh read-only volume"
fi
docker volume rm -f "$CHECK_VOLUME" > /dev/null 2>&1 || true

# --- 5. Files --------------------------------------------------------------------------------

step "6/7 Add Compose, scripts, docs, manifest and checksums"
cp "$ROOT/compose.yaml" "$ROOT/.env.example" "$STAGE/"
[ "$WITH_GPU" -eq 1 ] && cp "$ROOT/compose.gpu.yaml" "$STAGE/"
for script in lib.sh check-prereqs.sh verify-bundle.sh offline-install.sh smoke-test.sh smoke_test.py airgap-test.sh diagnose.sh; do
  cp "$ROOT/scripts/$script" "$STAGE/scripts/"
done
chmod 0755 "$STAGE"/scripts/*.sh
cp "$ROOT/docs/offline-deployment.md" "$STAGE/README.md"
cp "$ROOT/docs/third-party-notices.md" "$STAGE/THIRD-PARTY-NOTICES.md"
cp "$ROOT/LICENSE" "$STAGE/LICENSE"

BLOB_LIST="$(printf '"%s", ' "${BLOBS[@]}" | sed 's/, $//')"
{
  printf '{\n'
  printf '  "bundle": "%s",\n' "$NAME"
  printf '  "schema": 1,\n'
  printf '  "app_version": "%s",\n' "$VERSION"
  printf '  "git_commit": "%s",\n' "$GIT_COMMIT"
  printf '  "source_date_epoch": %s,\n' "$SOURCE_DATE_EPOCH"
  printf '  "platform": {"os": "linux", "architecture": "%s"},\n' "$ARCH"
  printf '  "built_with": {"docker": "%s", "compose": "%s"},\n' \
    "$(docker version --format '{{.Server.Version}}')" "$(docker compose version --short)"
  printf '  "images": [\n'
  (IFS=$'\n'; printf '%s' "${IMAGE_ENTRIES[*]}" | sed '$!s/$/,/')
  printf '\n  ],\n'
  printf '  "model": {"name": "%s", "ollama_version": "%s", "file": "%s", "bytes": %s, "sha256": "%s",\n' \
    "$MODEL" "$OLLAMA_VERSION" "$MODEL_FILE" "$MODEL_BYTES" "$MODEL_SUM"
  printf '            "manifest": "%s", "blobs": [%s],\n' "$MANIFEST_PATH" "$BLOB_LIST"
  printf '            "license": "Apache-2.0", "source": "https://ollama.com/library/%s"},\n' "${MODEL%%:*}"
  printf '  "embedding_assets": [],\n'
  printf '  "embedding_assets_note": "None needed: retrieval uses PostgreSQL full-text search."\n'
  printf '}\n'
} > "$STAGE/manifest.json"
ok "manifest.json"

(
  cd "$STAGE" || exit 1
  find . -type f | sed 's|^\./||' | LC_ALL=C sort | while read -r file; do
    printf '%s  %s\n' "$(sha256_of "$file")" "$file"
  done > "$OUT/SHA256SUMS.tmp"
)
mv "$OUT/SHA256SUMS.tmp" "$STAGE/SHA256SUMS"
ok "SHA256SUMS ($(wc -l < "$STAGE/SHA256SUMS" | tr -d ' ') files)"

# --- 6. Archive ------------------------------------------------------------------------------

step "7/7 Package"
ARCHIVE="$OUT/$NAME.tar"
tar --force-local -C "$OUT" --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner \
  --mode='u+rwX,go+rX,go-w' --format=gnu -cf "$ARCHIVE" "$NAME"
(cd "$OUT" && printf '%s  %s\n' "$(sha256_of "$NAME.tar")" "$NAME.tar" > "$NAME.tar.sha256")
ok "$ARCHIVE ($(human "$(size_of "$ARCHIVE")"))"
ok "$ARCHIVE.sha256: $(cut -d' ' -f1 "$ARCHIVE.sha256")"

printf '\n%sNext%s: copy both files to the server (USB drive, scp over a private link, ...), then:\n' "$C_B" "$C_0"
printf '  sha256sum -c %s.tar.sha256\n  tar -xf %s.tar\n  cd %s && ./scripts/offline-install.sh\n' "$NAME" "$NAME" "$NAME"
