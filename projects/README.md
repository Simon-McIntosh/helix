# Project overlays

Helix is **project-agnostic core + project-specific data**. The loop logic and
the base phase contracts (`prompts/`, `helix/`) are a shared, versioned core.
Everything a single project knows that the core does not lives in the
*project's own run directory* as a small overlay, layered over the core at
compose time:

```
<project>/                     # the run directory (holds helix.yaml)
  helix.yaml                   # worker command/model, caps, oracle gates
  PLAN.md                      # the agreed plan (checkbox tasks)
  prompts/
    overlay.plan.md            # appended to the core plan contract
    overlay.implement.md       # appended to the core implement contract
    overlay.judge.md           # appended to the core judge contract
  sessions/                    # the committed lab notebook
```

**Overlays extend; they never fork.** An extension is *appended* after the
packaged contract (`helix/overlay.py:resolve_prompt`). A project that ships a
full `prompts/<phase>.md` replacement has forked the core contract — resolution
ignores it and `helix check <project>` flags it, along with restated core
headings, oversized overlays, duplicate or unrunnable gates, and a missing plan
file. **Drift between projects is the chief long-term risk**; keep overlays
small and diff-like, and push anything general back into the core.

This `projects/` directory is the overlay home for projects hosted alongside
Helix itself. Self-hosting is the sanctioned identity case: the repo root is
its own project directory, so the packaged `prompts/` *are* its contracts — no
overlay files, no fork.
