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

- **P1 — Phase-separated loop + fresh judge** (the ~80% of value)
  Implement `loop.py`, `worker.py`, `phases/*`, `oracle.py` (surrogate tier),
  `state.py`. Prove plan→implement→judge with file handoffs on Helix itself,
  using Helix's test suite as the fast oracle. Done when an autonomous loop can
  make a verified increment without a human in the inner loop.

- **P2 — Interactive planning entry + clean session handoff**
  Build the `plan` phase: how a human co-authors a plan and materializes the
  contract the loop consumes. Tool writes deterministic metadata; worker writes
  judgment-laden content.

- **P3 — Session management & provenance**
  Self-contained sessions, predecessor chaining, age-stamped findings, and the
  commit/push discipline for the durable record. Implement the `status` command
  and chain walking.

- **P4 — Project-agnostic core split + anti-drift check**
  Formalize core vs overlay; per-project data as small diffs; a check that
  guards overlays from forking core contracts.

- **P5 — Human lens**
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
