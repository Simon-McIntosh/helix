"""The three phase contracts: plan, implement, judge.

Each phase is a distinct worker invocation with a fresh context. Phases hand off
through files, never through an accumulating conversation. The judge is always a
separate invocation from the worker — a worker never declares its own work done.
"""
