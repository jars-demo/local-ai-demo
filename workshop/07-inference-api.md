# 07 · The Inference API and Model Storage

> ⏱ 20 minutes · Ollama endpoints, timings, manifests, blobs and checksums on disk.

## Goal

Call Ollama's HTTP API the way the backend does, read its timings, and see exactly what "the model"
is on disk: a manifest and a few content-addressed files you can verify with `sha256sum`.

## What you'll learn

- The four Ollama endpoints this app uses, and the one it deliberately never uses
- Where the timing numbers in every answer come from
- The model store: manifests, blobs, metadata, and why blob names are their checksums
- Why the runtime mounts the model store read-only

## Architecture

```text
backend/app/llm/ollama.py ──HTTP──► ollama:11434
   GET  /api/version     which Ollama
   GET  /api/tags        which models are installed      ──► readiness
   POST /api/show        model details (context length)  ──► /api/model
   POST /api/chat        inference                       ──► /api/ask, /api/notes/{id}/summary
   (never /api/pull: there is no code for it)

/models (volume local-ai-demo-ollama-models, mounted read-only)
   manifests/registry.ollama.ai/library/qwen3/0.6b      the manifest (JSON)
   manifests-v2/ollama.com/library/qwen3/0.6b           symlink to the manifest stored as a blob
   blobs/sha256-<digest>                                 weights, template, license, params, config
   metadata/sha256-<digest>.json                         Ollama's cache of the weights' header
```

## Prerequisites

Module 06.

## Steps

### 1. Call the chat API yourself

The Ollama port is not published, so call it from the backend container, as the backend does:

```bash
docker compose exec backend python -c "
import json, urllib.request as u
body = {'model': 'qwen3:0.6b', 'think': False, 'stream': False,
        'messages': [{'role': 'user', 'content': 'In one sentence: what is a container?'}],
        'options': {'temperature': 0.2, 'num_predict': 60}}
r = u.urlopen(u.Request('http://ollama:11434/api/chat', json.dumps(body).encode(),
              {'Content-Type': 'application/json'}), timeout=120)
print(json.dumps(json.load(r), indent=1))"
```

> **What it does:** Sends one non-streaming chat request.
> **Why:** This is the only inference call the app makes; seeing it raw removes the magic.
> **Expected (a real response; your text will differ):**
>
> ```json
> {
>  "model": "qwen3:0.6b",
>  "message": {"role": "assistant", "content": "A container is a structure or object used to hold or transport goods, people, or other items."},
>  "done": true,
>  "done_reason": "stop",
>  "total_duration": 578906850,
>  "load_duration": 3264142,
>  "prompt_eval_count": 25,
>  "prompt_eval_duration": 294293000,
>  "eval_count": 21,
>  "eval_duration": 262101000
> }
> ```

The model answered about shipping containers, not software ones: with no context, a small model
guesses. Durations are in nanoseconds. `eval_count / eval_duration` is the generation speed: here
21 tokens in 0.26 s, about 80 tokens per second on this laptop's CPU. The backend converts these to
the `total_ms`, `load_ms`, `prompt_tokens` and `output_tokens` you see in every answer.

### 2. Look inside the model store

```bash
docker compose exec ollama sh -c 'ls -la /models/blobs; du -sh /models'
```

> **What it does:** Lists the blob files and the store's total size.
> **Why:** "The model" is just files. Each file's name is the SHA-256 of its content.
> **Expected:**
>
> ```text
> -rw-r--r-- 1 ollama ollama       858 sha256-7df6b6e09427a7...   the manifest, as a blob
> -rw-r--r-- 1 ollama ollama 522640096 sha256-7f4030143c1c47...   the weights (GGUF)
> -rw-r--r-- 1 ollama ollama      1723 sha256-ae370d884f108d...   the chat template
> -rw-r--r-- 1 ollama ollama       490 sha256-b0830f4ff6a022...   the config
> -rw-r--r-- 1 ollama ollama       120 sha256-cff3f395ef3756...   default parameters
> -rw-r--r-- 1 ollama ollama     11338 sha256-d18a5cc71b84bc...   the license (Apache 2.0)
> 499M	/models
> ```

### 3. Verify the model yourself

```bash
docker compose exec ollama sh -c 'cd /models/blobs && for f in sha256-*; do echo "${f#sha256-}  $f"; done | sha256sum -c'
```

> **What it does:** Recomputes every blob's SHA-256 and compares it with the file name.
> **Why:** Content addressing makes a model verifiable with standard tools, without trusting where
> it came from. The bundle and the offline installer run exactly this check.
> **Expected:** Six lines ending in `: OK`.

### 4. The store is read-only at runtime

```bash
docker compose exec ollama touch /models/test
```

> **What it does:** Tries to write into the model store from the running Ollama.
> **Why:** `compose.yaml` mounts it with `:ro`. The running stack can load the model but can never
> change, add or delete one, so nothing at runtime can quietly download a different model.
> **Expected:** `touch: cannot touch '/models/test': Read-only file system`.

This has one consequence worth knowing. Ollama 0.40 writes a second manifest layout
(`manifests-v2/`) the first time it reads a model. On a read-only store that write fails, so the
bundle ships `manifests-v2/` ready-made, and the installer starts a throwaway read-only Ollama to
prove the restored store loads before the real stack starts.

### 5. The API the app never calls

```bash
docker compose exec ollama ollama pull qwen3:0.6b
```

> **What it does:** Tries to download the model from inside the running stack.
> **Why:** To see both protections at once.
> **Expected:** `Error: pull model manifest: Get "https://registry.ollama.ai/v2/library/qwen3/manifests/0.6b": dial tcp: lookup registry.ollama.ai on 127.0.0.11:53: server misbehaving`.
> Docker's DNS cannot resolve public names on an internal network. Had it resolved, the read-only
> store would have refused the write.

## Verification

- [ ] You called `/api/chat` and computed tokens per second from the response
- [ ] All six blobs pass `sha256sum -c`
- [ ] Writing to `/models` fails, and so does `ollama pull`

## Exercises

1. Run the chat request twice with the same prompt. Why is `load_duration` large only after a
   restart, and what is `prompt_eval_cached_count`?
2. Print the manifest: `docker compose exec ollama cat /models/manifests/registry.ollama.ai/library/qwen3/0.6b`.
   Match each `digest` to a blob file.
3. Read `backend/tests/test_llm.py`: which test proves the client cannot download a model?

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `sha256sum: WARNING: 1 computed checksum did NOT match` | A blob is corrupt (disk, interrupted copy) | Restore the model again from the bundle, or pull again on a connected machine |
| Ollama healthy but `/api/tags` returns 500 | The store lacks `manifests-v2` and is read-only | Re-run `./scripts/offline-install.sh`; it restores and checks it |
| `model "qwen3:0.6b" not found` from `/api/chat` | The model name in `.env` differs from what is installed | Make `OLLAMA_MODEL` match `ollama list` |
| Very low tokens per second | No AVX2, or the CPU is busy | `./scripts/check-prereqs.sh` reports AVX2; close other heavy work |

Next: [08 · Multi-stage Builds and Image Optimization](08-image-optimization.md)
