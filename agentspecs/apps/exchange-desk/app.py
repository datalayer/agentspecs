# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Exchange Desk: a company to people's own agents, written in Python
(PAP_DATALAYER E-02; AGENT_PROTOCOLS PI-42).

Shipped at its own domain, it answers before anybody signs in, lets people
sign in with their Datalayer account, and proposes an exchange in its
Maker's words: ``orders.exchange``, done by its own ``exchange_order`` once
the person approves its exact terms, and once only.

Decided 2026-10-13 (the user): ``exchange_order`` exchanges against the
hosted Manzanita, the test shop at ``manzanita.examples.datalayer.run``
(services' counterparts): its back office takes the exchange of its one
order, ``ord_7Hk2``, keyed by the confirmed operation's ticket, so a retry
is never a second exchange. Fake data, reset when Manzanita restarts.

Its Appspec, ``exchange-desk.yaml`` beside this folder, is what
``loop apps build`` writes from this file; agent-runtimes' tests build it
again and compare, so that the two never drift.

What was verified, and how, is said in its spec (``tests.verified``), on its
card and on its page.
"""

import uuid
from typing import Any

import httpx

from agent_runtimes.loop.apps import Application
from agent_runtimes.loop.apps.pap_company import current_pap_turn

#: The hosted Manzanita's back office: where its exchanges are done.
MANZANITA_EXCHANGES = "https://manzanita.examples.datalayer.run/back-office/exchanges"

app = Application.from_spec(
    {
        "schema": "loop.app/v1",
        "id": "exchange-desk",
        "version": "0.0.2",
        "name": "Exchange Desk",
        "kind": "chat",
        "description": (
            "Answers people's own agents about their orders and exchanges them, "
            "each exchange proposed with its exact terms and done once the person "
            "approves."
        ),
        "owner": "Datalayer <info@datalayer.io>",
        "agent": "cog-crawler:0.0.1",
        "instructions": (
            "You are a shop's desk for people's own agents. Answer what anybody may "
            "ask before they sign in; read an order only for its signed-in owner. "
            "When an exchange is asked for, give its terms: the shop proposes it, "
            "the person approves it, and exchange_order does it."
        ),
        # The protocols it speaks: its `pap` block is refused unless listed here.
        "protocols": ["pap"],
        "pap": {"profile": "draft-01"},
        "interface": {
            "layout": "chat",
            "accent": "violet",
            "welcome": (
                "The desk of a shop, for people's own agents: ask about an order, "
                "and exchange it with your approval."
            ),
        },
        "tests": {
            "ready_at": 0.8,
            "cases": [
                {
                    "ask": "Do you exchange jackets?",
                    "expect": "It answers without anybody signed in, and reads no order.",
                },
                {
                    "ask": "Exchange order ord_7Hk2 for size L.",
                    "expect": (
                        "It proposes the exchange in its own words with the order and "
                        "the size, and exchanges nothing before the person approves."
                    ),
                },
            ],
            "verified": {
                "live": [],
                "recorded": [
                    "Its exchange_order runs in process in agent-runtimes' tests against "
                    "a stand-in for Manzanita's back office: one exchange per confirmed "
                    "operation, a retry answered as already done.",
                ],
                "unverified": [
                    "Drilled on r1 on 13 October 2026: shipped at its own domain, it "
                    "answered a personal agent signed out, and a person signed in "
                    "through Datalayer granted orders:read and orders:write; but the "
                    "application was not told who had signed in (fixed in "
                    "agent-runtimes 1.5.11), and its exchange_order had no code yet. "
                    "Not drilled since.",
                ],
            },
        },
        "record": {
            "keep_for": "90_days",
            "include": ["conversations", "actions", "decisions", "approvals"],
        },
        "deployment": {"hosted": {"visibility": "private"}},
        "enabled": False,
        "unavailable_because": (
            "Its exchange_order is written against the hosted Manzanita and has not "
            "been drilled live yet."
        ),
        "tags": ["example", "companies", "python"],
        "emoji": "🏪",
    }
)

app.as_company(
    signed_out=True,
    interfaces=["agent", "openapi"],
    scopes=["orders:read", "orders:write"],
    extensions=["operations"],
    personal_agents="any",
)


@app.company_operation("orders.exchange", summary="Exchange order {order_id} for size {size}.")
@app.tool(does="write")
async def exchange_order(order_id: str, size: str) -> dict[str, Any]:
    """Exchanges an order for another size, once the person approved it."""

    turn = current_pap_turn()
    # Done once per confirmed operation: its ticket is Manzanita's idempotency
    # key. Approved in the Studio instead (its rule), each call is one exchange.
    key = turn.ticket if turn is not None and turn.ticket else f"studio-{uuid.uuid4().hex}"
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        answered = await client.post(
            MANZANITA_EXCHANGES,
            json={"order_id": order_id, "size": size, "idempotency_key": key},
        )
    said = answered.json()
    if answered.status_code != 200:
        raise ValueError(
            f"Manzanita did not exchange order {order_id} for size {size}: "
            f"{said.get('error') or answered.status_code}."
        )
    return said


app.rule("Exchange an order", applies_to=["exchange_order"], behaviour="ask_first")
