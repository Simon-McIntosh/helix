# Helix — Agent Guidelines

Helix is a long-horizon agent orchestrator: a **dumb** plan→implement→judge loop
around a **smart** native worker. Read `README.md` for the thesis and the eight
fixed design choices, and `docs/specs/` for the live design and roadmap. This
file is the working contract for agents in *this* repo; user-global guardrails
(git safety, commit discipline, model selection) are in
`/home/ITER/mcintos/.agents/AGENTS.md` and are not repeated here.

## Primary branch

`main` (trunk-based). Commit incrementally to `main` and push immediately. No
feature branches unless the user asks for a PR.

## Invariants you must not break

These are the project's reason to exist — treat them as binding:

- **Never reimplement, wrap, or translate the worker's tool surface.** Helix
  invokes a native worker and lets it use its own tools, skills, and edit
  format (model-harness fit). `helix/worker.py` sets context; it does not steer
  the worker turn-by-turn.
- **No model judgment in the loop.** `helix/loop.py` and the phases compose
  prompts, invoke the worker, run the oracle, enforce caps, and persist state —
  nothing else.
- **Fresh context per phase; files are the handoff.** Plan, implement, and judge
  are separate invocations. Never thread an accumulating conversation between
  them. A worker never judges its own work.
- **Markdown-and-files is the source of truth.** HTML (reckon) is a projection
  generated on demand, never authoritative.
- **reckon is composed, never absorbed.** Helix core imports nothing from
  reckon. reckon is a capability the worker brings; Helix orchestrates around
  it.
- **Keep the core project-agnostic.** Domain knowledge belongs in
  `projects/<name>/` overlays, not in the core. Guard against drift.

## Schema and models

State record types live in `schema/helix.yaml` (LinkML) — the single source of
truth. `helix/models.py` is **generated**; do not hand-edit it. After changing
the schema:

```bash
uv run gen-pydantic schema/helix.yaml > helix/models.py
```

## Build / test / format

Lightweight; runs fine on a login node (no SLURM needed).

```bash
uv sync                        # environment (Python >= 3.13)
uv run ruff check --fix . && uv run ruff format .   # BEFORE staging
uv run pytest                  # the surrogate oracle baseline — must stay green
git add <specific paths>       # never -A / . / *
git commit -m "type(scope): ..."   # conventional; no AI co-author trailer
git push origin main
```

The test suite **is** Helix's own surrogate oracle. Keep it green and grow it
with each phase — a failing baseline is a broken backpressure signal. Most
modules raise `NotImplementedError` by design until their bootstrap phase lands;
do not stub them with fake passing behavior.

## Self-hosting goal

The near-term milestone is for Helix to drive its own development through its
own loop. Build toward that: clean test oracle, small verifiable task units,
state on disk.
