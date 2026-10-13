# 06 · Running and Querying the Local LLM

> ⏱ 25 minutes · Talk to the model directly, then through the app; retrieval before inference.

## Goal

Run the model yourself, see what it is good and bad at, and understand how the backend turns a
question into a grounded answer: retrieve notes first, then infer.

## What you'll learn

- Which model this is, how big it is and what it is licensed under
- Talking to the model with the Ollama CLI and its HTTP API
- Why the prompt includes your notes, and why answers cite `[#id]`
- Honest limits of a 0.6B-parameter model on a CPU

## Architecture

```text
POST /api/ask {"question": "Where is the backup NAS?"}
  1. retrieve   PostgreSQL full-text search ──► notes #1 (and up to 3 more)
  2. prompt     system rules + "[#1] Server rack layout\n<body>" + the question
  3. infer      POST http://ollama:11434/api/chat (model qwen3:0.6b, think false, stream false)
  4. respond    answer + sources + timings reported by Ollama
```

## Prerequisites

Module 05, stack running, model installed.

## The model

| | |
|---|---|
| Name | `qwen3:0.6b`, by the Qwen team (Alibaba Cloud) |
| License | Apache 2.0 (shipped with the model; `ollama show qwen3:0.6b` prints it) |
| Parameters | 751.63M (Ollama's count; "0.6B" is the family name) |
| Quantisation | Q4_K_M (about 4.5 bits per weight) |
| On disk | 523 MB |
| Context window | 40,960 tokens supported; this stack uses 4,096 |
| In memory when loaded | about 1.0 GB (`ollama ps`); the Ollama container used 1.11 GiB |

It was chosen over `qwen2.5:0.5b` (398 MB) after a small test on this workshop's own notes: both
answered most questions, but Qwen3 cited its sources far more often (14 of 20 answers versus 1 of 20).
That is a small, workshop-specific comparison, not a benchmark.

## Steps

### 1. What Ollama has

```bash
docker compose exec ollama ollama list
docker compose exec ollama ollama ps
```

> **What it does:** `list` shows installed models; `ps` shows models loaded in memory right now.
> **Why:** Installed is not the same as loaded. The first request after a start loads the model,
> which takes seconds; later requests reuse it for 30 minutes (`OLLAMA_KEEP_ALIVE`).
> **Expected:**
>
> ```text
> NAME          ID              SIZE      MODIFIED
> qwen3:0.6b    7df6b6e09427    522 MB    34 minutes ago
> NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL
> qwen3:0.6b    7df6b6e09427    1.0 GB    100% CPU     4096       llamacpp    29 minutes from now
> ```
>
> `ps` is empty if nothing has asked the model anything since it started.

### 2. Talk to the model directly

```bash
docker compose exec ollama ollama run qwen3:0.6b --think=false "In one sentence: what is a Docker volume?"
```

> **What it does:** Runs one prompt with the CLI inside the Ollama container.
> **Why:** To see the raw model, with no notes and no rules.
> **Expected:** One sentence, after a pause the first time while the model loads. It may be
> imprecise: a 0.6B model knows little and can be wrong with confidence. That is exactly why the app
> gives it your notes.

### 3. Ask through the app

Open <http://localhost:3000/app/>, create a note titled `Server rack layout` with the body
`The backup NAS is in rack 4, slot 12. Power for rack 4 comes from PDU-B.`, then ask
`Where is the backup NAS?`. Or with curl:

```bash
curl -s -X POST http://127.0.0.1:3000/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"Where is the backup NAS?"}'
```

> **What it does:** Runs retrieval and inference through nginx and the backend.
> **Why:** This is the whole feature in one request.
> **Expected (a real response):**
>
> ```json
> {"answer": "The backup NAS is in rack 4, slot 12. [#1]",
>  "retrieval": "search",
>  "sources": [{"id": 1, "title": "Server rack layout", "score": 0.8}],
>  "retrieval_ms": 2,
>  "inference": {"model": "qwen3:0.6b", "total_ms": 488, "load_ms": 4,
>                "prompt_tokens": 122, "output_tokens": 18}}
> ```

### 4. Read the prompt

Open `backend/app/assistant/prompts.py`. The system message tells the model to answer only from the notes,
to cite ids such as `[#3]`, and to say when the notes do not cover the question. Each note is
labelled `[#id] title`. Long notes are clipped at a word boundary so the prompt fits the context.

### 5. Thinking off, on purpose

Qwen3 is a "thinking" model: by default it writes a reasoning section before answering. For short
answers from notes that mostly costs CPU time, so the backend sends `"think": false`
(`OLLAMA_THINK=false`). Compare:

```bash
docker compose exec ollama ollama run qwen3:0.6b --think=true "Is 17 a prime number? Answer yes or no."
```

> **What it does:** Asks with thinking on.
> **Why:** To see the extra tokens thinking costs.
> **Expected:** A "Thinking..." section before the answer, and a noticeably longer wait.

## Verification

- [ ] `ollama list` shows `qwen3:0.6b`, and `ollama ps` shows it loaded after a question
- [ ] An answer through `/api/ask` cites a note id and names the model in `inference.model`
- [ ] You can explain why the notes go into the prompt

## Exercises

1. Ask a question your notes do not answer, such as `What is the wifi password?`. Does the model say
   the notes do not cover it, or does it invent something? Try three times.
2. Create two notes that disagree (`The meeting is on Monday` and `The meeting moved to Tuesday`).
   Ask `When is the meeting?`. What would help: a better prompt, or showing `updated_at`?
3. Summarise a long note with the "Summarise" button. Compare `inference.total_ms` with an ask. Why
   is the first request after a restart slower (`load_ms`)?

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `MODEL_NOT_INSTALLED` | The model is not in the volume | `./scripts/pull-model.sh` (connected) or `./scripts/offline-install.sh` (offline) |
| First answer takes 10 s or more | The model is loading from disk into memory | Normal once per start; `OLLAMA_KEEP_ALIVE=30m` keeps it loaded |
| `LLM_TIMEOUT` | A slow CPU, or a very long note | Raise `LLM_TIMEOUT_SECONDS` in `.env`; keep notes focused |
| Answers ignore the notes | Retrieval found nothing and used recent notes | Check `retrieval` in the response; use words that appear in the note |
| Ollama container killed (`OOMKilled`) | `OLLAMA_MEMORY_LIMIT` too low for the model | Keep it at `3g` or more |

Next: [07 · The Inference API and Model Storage](07-inference-api.md)
