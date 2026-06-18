"""Main exploration agent + the Explore deep-dive subagent + options builder.

Maps to the build spec:
  * Step 1 - the main agent uses BUILT-IN tools (Grep -> Glob -> Read) and is told
    to search first and read only what matters, never the whole repo.
  * Step 2 - it has an MCP docs tool (mcp__docs__lookup_docs) to ground answers.
  * Step 3 - it delegates VERBOSE deep dives to the `Explore` subagent (Task),
    which returns only a summary so the main context stays clean.
  * Step 4 - it persists key findings via the scratchpad MCP tools and re-reads
    them when answering follow-ups.
  * Step 6 - it explores read-only and only makes tiny edits directly (Edit).
"""
from __future__ import annotations

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions

from docs_server import build_docs_server
from scratchpad import build_scratchpad_server

DOCS_TOOL = "mcp__docs__lookup_docs"
SCRATCH_WRITE = "mcp__scratch__scratchpad_write"
SCRATCH_READ = "mcp__scratch__scratchpad_read"


# --- The deep-dive subagent (Step 3) ----------------------------------------
# Does the verbose digging (reads many files, follows many imports) and returns
# ONLY a tight summary, so none of that verbosity lands in the parent context.
EXPLORE = AgentDefinition(
    description=(
        "Deep-dive explorer. Give it ONE focused target (a file, module or "
        "mechanism). It reads widely with Grep/Glob/Read and returns a concise "
        "structured summary - not raw file dumps."
    ),
    tools=["Grep", "Glob", "Read"],   # restricted: read-only exploration
    model="inherit",
    prompt=(
        "You are a deep-dive code EXPLORER. You are given ONE focused target.\n\n"
        "Method:\n"
        "1. Grep for the target's symbols/keywords to find where it lives.\n"
        "2. Glob/Read only the files that actually matter; follow imports.\n"
        "3. Read as much as you need - you are the one absorbing the verbosity so "
        "the parent agent doesn't have to.\n\n"
        "Then return a CONCISE summary (the parent only sees this, not your "
        "reads). Use these sections:\n"
        "  PURPOSE: one line.\n"
        "  KEY FILES: `path` - what it does (the few that matter).\n"
        "  HOW IT WORKS: 3-6 bullets tracing the mechanism across files.\n"
        "  GOTCHAS: edge cases, security notes, surprises (or 'none found').\n"
        "Cite concrete `path:line`-style references. Do NOT paste whole files. "
        "Keep it under ~250 words - it must fit cleanly in the parent's context."
    ),
)


# --- The main exploration agent ----------------------------------------------
MAIN_SYSTEM_PROMPT = """\
You are a CODEBASE EXPLORATION agent helping an engineer understand an
unfamiliar repository FAST, without reading every file. Your working directory
is the repo root.

Core discipline (this is the whole point - do not skip it):
  - EXPLORE INCREMENTALLY. Start with Grep to locate where something lives, use
    Glob for file patterns, and Read ONLY the specific files that matter. Follow
    imports from there. Never read the whole repo or dump large files you don't
    need.
  - GROUND YOUR ANSWERS. Before explaining a convention (token TTLs, how auth
    works, how money is stored), call `{DOCS_TOOL}` and cite the doc id(s) you
    used. Prefer documented facts over guesses.
  - DELEGATE DEEP DIVES. When a question needs verbose digging through many
    files (e.g. "deep-dive the auth middleware"), spawn the `Explore` subagent
    with the Task tool (subagent_type="Explore") and a focused target. It does
    the heavy reading and returns a short summary, keeping YOUR context clean.
    Paste anything it needs into the Task prompt - subagents share your files but
    not your conversation.
  - REMEMBER ACROSS THE SESSION. After you work something out, save the key
    finding with `{SCRATCH_WRITE}` (short title + a few lines). At the START of
    any follow-up question, call `{SCRATCH_READ}` first to recover earlier
    findings that may have left your context window. Treat the scratchpad as your
    durable memory.
  - PLAN vs DIRECT (mode discipline). Exploration and explanation are read-only:
    Grep/Glob/Read/Task/docs/scratchpad only - never edit while exploring. Make a
    direct Edit ONLY when the user explicitly asks for a small, well-scoped
    change.

Answering "how does X work":
  1. (follow-up?) scratchpad_read to recover prior findings.
  2. Grep for X's entry points; Glob/Read only the relevant files; follow imports
     across files to trace the real flow.
  3. lookup_docs to confirm conventions; cite the doc id.
  4. Explain the flow concretely, citing `path:line` and the files you traced.
  5. scratchpad_write the key finding so a later question can reuse it.

Be accurate and traced. If you didn't verify something in the code or docs, say
so rather than guessing.
""".format(
    DOCS_TOOL=DOCS_TOOL, SCRATCH_WRITE=SCRATCH_WRITE, SCRATCH_READ=SCRATCH_READ
)


def build_options(cwd: str, model: str | None,
                  max_budget_usd: float) -> ClaudeAgentOptions:
    """Assemble ClaudeAgentOptions for the main exploration agent."""
    return ClaudeAgentOptions(
        system_prompt=MAIN_SYSTEM_PROMPT,
        cwd=cwd,                          # built-in tools operate on the sample repo
        # Built-in exploration tools + delegate + (rarely) a direct edit, plus
        # the two in-process MCP servers' tools.
        tools=[
            "Grep", "Glob", "Read", "Task", "Edit",
            DOCS_TOOL, SCRATCH_WRITE, SCRATCH_READ,
        ],
        agents={"Explore": EXPLORE},
        mcp_servers={
            "docs": build_docs_server(),
            "scratch": build_scratchpad_server(),
        },
        model=model,                      # None -> CLI default
        permission_mode="bypassPermissions",   # non-interactive subprocess
        setting_sources=[],               # isolation: ignore filesystem settings
        strict_mcp_config=True,           # only our in-process servers
        max_turns=60,
        max_budget_usd=max_budget_usd,    # safety cap
    )
