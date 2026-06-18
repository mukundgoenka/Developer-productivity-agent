# Developer Productivity Agent

An exploration agent (built on the **Claude Agent SDK**, Python) that helps an
engineer understand a large, unfamiliar codebase **fast — without reading every
file**. It searches before it reads, grounds its answers in documentation,
offloads verbose deep-dives to a subagent, and writes findings to a scratchpad
so long sessions stay coherent.

It explores a bundled sample repo (`sample_app/` — a small Express + SQLite
storefront API), but the workflow is packaged as a reusable Claude Code skill so
it works on any repo.

## The problem it solves

A new codebase is overwhelming. Reading everything overflows the context window,
and in a long session the agent starts forgetting what it learned earlier. This
agent attacks both: **incremental search** keeps reads small, a **subagent**
absorbs verbose digging, and a **scratchpad** is durable memory.

## How it works (maps to the 6-step build)

| Step | Mechanism | Where |
|---|---|---|
| 1. Use built-in tools well | Agent told to **Grep → Glob → Read only what matters**, follow imports | `agents.py` (system prompt), `tools=["Grep","Glob","Read",...]` |
| 2. MCP documentation server | In-process MCP server `mcp__docs__lookup_docs` serves curated, **citable** reference docs | `docs_server.py` |
| 3. Subagent for deep dives | `Explore` `AgentDefinition` (read-only tools) does verbose digging, returns only a summary | `agents.py` → `EXPLORE` |
| 4. Scratchpad | In-process MCP server `scratchpad_write` / `scratchpad_read` persists findings to `SCRATCHPAD.md` | `scratchpad.py` |
| 5. Package as a skill | Reusable Claude Code skill any teammate can invoke | `.claude/skills/explore-codebase/SKILL.md` |
| 6. Plan vs direct | Explore read-only; make a direct `Edit` only when explicitly asked | `agents.py` (system prompt) |

The main agent gets `Grep, Glob, Read, Task, Edit` plus the two MCP servers. The
`Explore` subagent is **restricted to `Grep, Glob, Read`** — it can dig but not
change anything, and its reads never land in the parent's context.

## Run it

```bash
pip install -r requirements.txt        # claude-agent-sdk

python test_offline.py                 # 30 checks, no API key / no cost

python main.py                         # all 3 example prompts in ONE session
python main.py --demo 1                # just the password-reset flow
python main.py --demo 2                # just the orders data model
python main.py --demo 3                # just the subagent deep-dive
python main.py --ask "where is login handled?"
python main.py --model default         # use the CLI's default model
```

Live mode drives the real model, so it needs Claude auth (`ANTHROPIC_API_KEY` or
an existing `claude` login) and the Claude Code CLI. Default model
`claude-sonnet-4-6`; ~$0.10 per prompt. A `--budget` cap (default $2) stops
runaway sessions.

## The three example prompts (verified)

1. **"How does the password-reset flow work here?"** — greps first, then reads
   only `routes/auth.js → controllers/authController.js → services/tokenService.js
   + emailService.js`, traces the two-step flow, cites doc `SHOPLINE-DOC-AUTH-001`,
   saves a finding.
2. **"Summarize the data model for orders."** — traces across `db/schema.sql` +
   `models/order.js` (users → orders → order_items), saves notes to the scratchpad.
3. **"Deep-dive the auth middleware in a subagent, then return a concise parent
   summary and persist key findings in scratchpad."** — spawns the `Explore`
   subagent (which does 10+ reads internally), returns a tight summary, and writes
   it to `SCRATCHPAD.md`. The parent's own turn stays tiny — proof the deep dive
   didn't bloat its context.

## What the runner shows

A live trace of every tool call (Grep/Glob/Read/Task/docs/scratchpad), then a
**docs-consulted ledger** (what grounded the answers) and the **scratchpad
contents** (findings that survive the session).

## Files

```
agents.py          main exploration agent + Explore subagent + options builder
docs_server.py     in-process MCP docs server (mcp__docs__lookup_docs)
scratchpad.py      in-process MCP scratchpad server (write/read)
main.py            runner: 3 example prompts, live trace, post-run ledgers
test_offline.py    30 offline checks (tools, docs, scratchpad, sample app, wiring)
sample_app/        the codebase being explored (Express + SQLite storefront API)
.claude/skills/explore-codebase/SKILL.md   reusable Claude Code skill (Step 5)
```
