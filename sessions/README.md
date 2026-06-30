# Sessions — the durable lab notebook

Every Helix run is a self-contained session committed to git. Sessions are the
primary multi-year asset: they record what was done, what was verified, and
under what conditions each claim held.

- **Ids are human-sortable:** `YYYYMMDDTHHMMSSZ-<slug>` (UTC). Lexical order
  equals chronological order, so the directory listing *is* the campaign
  timeline.
- **Sessions chain:** each session names its predecessor, forming a campaign
  thread that can be walked backwards over years.
- **Findings are stamped:** every durable claim carries the date it was observed
  and the conditions under which it was true. Read-time freshness matters — an
  old finding is context, not gospel.

```
sessions/
  20260630T101500Z-bootstrap-p1/
    session.md       # frontmatter (id, phase, predecessor, verdict) + narrative
    evidence/        # test output, logs, metrics, screenshots
    findings.md      # age- and condition-stamped findings
```

This directory is intentionally **not** gitignored — the notebook is the asset.
The schema for session/finding records is defined in `schema/helix.yaml`.
