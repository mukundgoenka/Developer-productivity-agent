"""Offline checks - no API key, no model, no cost.

Verifies the wiring the live demo depends on:
  * the in-process MCP tools (docs lookup + scratchpad write/read) actually work,
  * the docs corpus matches the topics the agent will ask for,
  * the sample codebase has the files the example prompts trace through,
  * the agent options assemble with the expected tools/subagent.

Run: python test_offline.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import docs_server
import scratchpad
from agents import EXPLORE, build_options

HERE = Path(__file__).parent
SAMPLE = HERE / "sample_app"

checks: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    checks.append((bool(cond), label))


async def call(tool_fn, args):
    """Invoke an @tool (it exposes a .handler coroutine) and return its text."""
    res = await tool_fn.handler(args)
    parts = res.get("content", [])
    return " ".join(p.get("text", "") for p in parts if isinstance(p, dict)), res


async def main() -> int:
    # --- 1. docs server matches the topics the agent will ask about ----------
    docs_server.reset_ledger()
    for topic, expect_id in [
        ("password reset", "SHOPLINE-DOC-AUTH-001"),
        ("auth middleware", "SHOPLINE-DOC-AUTH-002"),
        ("orders data model", "SHOPLINE-DOC-DATA-001"),
        ("conventions", "SHOPLINE-DOC-CONV-001"),
    ]:
        text, _ = await call(docs_server.lookup_docs, {"topic": topic})
        check(expect_id in text, f"docs: {topic!r} -> {expect_id}")
    text, _ = await call(docs_server.lookup_docs, {"topic": "xyzzy-nonsense"})
    check("No documentation matched" in text, "docs: unknown topic handled gracefully")
    check(len(docs_server.LOOKUPS) == 5, "docs: lookups logged to ledger")

    # --- 2. scratchpad write then read round-trips ---------------------------
    tmp = HERE / "_test_scratch.md"
    scratchpad.set_path(tmp)
    scratchpad.reset(fresh=True)
    r_empty, _ = await call(scratchpad.scratchpad_read, {})
    check("empty" in r_empty.lower(), "scratchpad: empty before any write")
    await call(scratchpad.scratchpad_write,
               {"title": "Reset TTL", "note": "Tokens expire after 30 minutes."})
    await call(scratchpad.scratchpad_write,
               {"title": "Money", "note": "Stored as integer cents."})
    r_full, _ = await call(scratchpad.scratchpad_read, {})
    check("Reset TTL" in r_full and "Money" in r_full, "scratchpad: notes persist")
    check("30 minutes" in r_full, "scratchpad: note body persists")
    check(len(scratchpad.WRITES) == 2, "scratchpad: writes logged to ledger")
    scratchpad.set_path(tmp)
    scratchpad.reset(fresh=True)  # cleanup
    if tmp.exists():
        tmp.unlink()

    # --- 3. sample codebase has the files the prompts trace through ----------
    must_exist = [
        "src/routes/auth.js",
        "src/controllers/authController.js",
        "src/services/tokenService.js",
        "src/services/emailService.js",
        "src/models/resetToken.js",
        "src/middleware/authMiddleware.js",
        "src/models/order.js",
        "src/db/schema.sql",
    ]
    for rel in must_exist:
        check((SAMPLE / rel).exists(), f"sample_app has {rel}")
    schema = (SAMPLE / "src/db/schema.sql").read_text(encoding="utf-8")
    check("CREATE TABLE orders" in schema and "order_items" in schema,
          "schema.sql defines orders + order_items")
    ts = (SAMPLE / "src/services/tokenService.js").read_text(encoding="utf-8")
    check("RESET_TOKEN_TTL_MINUTES = 30" in ts, "tokenService TTL is 30 min")

    # --- 4. options assemble with the expected wiring ------------------------
    opts = build_options(str(SAMPLE), model="claude-sonnet-4-6", max_budget_usd=1.0)
    for t in ["Grep", "Glob", "Read", "Task", "mcp__docs__lookup_docs",
              "mcp__scratch__scratchpad_write", "mcp__scratch__scratchpad_read"]:
        check(t in opts.tools, f"options expose tool {t}")
    check("Explore" in (opts.agents or {}), "options register the Explore subagent")
    check(set(EXPLORE.tools) == {"Grep", "Glob", "Read"},
          "Explore subagent is restricted to read-only tools")
    check(opts.permission_mode == "bypassPermissions", "options run non-interactively")

    # --- report --------------------------------------------------------------
    passed = sum(1 for ok, _ in checks if ok)
    print(f"\nOffline checks: {passed}/{len(checks)} passed\n")
    for ok, label in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    failed = [l for ok, l in checks if not ok]
    if failed:
        print(f"\n{len(failed)} FAILED")
        return 1
    print("\nAll offline checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
