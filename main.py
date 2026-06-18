"""Developer Productivity Agent - runner.

An exploration agent that understands an unfamiliar codebase FAST: it Greps to
locate things, Reads only what matters, grounds answers in an MCP docs server,
offloads verbose deep dives to an `Explore` subagent, and persists findings to a
scratchpad so long sessions stay coherent.

Usage:
    python main.py                 # run all 3 example prompts in ONE session
    python main.py --demo 1        # just prompt 1 (password-reset flow)
    python main.py --demo 2        # just prompt 2 (orders data model)
    python main.py --demo 3        # just prompt 3 (subagent deep-dive)
    python main.py --ask "..."     # your own question about the sample repo

By default all three run in a single shared session, so you can see the
scratchpad accumulate findings across questions (Step 4).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Make console output safe + readable on Windows terminals.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

import docs_server
import scratchpad
from agents import build_options

SAMPLE_APP = Path(__file__).parent / "sample_app"
SCRATCHPAD_PATH = Path(__file__).parent / "SCRATCHPAD.md"

# The subagent-spawning tool is surfaced as "Task" (older builds) or "Agent".
_SPAWN_TOOLS = {"Task", "Agent"}

# The three EXACT example prompts from the spec.
DEMOS = {
    "1": {
        "label": "password-reset flow",
        "prompt": "How does the password-reset flow work here?",
        "expect": "Greps first, then reads only the relevant files, traces across files.",
    },
    "2": {
        "label": "orders data model",
        "prompt": "Summarize the data model for orders.",
        "expect": "Traces across schema + model, saves notes to the scratchpad.",
    },
    "3": {
        "label": "auth middleware deep-dive",
        "prompt": ("Deep-dive the auth middleware in a subagent, then return a "
                   "concise parent summary and persist key findings in scratchpad."),
        "expect": "Delegates to the Explore subagent, summarizes, writes scratchpad.",
    },
}


def hr(char: str = "-") -> str:
    return char * 78


def short(text: str, n: int = 300) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + " ..."


class Trace:
    """Pretty-prints the agent's exploration as it streams."""

    def __init__(self) -> None:
        self.labels: dict[str, str] = {}
        self._open_spawns: set[str] = set()

    def route(self, msg) -> None:
        if isinstance(msg, SystemMessage):
            if msg.subtype == "init":
                model = (msg.data or {}).get("model", "?")
                print(f"[session] model={model}  cwd={SAMPLE_APP.name}")
            return

        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    if block.text.strip():
                        print(f"\n[AGENT] {short(block.text, 900)}")
                elif isinstance(block, ToolUseBlock):
                    self._tool_use(block)
            return

        if isinstance(msg, UserMessage):
            content = msg.content if isinstance(msg.content, list) else []
            for block in content:
                if isinstance(block, ToolResultBlock):
                    self._tool_result(block)
            return

        if isinstance(msg, ResultMessage):
            self._result(msg)

    def _tool_use(self, block: ToolUseBlock) -> None:
        inp = block.input or {}
        name = block.name
        if name in _SPAWN_TOOLS:
            sub = inp.get("subagent_type", "?")
            desc = inp.get("description") or short(inp.get("prompt", ""), 70)
            self.labels[block.id] = f"subagent:{sub}"
            self._open_spawns.add(block.id)
            print(f"   -> Task[{sub}] (deep dive) :: {short(desc, 90)}")
        elif name == "Grep":
            self.labels[block.id] = "Grep"
            print(f"   -> Grep  pattern={inp.get('pattern')!r}"
                  + (f" glob={inp.get('glob')!r}" if inp.get('glob') else ""))
        elif name == "Glob":
            self.labels[block.id] = "Glob"
            print(f"   -> Glob  {inp.get('pattern')!r}")
        elif name == "Read":
            self.labels[block.id] = "Read"
            print(f"   -> Read  {inp.get('file_path')}")
        elif name == "Edit":
            self.labels[block.id] = "Edit"
            print(f"   -> Edit  {inp.get('file_path')}  (direct change)")
        elif name == "mcp__docs__lookup_docs":
            self.labels[block.id] = "docs"
            print(f"   -> docs.lookup_docs(topic={inp.get('topic')!r})")
        elif name == "mcp__scratch__scratchpad_write":
            self.labels[block.id] = "scratchpad_write"
            print(f"   -> scratchpad.write(title={inp.get('title')!r})")
        elif name == "mcp__scratch__scratchpad_read":
            self.labels[block.id] = "scratchpad_read"
            print("   -> scratchpad.read()")
        else:
            self.labels[block.id] = name
            print(f"   -> {name}")

    def _tool_result(self, block: ToolResultBlock) -> None:
        self._open_spawns.discard(block.tool_use_id)
        label = self.labels.get(block.tool_use_id, "result")
        text = block.content
        if isinstance(text, list):
            text = " ".join(p.get("text", "") for p in text if isinstance(p, dict))
        flag = "ERR" if block.is_error else "OK "
        # Subagent summaries are the interesting part; show a bit more of them.
        n = 360 if label.startswith("subagent") else 160
        print(f"   <- [{flag}] {label}: {short(text, n)}")

    def _result(self, msg: ResultMessage) -> None:
        usage = msg.usage or {}
        toks = (usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        cost = f"${msg.total_cost_usd:.4f}" if msg.total_cost_usd else "n/a"
        print(f"\n   [turn done] turns={msg.num_turns} "
              f"in/out tokens={toks[0]}/{toks[1]} cost={cost}")


def post_run_report() -> None:
    """Show the durable side effects: docs consulted + scratchpad contents."""
    print("\n" + hr("="))
    print("DOCS CONSULTED (grounding ledger)")
    print(hr("="))
    if docs_server.LOOKUPS:
        for lk in docs_server.LOOKUPS:
            matched = ", ".join(lk["matched"]) or "(no match)"
            print(f"  lookup_docs(topic={lk['topic']!r}) -> {matched}")
    else:
        print("  (none)")

    print("\n" + hr("="))
    print(f"SCRATCHPAD  ({SCRATCHPAD_PATH.name}) - findings that survive the session")
    print(hr("="))
    if SCRATCHPAD_PATH.exists() and SCRATCHPAD_PATH.stat().st_size:
        print(SCRATCHPAD_PATH.read_text(encoding="utf-8").rstrip())
    else:
        print("  (empty - agent saved no notes)")
    print(hr())


async def run_session(prompts: list[dict], model: str | None, budget: float) -> None:
    # Fresh scratchpad + ledgers for a clean demo.
    scratchpad.set_path(SCRATCHPAD_PATH)
    scratchpad.reset(fresh=True)
    docs_server.reset_ledger()

    options = build_options(str(SAMPLE_APP), model, budget)
    trace = Trace()

    async with ClaudeSDKClient(options=options) as client:
        for i, spec in enumerate(prompts, 1):
            print("\n" + hr("#"))
            print(f"# PROMPT {i}: {spec['prompt']}")
            print(f"# (expect: {spec['expect']})")
            print(hr("#"))
            try:
                await client.query(spec["prompt"])
                async for msg in client.receive_response():
                    trace.route(msg)
            except Exception as exc:
                print(f"\n!! run error: {type(exc).__name__}: {exc}")

    post_run_report()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Developer Productivity Agent")
    p.add_argument("--demo", choices=["1", "2", "3"],
                   help="run a single example prompt (default: all three)")
    p.add_argument("--ask", help="ask your own question about the sample repo")
    p.add_argument("--model", default="claude-sonnet-4-6",
                   help="model (default claude-sonnet-4-6; 'default' = CLI default)")
    p.add_argument("--budget", type=float, default=2.0,
                   help="max USD per session (safety cap)")
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    model = None if args.model == "default" else args.model

    if args.ask:
        prompts = [{"label": "custom", "prompt": args.ask, "expect": "your question"}]
    elif args.demo:
        prompts = [DEMOS[args.demo]]
    else:
        prompts = [DEMOS["1"], DEMOS["2"], DEMOS["3"]]

    await run_session(prompts, model, args.budget)


if __name__ == "__main__":
    asyncio.run(main())
