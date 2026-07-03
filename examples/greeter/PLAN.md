---
id: 20260703T000000Z-plan
project: greeter
agreed_at: '2026-07-03T00:00:00+00:00'
---

# Plan

## Intent

A tiny, dependency-free greeting library — the smallest project that exercises
the whole loop: checkbox tasks, per-task model routing, a real surrogate gate,
and live progress. Stdlib only; two source files in this directory.

## Tasks

- [ ] Create `greeter.py` with `greet(name: str) -> str` returning
  `"Hello, <name>!"`; whitespace is stripped and an empty/blank name greets
  `"world"` (model: haiku)
- [ ] Create `test_greeter.py` covering the named, blank, and
  whitespace-padded cases with stdlib `unittest` (model: haiku)

## Oracle gates

- `tests` (surrogate): `python3 -m unittest -v test_greeter` passes.
- `tasks` (surrogate): every checkbox above is checked off.
