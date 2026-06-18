---
name: explore-codebase
description: Understand an unfamiliar codebase fast without reading every file. Use when asked "how does X work", "where is X", "trace the X flow", "summarize the data model for X", or to deep-dive a module. Greps first, reads only what matters, delegates verbose deep dives to a subagent, and keeps a scratchpad so findings survive long sessions.
---

# Explore a codebase

A repeatable workflow for understanding a large, unfamiliar repository **without
overflowing the context window or forgetting earlier findings**. This is the
packaged version of the Developer Productivity Agent (Step 5).

## Principles

1. **Search before you read.** Use Grep to locate symbols/keywords, Glob for
   file patterns, and Read **only** the specific files that matter. Follow
   imports from there. Never read the whole repo or dump files you don't need.
2. **Ground conventions in docs.** Before asserting a convention (token TTLs,
   how auth works, how money is stored), check the project's docs/reference and
   cite it. Prefer documented facts over guesses.
3. **Delegate deep dives.** For a target that needs verbose digging across many
   files, spawn a subagent (the `Explore` agent) with one focused target. It
   absorbs the verbosity and returns a short summary, keeping your context clean.
4. **Persist findings.** Keep a scratchpad file (`SCRATCHPAD.md`). After working
   something out, append a short titled note. At the start of any follow-up,
   re-read the scratchpad to recover findings that may have left your context.
5. **Plan vs direct.** Exploring and explaining are read-only. Only make a direct
   edit when explicitly asked for a small, well-scoped change.

## How to answer "how does X work"

1. If this is a follow-up, **read the scratchpad first**.
2. **Grep** for X's entry points (route, handler, exported symbol).
3. **Glob/Read** only the relevant files; **follow imports across files** to
   trace the real flow end to end.
4. **Check the docs** to confirm conventions; cite the reference.
5. **Explain** the traced flow concretely, citing `path:line`.
6. **Save** the key finding to the scratchpad so the next question can reuse it.

## Anti-patterns

- Reading dozens of files "to be safe" instead of grepping first.
- Pulling a verbose deep-dive into the main context instead of delegating it.
- Re-deriving something you already figured out earlier in the session (read the
  scratchpad instead).
- Editing files while you're only supposed to be exploring.

## Reference implementation

The full Claude Agent SDK build of this workflow lives in this project
(`agents.py`, `docs_server.py`, `scratchpad.py`, `main.py`) with a sample repo
under `sample_app/`. Run `python main.py` to see it explore the password-reset
flow, the orders data model, and the auth middleware.
