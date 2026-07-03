# Helix — bootstrap design and roadmap

Status: **in work** · Created: 2026-06-30 · Source of truth (markdown). The
reckon HTML plan in `docs/` is a rendered lens over this document, not a
competing source.

## 1. What Helix is

A long-horizon agent orchestrator. Helix wraps a native agent worker inside a
deterministic outer loop with three disciplined phases — **plan, implement,
judge** — that hand off through files, never through an accumulating
conversation. The loop is dumb; the worker is smart. The durable record (plain
text + git history) is the asset, not any single agent session.

Helix is project-agnostic: a shared, versioned core serves many repositories,
with per-project knowledge layered on as small data overlays.

## 2. Fixed design choices (non-negotiable)

1. Dumb orchestration, smart worker — no model judgment in the loop; never
   reimplement the worker's tool surface (model-harness fit).
2. Phase separation with fresh context per phase; the judge is always separate
   from the worker.
3. Markdown-and-files as truth; HTML as a rendered human lens.
4. The human's seat is the plan phase; the agreed plan is a signed contract.
5. A tiered completion oracle — fast `surrogate` checks every iteration; slow or
   physical `blocking` gates pause the loop for human ground truth.
6. Provenance and session chaining are first-class; findings are age- and
   condition-stamped.
7. Parallel where idempotent, serial at the gate.
8. Project-agnostic core, project-specific data; drift is the chief long-term
   risk and is designed against.

These are grounded in three references: long-running-agent engineering (the
Ralph loop; verification as backpressure; state outside the model),
model-harness fit (do not pull a model out of the harness it was trained on),
and agent-memory engineering (LLM + markdown + bash is the whole stack; default
to *not* saving; age-stamp and verify at read time).

## 3. Architecture

```
plan  ──(agreed plan = contract)──▶  implement ──(evidence)──▶  judge
  ▲                                      │  ▲                      │
  │                                      └──┘ (loop until          │
 human seat                              oracle pass / cap / gate) │
                                                                   ▼
                                            verdict: pass | fail | blocked
```

- **Core** (`helix/`): `loop.py` (the dumb loop), `phases/` (plan/implement/judge
  contracts), `worker.py` (native-worker adapter, no tool reimplementation),
  `session.py` (ids, chaining, provenance), `oracle.py` (tiered gates),
  `state.py` (markdown+frontmatter substrate), `models.py` (generated from
  `schema/helix.yaml`).
- **Prompts** (`prompts/`): project-agnostic base phase contracts.
- **Overlays** (`projects/<name>/`): glossary, gate definitions, spec, and
  prompt extensions — small diffs over the core.
- **Sessions** (`sessions/`): the committed lab notebook.
- **Schema** (`schema/helix.yaml`): LinkML; single source of truth for state
  record types; pydantic generated via `gen-pydantic`.

## 4. The completion oracle (tiered)

| Tier | Cadence | On unmet | Example |
|------|---------|----------|---------|
| `surrogate` | every iteration | judge returns `fail` with direction | unit tests, linters, reference-diff |
| `blocking` | when reached | loop blocks, judge returns `blocked` | physical experiment, slow campaign run |

For Helix's own development the surrogate oracle is its **own test suite** —
clean, fast, deterministic — which makes the bootstrap loop's backpressure
tight.

## 5. Roadmap (phases)

We skip the throwaway bash-loop stage (the loop pattern is already validated)
and go straight to the structured harness. Stop and *use* Helix after each
stage; later stages are about scaling across projects and years, not capability.

- **P0 — Scaffold & init** ✅ *(this session)*
  Repo skeleton, pyproject (uv, Python ≥3.13), LinkML schema + generated models,
  base phase prompts, README/AGENTS/CLAUDE, LICENSE (MIT), git init,
  GitHub remote, first push, markdown plan + reckon lens. Surrogate baseline
  (tests) green.

