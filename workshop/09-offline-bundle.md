# 09 · Packaging a Portable Offline Bundle

> ⏱ 25 minutes · Images, model, manifest and SHA-256 checksums in one reproducible archive.

> [!NOTE]
> **Advanced.** Part 2 is for operators who will deploy to a server without internet. Everything in
> Part 1 stands on its own.

## Goal

Build one archive that contains everything the server needs, and nothing it does not, with a
manifest and checksums that let anyone verify it without trusting the machine it came from.

## What you'll learn

- What "everything" is: four images, the model, Compose, configuration templates, scripts, docs
- `docker save` and `docker load`: images as files
- A manifest with versions, image IDs, architectures, sizes and SHA-256 for every file
- Reproducible packaging: same inputs, byte-identical archive

## Architecture

```text
connected build machine                                         dist/
  tests ─► docker compose build ─► docker pull postgres           local-ai-demo-bundle-1.0.0-linux-amd64.tar
  ./scripts/pull-model.sh (ollama verifies every blob)            local-ai-demo-bundle-1.0.0-linux-amd64.tar.sha256
  docker save | normalise | gzip ─► images/*.tar.gz
  model files (manifests, blobs, metadata) ─► models/qwen3_0.6b.tar
  round trip: restore the model into a scratch volume, load it read-only
  manifest.json + SHA256SUMS ─► tar (sorted, fixed time, owner 0)
```

Inside the archive:

```text
local-ai-demo-bundle-1.0.0-linux-amd64/
├── README.md                    the offline deployment guide (docs/offline-deployment.md)
├── THIRD-PARTY-NOTICES.md       model and software licenses
├── LICENSE
├── compose.yaml                 the runtime stack, no build steps
├── .env.example
├── manifest.json                versions, image IDs, architectures, sizes, SHA-256
├── SHA256SUMS                   one line per file
├── images/   local-ai-demo-backend_1.0.0.tar.gz  local-ai-demo-ollama_0.40.3.tar.gz
│             local-ai-demo-web_1.0.0.tar.gz      postgres_18.6-alpine3.24.tar.gz
├── models/   qwen3_0.6b.tar
└── scripts/  check-prereqs.sh verify-bundle.sh offline-install.sh smoke-test.sh smoke_test.py
              airgap-test.sh diagnose.sh lib.sh
```

No embedding model is included because none is needed: retrieval is PostgreSQL full-text search.
`manifest.json` says so explicitly (`"embedding_assets": []`).

## Prerequisites

Modules 01 to 08. The build machine needs internet access and GNU tar (`./scripts/check-prereqs.sh --build`).
Build on the same CPU architecture as the server (the bundle is `linux/amd64` or `linux/arm64`).

## Steps

### 1. Build the bundle

```bash
./scripts/build-bundle.sh
```

> **What it does:** Seven steps: checks this machine; runs the backend's unit and integration tests;
> builds the three application images and pulls `postgres`; makes sure the model is downloaded and
> re-hashes every blob; exports each image with `docker save`, and the model's files with `tar`;
> restores that model export into a scratch volume and loads it read-only to prove it works; writes
> `manifest.json` and `SHA256SUMS` and packs everything into one archive.
> **Why:** Everything that needs the internet happens here, on a machine that has it.
> **Expected (measured):**
>
> ```text
> ==> 5/7 Export images and the model
>   ok    local-ai-demo-backend:1.0.0 -> images/local-ai-demo-backend_1.0.0.tar.gz (54.9 MB)
>   ok    local-ai-demo-ollama:0.40.3 -> images/local-ai-demo-ollama_0.40.3.tar.gz (54.2 MB)
>   ok    local-ai-demo-web:1.0.0 -> images/local-ai-demo-web_1.0.0.tar.gz (25.4 MB)
>   ok    postgres:18.6-alpine3.24 -> images/postgres_18.6-alpine3.24.tar.gz (116.5 MB)
>   ok    qwen3:0.6b -> models/qwen3_0.6b.tar (522.7 MB, 9 entries)
>   ok    round trip: the exported model loads from a fresh read-only volume with no network
> ==> 7/7 Package
>   ok    dist/local-ai-demo-bundle-1.0.0-linux-amd64.tar (774.0 MB)
> ```
>
> About 1 to 2 minutes when images are already built. Use `--skip-tests` if CI already ran them.

