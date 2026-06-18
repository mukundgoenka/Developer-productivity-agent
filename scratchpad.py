"""In-process MCP SCRATCHPAD server (Step 4 of the spec).

The problem this solves: in a long exploration session the agent's context
window fills up and early findings fall out - it 'forgets' what it learned. The
scratchpad is durable external memory: the agent writes short titled notes to a
real file (SCRATCHPAD.md) and can re-read them later, so findings survive even
after they've scrolled out of the context window.

Implemented as two tools rather than raw Write/Read so the intent is explicit in
the trace and notes are always appended (never accidentally overwritten).
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server, tool

# Set by the runner before a session so all notes land in one known file.
SCRATCHPAD_PATH = Path(__file__).parent / "SCRATCHPAD.md"

WRITES: list[dict] = []   # ledger of notes saved this session


def set_path(path: Path) -> None:
    global SCRATCHPAD_PATH
    SCRATCHPAD_PATH = Path(path)


def reset(fresh: bool = True) -> None:
    """Start a clean scratchpad for a new session."""
    WRITES.clear()
    if fresh and SCRATCHPAD_PATH.exists():
        SCRATCHPAD_PATH.unlink()


def _log(msg: str) -> None:
    print(f"      ~ [scratchpad] {msg}", file=sys.stderr, flush=True)


@tool(
    "scratchpad_write",
    "Persist a key finding to the scratchpad file so it survives even if it "
    "later falls out of the context window. Provide a short 'title' and the "
    "'note' body. Notes are appended, never overwritten.",
    {"title": str, "note": str},
)
async def scratchpad_write(args: dict) -> dict:
    title = (args.get("title") or "untitled").strip()
    note = (args.get("note") or "").strip()
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"\n## {title}  _(saved {ts})_\n\n{note}\n"
    with SCRATCHPAD_PATH.open("a", encoding="utf-8") as fh:
        if SCRATCHPAD_PATH.stat().st_size == 0:
            fh.write("# Exploration scratchpad\n")
        fh.write(entry)
    WRITES.append({"title": title, "chars": len(note)})
    _log(f"saved note {title!r} ({len(note)} chars)")
    return {"content": [{"type": "text",
                         "text": f"Saved note '{title}' to scratchpad."}]}


@tool(
    "scratchpad_read",
    "Re-read everything saved to the scratchpad so far. Use this at the START of "
    "answering a follow-up question to recover findings from earlier in the "
    "session that may have left the context window.",
    {},
)
async def scratchpad_read(args: dict) -> dict:
    if not SCRATCHPAD_PATH.exists() or SCRATCHPAD_PATH.stat().st_size == 0:
        _log("read -> empty")
        return {"content": [{"type": "text",
                             "text": "Scratchpad is empty (no notes saved yet)."}]}
    text = SCRATCHPAD_PATH.read_text(encoding="utf-8")
    _log(f"read -> {len(text)} chars")
    return {"content": [{"type": "text", "text": text}]}


def build_scratchpad_server():
    """Create the in-process MCP scratchpad server.

    Server key is 'scratch', so tools are `mcp__scratch__scratchpad_write` and
    `mcp__scratch__scratchpad_read`.
    """
    return create_sdk_mcp_server(name="scratch", version="1.0.0",
                                 tools=[scratchpad_write, scratchpad_read])