- **P1 — Phase-separated loop + fresh judge** ✅ *(the ~80% of value)*
  Shipped. The dumb outer loop drives `implement→judge` iterations that hand off
  through files, with the surrogate oracle (the test suite) as fast
  backpressure. No model judgment lives in the loop or the phases — they compose
  prompts, invoke the native worker, evaluate gates, and persist sessions.
  - `state.py` — markdown+YAML frontmatter read/write (the handoff substrate).
  - `config.py` — project run config (worker command, caps, gates) from
    `helix.yaml`; runtime config, distinct from the durable schema records.
  - `oracle.py` — tiered gate evaluation reducing to `pass | fail | blocked`;
    surrogate gates run every iteration, a blocking gate pauses for ground truth.
  - `worker.py` — native-worker subprocess (composed prompt on stdin; the worker
    keeps its own tool surface — no reimplementation).
  - `session.py` — `write_session` persists `Session` records to `sessions/`.
  - `phases/implement.py` — compose prompt, invoke worker, persist evidence.
  - `phases/judge.py` — an independent, mechanical oracle verdict (never the
    worker); the test suite *is* the judge in this tier.
  - `loop.py` + CLI — `run_loop` halts on `pass | blocked | cap`; `helix run`
    turns the verdict into an exit code (0 / 2 / 1).
  - `helix.yaml` — the self-hosting run config (`helix run .`).

  *Done-when, met:* `helix run` drives implement→judge against a task with the
  test suite as the surrogate oracle and halts on pass/fail/cap; sessions are
  written to `sessions/` in the schema's record shape and chain through their
  predecessor; the test suite grew to 33 passing across loop/oracle/state/phases
  and stays green.

