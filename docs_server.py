"""In-process MCP DOCUMENTATION server (Step 2 of the spec).

Why this exists: when the agent explains how something works, it shouldn't
*guess* at conventions (token TTLs, what 'Bearer' means, how money is stored).
This server serves a small set of curated "official docs" for the ShopLine
codebase so explanations can be grounded in - and cite - real reference material
instead of being invented.

It runs inside this Python process (no subprocess/IPC), which also lets us log
every lookup to a ledger so the runner can show what was actually consulted.
"""
from __future__ import annotations

import sys

from claude_agent_sdk import create_sdk_mcp_server, tool

# Provenance ledger: every docs lookup the agent (or a subagent) made.
LOOKUPS: list[dict] = []


def reset_ledger() -> None:
    LOOKUPS.clear()


def _log(msg: str) -> None:
    print(f"      ~ [docs] {msg}", file=sys.stderr, flush=True)


# --- The curated documentation corpus ---------------------------------------
# Each entry has a stable doc id (used as the citation), a title, keywords for
# fuzzy matching, and the body. Keep these factually aligned with sample_app/.
DOCS: list[dict] = [
    {
        "id": "SHOPLINE-DOC-AUTH-001",
        "title": "Password reset flow",
        "keywords": ["password", "reset", "forgot", "token", "email", "recover"],
        "body": (
            "Password reset is a two-step flow.\n"
            "Step 1 (POST /auth/forgot-password): the user submits an email. If an "
            "account exists, a reset token is minted and emailed as a link. The "
            "endpoint ALWAYS returns 200 (even for unknown emails) to prevent "
            "account enumeration.\n"
            "Step 2 (POST /auth/reset-password): the user submits the token + a new "
            "password. The token is verified, the password is re-hashed with bcrypt, "
            "and the token is consumed (single-use).\n"
            "Reset tokens are random 32-byte values, expire after "
            "RESET_TOKEN_TTL_MINUTES (30 minutes), and are stored only as a SHA-256 "
            "hash so a leaked database cannot be replayed."
        ),
    },
    {
        "id": "SHOPLINE-DOC-AUTH-002",
        "title": "Authentication middleware (Bearer JWT)",
        "keywords": ["auth", "middleware", "jwt", "bearer", "token", "requireauth",
                     "requirerole", "session", "login"],
        "body": (
            "Protected routes are guarded by requireAuth, which expects an "
            "'Authorization: Bearer <jwt>' header. The JWT is signed at login with "
            "HS256 and a 1-hour expiry; its `sub` claim is the user id and `role` "
            "carries the role. requireAuth verifies the token, loads the user, and "
            "attaches it as req.user for downstream handlers.\n"
            "requireRole(role) is a factory guard used AFTER requireAuth to enforce "
            "a specific role (e.g. 'admin') and returns 403 otherwise."
        ),
    },
    {
        "id": "SHOPLINE-DOC-DATA-001",
        "title": "Orders data model",
        "keywords": ["order", "orders", "data", "model", "schema", "order_items",
                     "line", "items", "money", "cents", "status"],
        "body": (
            "The orders domain spans three tables. `users` owns orders. `orders` is "
            "the header (one row per order) with a status in "
            "{pending, paid, shipped, delivered, cancelled}, a total_cents integer, "
            "and a currency. `order_items` holds line items (many per order), each "
            "with product_id, quantity (CHECK > 0) and unit_price_cents captured at "
            "purchase time.\n"
            "Money is ALWAYS stored as integer cents, never floats. order_items "
            "cascade-delete with their order."
        ),
    },
    {
        "id": "SHOPLINE-DOC-CONV-001",
        "title": "Codebase conventions",
        "keywords": ["convention", "conventions", "structure", "layout", "style",
                     "routes", "controllers", "services", "models"],
        "body": (
            "Layering: routes/ define URLs and delegate to controllers/. "
            "controllers/ hold request logic and call services/ (cross-cutting "
            "behaviour like tokens/email) and models/ (one wrapper per DB table). "
            "To trace any feature, start at the route that owns its URL prefix and "
            "follow the imports downward."
        ),
    },
]


def _match(topic: str) -> list[dict]:
    t = topic.lower().strip()
    if not t:
        return []
    scored = []
    for d in DOCS:
        score = 0
        if t in d["title"].lower():
            score += 5
        for kw in d["keywords"]:
            if kw in t or t in kw:
                score += 2
        # any shared word
        for word in t.replace("-", " ").split():
            if word in d["keywords"] or word in d["title"].lower():
                score += 1
        if score:
            scored.append((score, d))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [d for _, d in scored]


@tool(
    "lookup_docs",
    "Look up official ShopLine reference documentation for a topic (e.g. "
    "'password reset', 'auth middleware', 'orders data model', 'conventions'). "
    "Returns matching docs, each with a citable doc id, so explanations can be "
    "grounded in real reference material instead of guessed.",
    {"topic": str},
)
async def lookup_docs(args: dict) -> dict:
    topic = (args.get("topic") or "").strip()
    matches = _match(topic)
    LOOKUPS.append({"topic": topic, "matched": [m["id"] for m in matches]})

    if not matches:
        _log(f"topic={topic!r} -> no matching docs")
        return {
            "content": [{
                "type": "text",
                "text": (f"No documentation matched {topic!r}. Available topics: "
                         + ", ".join(d["title"] for d in DOCS)),
            }]
        }

    _log(f"topic={topic!r} -> {[m['id'] for m in matches]}")
    out = []
    for d in matches[:3]:  # top few, don't dump the whole corpus
        out.append(f"[{d['id']}] {d['title']}\n{d['body']}")
    text = (
        "Cite the doc id(s) in square brackets when you use these.\n\n"
        + "\n\n---\n\n".join(out)
    )
    return {"content": [{"type": "text", "text": text}]}


def build_docs_server():
    """Create the in-process MCP docs server.

    Server key is 'docs', so the tool is exposed as `mcp__docs__lookup_docs`.
    """
    return create_sdk_mcp_server(name="docs", version="1.0.0", tools=[lookup_docs])
