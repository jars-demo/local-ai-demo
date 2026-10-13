#!/usr/bin/env bash
# Verify a bundle's integrity. Works with no network and changes nothing.
#
#   ./scripts/verify-bundle.sh path/to/local-ai-demo-bundle-*.tar   # the archive, before extracting
#   ./scripts/verify-bundle.sh                                      # inside an extracted bundle
#
# Archive mode checks the archive against its .tar.sha256 file. Extracted mode checks every file
# against SHA256SUMS, then checks that manifest.json and SHA256SUMS agree with each other.

source "$(dirname "$0")/lib.sh"

check_sums() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum -c --quiet "$1"; else shasum -a 256 -c --quiet "$1"; fi
}

if [ $# -gt 0 ]; then
  archive="$1"
  [ -f "$archive" ] || die "no such file: $archive"
  [ -f "$archive.sha256" ] || die "missing $archive.sha256: copy it together with the archive"
  step "Verify $(basename "$archive")"
  (cd "$(dirname "$archive")" && check_sums "$(basename "$archive").sha256") \
    || { fail "the archive does not match its checksum"; fix "copy it again; the transfer was incomplete or altered"; exit 1; }
  ok "archive matches $(basename "$archive").sha256"
  exit 0
fi

BUNDLE="$ROOT"
[ -f "$BUNDLE/manifest.json" ] && [ -f "$BUNDLE/SHA256SUMS" ] \
  || die "run this inside an extracted bundle (manifest.json and SHA256SUMS not found in $BUNDLE)"

step "Verify every file against SHA256SUMS"
if (cd "$BUNDLE" && check_sums SHA256SUMS); then
  ok "$(wc -l < "$BUNDLE/SHA256SUMS" | tr -d ' ') files match their SHA-256"
else
  fail "one or more files are missing or changed (listed above)"
  fix "extract the archive again from a copy that passes: ./scripts/verify-bundle.sh <archive>"
  exit 1
fi

step "Cross-check manifest.json"
missing=0
while read -r file; do
  listed_sum="$(grep -o '"file": *"'"$file"'"[^}]*"sha256": *"[0-9a-f]*"' "$BUNDLE/manifest.json" | grep -o '[0-9a-f]\{64\}' | tail -n 1)"
  actual_sum="$(awk -v f="$file" '$2 == f {print $1}' "$BUNDLE/SHA256SUMS")"
  if [ -n "$actual_sum" ] && [ "$listed_sum" = "$actual_sum" ]; then ok "$file"
  else fail "$file: manifest and SHA256SUMS disagree or the file is not listed"; missing=1; fi
done < <(grep -o '"file": *"[^"]*"' "$BUNDLE/manifest.json" | sed 's/.*"\([^"]*\)"$/\1/')
[ "$missing" -eq 0 ] || { fix "the bundle was edited after it was built; rebuild it"; exit 1; }

unlisted="$(cd "$BUNDLE" && find . -type f ! -name SHA256SUMS ! -name .env ! -name '*.log' | sed 's|^\./||' | LC_ALL=C sort \
  | while read -r f; do grep -q "  $f\$" SHA256SUMS || echo "$f"; done)"
if [ -n "$unlisted" ]; then
  warn "files not in SHA256SUMS (not part of the original bundle):"
  printf '%s\n' "$unlisted" | sed 's/^/        /' >&2
fi

ok "bundle $(grep -o '"bundle": *"[^"]*"' "$BUNDLE/manifest.json" | cut -d'"' -f4) is intact"