- **P2 — Interactive planning entry + clean session handoff** ✅
  Shipped. The `plan` phase is the human's seat: it materializes a
  `PlanState`-shaped contract on disk that `helix run` consumes unchanged. The
  determinism boundary is strict — the *tool* writes metadata (`PlanState`
  frontmatter: `id`, `project`, and the `agreed_at` signature); the
  *worker/human* writes the judgment-laden body (Intent, Tasks, oracle gates).
  - `phases/plan.py` — three moves: `scaffold` (materialize the `PlanState`
    skeleton, preserving an existing draft on re-entry), `compose_prompt` (base
    contract + overlay + where-to-write + current draft), and `seal` (stamp
    `agreed_at` — the human's signature turning a draft into the contract). `run`
    orchestrates them and persists a chained `plan` session; no model judgment.
  - `worker.converse` — the interactive human's-seat invocation: the composed
    prompt is the worker's opening message and the worker inherits the terminal,
    so a human co-authors in the worker's native REPL. Distinct from
    `worker.invoke` (autonomous, prompt on stdin) used by implement.
  - `phases/__init__.py` — `base_prompt` factored out (project overlay → packaged
    default), shared by plan and implement.
  - `cli.py` — `helix plan <project> [--intent …] [--agree/--draft] [--out …]
    [--no-worker]` wired to the phase.

  *Done-when, met:* `helix plan` co-authors and (on `--agree`) seals a
  `PlanState` contract that `helix run` consumes end-to-end (verified directly:
  plan→implement→judge with the planned intent flowing into the implement prompt
  and a `pass` verdict); handoff stays clean (fresh context per phase, files as
  the artifact, chained sessions); the test suite grew from 33 to 43 passing and
  stays green (lint clean).

- **P3 — Session management & provenance** ✅
  Shipped, with rich observability folded in. Sessions were already chained on
  disk (P1); P3 makes the provenance layer first-class and makes a running
  worker *watchable from outside*.
  - `session.py` — `walk_chain` follows the `predecessor` links into one
    coherent campaign thread (not merely everything on disk); `iter_sessions`
    for chronological listing; `record_findings`/`read_findings` persist
    schema-shaped `Finding` records, age- (`observed_at`) and condition-stamped,
    rediscoverable by the walker. `prepare_session`/`write_record` split the
    session write so evidence can stream in *before* the record is finalized.
  - `worker.invoke` — streams the worker's output line by line to an optional
    `sink` file (so `tail -f sessions/<id>/evidence/worker.txt` follows it live)
    and an `on_line` callback, with a threaded stdin feed (no pipe deadlock) and
    a timer-based timeout.
  - `observe.py` — a *projection* (never steering, never reimplementing tools)
    that renders a Claude Code `stream-json` trace as a legible train-of-thought:
    init header, assistant text, dimmed thinking, `→ tool(summary)` actions,
    `← result (ok/err, N chars)`, and a `✓ done — turns/cost/duration` footer.
    Data is Rich-escaped; plain-text workers pass through unstructured.
  - `judge.py` — findings are now persisted as `Finding` records.
  - `cli.py` — `helix status` (read-only: walks the chain, shows verdicts,
    gates, and recent findings), `helix watch` (replay a session's trace), and
    `helix run --stream` (live train-of-thought as the worker works).
  - `helix.yaml` — the worker emits `--output-format stream-json --verbose`.

  *Done-when, met:* verified with a **real `claude` worker** — `helix run`
  streamed its train-of-thought and actions live (init → Bash/Write actions →
  reasoning → done footer) to a `pass` verdict; `helix status`/`helix watch`
  render the chain and trace; the raw trace is newline-delimited JSON and
  `tail -f`-able. Findings persist as age-/condition-stamped `Finding` records.
  The test suite grew from 43 to 65 passing and stays green (lint clean).

- **P4 — Project-agnostic core split + anti-drift check**
  Formalize core vs overlay; per-project data as small diffs; a check that
  guards overlays from forking core contracts.

- **P5 — Drive & feedback (Ralph-loop usability)** ✅
  Shipped 2026-07-03. The loop is pleasant and robust to *drive*, designed
  initially around a Claude Code worker; the tool stayed dumb — every signal
  below is mechanical. Verified end-to-end in a tmp dir with a real haiku
  worker: a clean run to `pass` (worker wrote the files, ran the gate, checked
  its boxes; 35s, $0.11) and a full interrupt→resume cycle (15s timeout cut →
  exit 3 with resume hint → `helix run -c` continued the same conversation to
  `pass`). The suite grew 65 → 99 tests, green, lint clean. Landed across
  `helix/tasks.py`, `helix/progress.py`, `helix/worker.py` (`build_command`,
  exit-code evidence), `helix/observe.py` (`classify_trace`/`halt_reason`),
  `helix/loop.py`, `helix/cli.py`, and `examples/greeter/`.
  - **Plan tasks are machine-countable.** The Tasks section of the agreed plan
    uses markdown checkboxes (`- [ ]` / `- [x]`); the worker checks tasks off
    as part of updating progress state. A task may carry a per-step model
    annotation, e.g. `- [ ] Build the parser (model: haiku)`.
  - **Model routing.** The worker model resolves as: CLI `--model` override →
    the next open task's `(model: …)` annotation → the project's
    `helix.yaml` worker model → the worker's own default. The flag name used
    to pass it is worker data (`model_flag`, default `--model`).
  - **Rich run feedback.** `helix run` renders a live progress snapshot after
    each iteration: tasks done vs remaining as a bar, iteration/cap, elapsed,
    and a mechanical ETA (average time per completed task × tasks remaining).
  - **Token-limit robustness.** The loop mechanically classifies the worker
    trace (stream-json result event / known limit messages). A cut-off or
    limit-hit worker halts the loop with verdict `interrupted` (exit code 3)
    and a printed resume line; `helix run -c` from the run dir resumes the
    campaign — the chain on disk is the state, and the first resumed worker
    invocation gets the worker's native continue flag (`--continue` for
    Claude Code) so the interrupted conversation picks up where it was cut.
  - **A smoke example.** A stdlib-only example project (haiku-tier worker,
    checkbox plan, unittest gate) that copies into a tmp dir for end-to-end
    iteration before dogfooding on Helix itself.

- **P6 — Human lens**
  On-demand HTML rendering via reckon and chain-walking tools for reviewing
  campaigns over time. reckon is composed, never absorbed.

- **Milestone — self-hosting**
  Helix drives its own development through its own plan→implement→judge loop.
  This is the honest signal that the harness is real.

## 6. Decisions locked this session

- **License:** MIT (permissive/open; CC BY-ND was rejected — NoDerivatives is
  wrong for code meant to be extended). reckon is also MIT.
- **Layout:** flat `helix/helix/` (matches sibling repos), not `src/`.
- **Python:** ≥3.13.
- **CLI:** typer + rich.
- **Schema:** LinkML (`schema/helix.yaml`) → generated pydantic (`helix/models.py`).
- **Plan substrate:** markdown (this doc) is truth; reckon HTML is the lens.
- **reckon boundary:** separate repos, composed at runtime; Helix core imports
  nothing from reckon.
