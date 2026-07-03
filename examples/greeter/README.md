# greeter — the smallest end-to-end run

A dependency-free smoke example for the loop: a sealed two-task plan, a
haiku-tier Claude Code worker, and stdlib-only gates. Use it to iterate on the
harness in a scratch directory before dogfooding on a real project.

```bash
# Copy out of the repo so the run's sessions/ and generated files stay scratch.
cp -r examples/greeter /tmp/greeter-run
uv run helix run /tmp/greeter-run
```

What you should see: the worker's live train-of-thought, then after each
iteration a progress line — task bar, done/total, iteration, elapsed, and the
mechanical ETA. The run passes when `test_greeter` is green and every plan
checkbox is checked.

Useful variations:

```bash
uv run helix run /tmp/greeter-run --model sonnet   # override every task's model
uv run helix run /tmp/greeter-run --quiet          # verdict + exit code only
uv run helix status /tmp/greeter-run               # chain, verdicts, findings
uv run helix watch /tmp/greeter-run                # replay the worker trace
```

If a run is cut off (token/usage limit, ^C, crash) it exits with code 3 and
prints the resume line — rerun with `-c` and the worker continues the
conversation it was cut from:

```bash
uv run helix run /tmp/greeter-run -c
```
