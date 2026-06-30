# Helix

**A long-horizon agent orchestrator.** Helix wraps a native agent worker inside
a deterministic outer loop with three disciplined phases — **plan, implement,
judge**. The loop is dumb; the worker is smart. Durable intelligence lives in
plain-text artifacts and git history, not in a long conversation.

> The name evokes the iterative spiral where each turn advances toward a
> converged result — and the helical fields and long campaigns of fusion work.

## The thesis

Long-running agents are **recoverable workflows, not long conversations.** The
agent is a disposable worker; the durable record is the asset. Helix is not a
smarter agent — it is the institutional memory and the verification spine that
native agent CLIs lack. It is project-agnostic: a shared core serves many
repositories, with per-project knowledge layered on as data.

## Design choices (the fixed points)

1. **Dumb orchestration, smart worker.** The loop composes prompts from files,
   invokes the worker, enforces caps and gates, and manages state. All model
   judgment stays in the worker. We never reimplement the worker's tools.
2. **Phase separation with fresh context.** Plan, implement, and judge are
   distinct invocations that hand off through files, never an accumulating
   conversation. The judge is always separate — a worker never declares its own
   work done.
3. **Markdown-and-files as truth; HTML as a rendered lens.** All state and
   provenance are plain text committed to git. Human review surfaces are
   projections generated on demand.
4. **The human's seat is the plan phase.** Planning is interactive and
   high-judgment; execution is autonomous. The agreed plan is a signed contract.
5. **A tiered completion oracle.** Done is decided by evidence against criteria.
   Fast *surrogate* checks run every iteration as backpressure; slow or physical
   *blocking* gates pause the loop and wait for human ground truth.
6. **Provenance and session chaining are first-class.** Every run is a
   self-contained, human-sortable session referencing its predecessor. Findings
   are age- and condition-stamped. This is the lab notebook.
7. **Parallel where idempotent, serial at the gate.** Read/draft work fans out;
   verification and commits-to-shared-state are serialized.
8. **Project-agnostic core, project-specific data.** Loop logic and base phase
   contracts are shared and versioned; domain knowledge is a small overlay.
   Drift between projects is the chief long-term risk and is designed against.

## Relationship to reckon

[reckon](https://github.com/Simon-McIntosh/reckon) provides HTML plan skills and
MCP tools — these belong to the **worker's native channel**. Helix is the
**orchestration channel** around the worker. They compose, they do not merge:
Helix sets the working context and lets the worker discover and use reckon on
its own; reckon's HTML capability is the rendering layer Helix calls to project
its markdown state into a human-review surface. Helix never absorbs reckon, and
stays usable in projects that have none.

## Layout

```
helix/            # the project-agnostic core (the dumb loop + phase contracts)
  cli.py            # `helix` entry point
  loop.py           # the outer loop: plan->implement->judge, caps, gates
  phases/           # plan / implement / judge phase contracts
  worker.py         # native-worker adapter — no tool reimplementation
  session.py        # session ids, predecessor chaining, provenance
  oracle.py         # tiered completion oracle (surrogate vs blocking)
  state.py          # markdown+frontmatter state substrate
  models.py         # pydantic models generated from schema/helix.yaml
prompts/          # base phase prompts (project-agnostic)
projects/         # per-project data overlays (glossary, gates, specs)
sessions/         # runtime session artifacts — the committed lab notebook
schema/           # LinkML schema (source of truth for state records)
docs/             # markdown design (specs/) + reckon HTML plan lens
tests/            # surrogate oracle baseline
```

## Quickstart

```bash
uv sync                       # create the environment (Python >= 3.13)
uv run helix --help           # see the CLI surface
uv run pytest                 # run the surrogate oracle baseline
```

To regenerate the data models after editing the schema:

```bash
uv run gen-pydantic schema/helix.yaml > helix/models.py
```

## Status

Bootstrap. The CLI surface and module contracts are scaffolded; the loop is
being built phase by phase (see `docs/specs/`). The near-term milestone is
**self-hosting** — Helix driving its own development through its own loop.

## License

Released under [CC BY-ND 4.0](LICENSE). © Simon McIntosh.
