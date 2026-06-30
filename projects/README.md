# Project overlays

Helix is **project-agnostic core + project-specific data**. The loop logic and
the base phase contracts (`prompts/`, `helix/`) are a shared, versioned core.
Everything a single project knows that the core does not — glossaries, oracle
gate definitions, specs, environment/boot notes, and phase-prompt extensions —
lives here as a small overlay layered over the core at runtime.

```
projects/
  <project-name>/
    overlay.plan.md        # appended to prompts/plan.md
    overlay.implement.md   # appended to prompts/implement.md
    overlay.judge.md       # appended to prompts/judge.md
    gates.yaml             # oracle gate definitions (surrogate | blocking)
    glossary.md            # domain terms the worker should know
```

**Drift between projects is the chief long-term risk.** Keep overlays small and
diff-like; push anything general back into the core. An anti-drift check
(bootstrap phase P4) guards the boundary so overlays cannot silently fork the
core contracts.