### 2. Read the manifest

```bash
python3 -m json.tool dist/local-ai-demo-bundle-1.0.0-linux-amd64/manifest.json | head -30
```

> **What it does:** Pretty-prints the manifest (any JSON viewer works).
> **Why:** It is the bundle's bill of materials: what is in it, built from which commit, for which
> platform, with which Docker, and the checksum of every artifact.
> **Expected:** `"platform": {"os": "linux", "architecture": "amd64"}`, then one entry per image
> with `ref`, `id` (the image ID `docker load` must reproduce), `architecture`, `bytes`,
> `unpacked_bytes` and `sha256`, then the `model` with its license, source and blob list.

### 3. Verify the archive like the server will

```bash
cd dist
sha256sum -c local-ai-demo-bundle-1.0.0-linux-amd64.tar.sha256
cd ..
./scripts/verify-bundle.sh dist/local-ai-demo-bundle-1.0.0-linux-amd64.tar
```

> **What it does:** Checks the archive against its checksum, first by hand, then with the script.
> **Why:** The `.sha256` file travels with the archive. A mismatch on the server means the copy is
> incomplete or altered: do not install it.
> **Expected:** `local-ai-demo-bundle-1.0.0-linux-amd64.tar: OK`, then
> `ok    archive matches local-ai-demo-bundle-1.0.0-linux-amd64.tar.sha256`.

### 4. Prove it is reproducible

```bash
cp dist/local-ai-demo-bundle-*.tar.sha256 /tmp/first.sha256
./scripts/build-bundle.sh --skip-tests > /dev/null
diff <(cut -d' ' -f1 /tmp/first.sha256) <(cut -d' ' -f1 dist/local-ai-demo-bundle-*.tar.sha256) && echo identical
```

> **What it does:** Builds the bundle a second time from the same images and model, and compares
> the archive checksums.
> **Why:** A reproducible bundle can be rebuilt and checked by someone else. `docker save` stamps
> the current time on some entries, so the script re-packs each saved image with sorted names and a
> fixed timestamp (`SOURCE_DATE_EPOCH`, the last commit's time); `gzip -n` drops gzip's own time.
> **Expected:** `identical`. Measured: two consecutive builds both produced
> `4c10e30c7c6dbc6fc25e6041a0999642ca066e4ffff88b9d2b8e009dff90fca9`.

> [!NOTE]
> Reproducible *packaging* means the same images and model give the same archive. Rebuilding the
> images from source can still change their IDs (timestamps inside layers, newer packages in a base
> image). The manifest records the exact IDs that were packaged, and the installer checks them.

### 5. Optional: GPU

```bash
./scripts/build-bundle.sh --with-gpu
```

Adds the official `ollama/ollama:0.40.3` image (CUDA) and `compose.gpu.yaml`. It is 5.57 GB
unpacked, so the bundle grows by roughly 2 GB compressed. Only useful with an NVIDIA GPU and the
NVIDIA Container Toolkit on the server.

## Verification

- [ ] `dist/` holds the `.tar` and its `.tar.sha256`
- [ ] `manifest.json` lists four images, all `amd64` (or all `arm64`), and the model
- [ ] Two builds give the same archive checksum

## Exercises

1. Extract the bundle into a temporary folder and run `./scripts/verify-bundle.sh` inside it. Then
   change one byte of `compose.yaml` and run it again. What does it report?
2. Why is the model stored as a plain `.tar` while images are `.tar.gz`? (Try `gzip -c` on the model
   file and compare sizes.)
3. Find where `build-bundle.sh` refuses to package a model that does not load from a read-only
   volume. What bug would ship without that check?

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `tar is not GNU tar` | macOS ships bsdtar | `brew install gnu-tar` and put `gnubin` first in `PATH` |
| `cannot reach registry.ollama.ai` | No internet or a proxy blocks it | Fix connectivity, or pull the model once and keep the volume |
| `Ollama has not written manifests-v2/...` | The model was pulled by an older Ollama | `./scripts/pull-model.sh` again with this version |
| Archive checksum differs between two builds | An image was rebuilt in between (new ID) | Expected; compare the image `id` fields in the two manifests |
| `tests failed` | A real failure | Read the log path printed; fix before shipping |

Next: [10 · Deploying on Bare-metal Linux without Internet](10-airgapped-deployment.md)
