# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Customer Interview: a chat written in Python (LOOP §9, E-02).

It asks for consent before anything else, then what the interviewer wants to
learn; it answers each message through its agent inside a step; it saves an
insight from a button, and gives a structured result when the interview ends.

Its Appspec, ``customer-interview.yaml`` beside this folder, is what
``loop apps build`` writes from this file; agent-runtimes' tests build it
again and compare, so that the two never drift.

What was verified, and how, is said in its spec (``tests.verified``), on its
card and on its page.
"""

from agent_runtimes.loop.apps import Application, ChoiceQuestion, Session

app = Application.from_spec(
    {
        "schema": "loop.app/v1",
        "id": "customer-interview",
        "version": "0.0.1",
        "name": "Customer Interview",
        "kind": "chat",
        "description": (
            "Interviews a customer about what you want to learn, without leading "
            "questions, and turns the conversation into insights that each cite "
            "what was said."
        ),
        "owner": "Datalayer <info@datalayer.io>",
        "agent": "cog-customer-interviewer:0.0.1",
        "instructions": (
            "Ask one open question at a time, and never a leading one. Each insight "
            "quotes the interviewee's own words; nothing is inferred beyond them."
        ),
        "context": ["customer-research:0.0.1"],
        "interface": {
            "layout": "chat",
            "accent": "rose",
            "assistant": "cat",
            "welcome": (
                "I interview your customer. I ask for their consent first, then one "
                "open question at a time."
            ),
        },
        "tests": {
            "ready_at": 0.8,
            "cases": [
                {
                    "ask": "The interviewee declines to be recorded.",
                    "expect": "It thanks them, asks nothing more, and saves no insight.",
                },
                {
                    "ask": "We want to learn why people leave after the trial.",
                    "expect": (
                        "It asks open questions about the trial, one at a time, and none "
                        "that suggests an answer."
                    ),
                },
                {
                    "ask": "The interviewee says the price was fine but the setup took a week.",
                    "expect": (
                        "It follows up on the setup, and the insight it saves quotes "
                        "their words about it."
                    ),
                },
                {
                    "ask": "End the interview.",
                    "expect": (
                        "It gives the goal, the insights each with its quote, and the "
                        "questions left open."
                    ),
                },
            ],
            "verified": {
                "live": [
                    "Tried signed out in the browser from its example's page "
                    "(2026-10-04): the model answered. Its Python code did not run there.",
                ],
                "recorded": [
                    "Its code runs in process in Datalayer's own tests with a scripted "
                    "model: consent asked, a refusal honoured, a reply per message, an "
                    "insight saved, the result recorded.",
                ],
                "unverified": [
                    "Its code has not run with a real model: its agent was switched on "
                    "in the catalogue on 2026-10-06, and its tests have not been run.",
                ],
            },
        },
        "record": {
            "keep_for": "1_years",
            "include": ["conversations", "outputs", "feedback"],
        },
        "deployment": {"hosted": {"visibility": "private"}},
        "tags": ["example", "research", "python"],
        "icon": "comment-discussion",
        "emoji": "🎙️",
    }
)
app.starter("Trial churn", "Interview me about why I stopped after the trial.")
app.starter("Onboarding", "Interview me about my first week with the product.")
app.setting(
    "language",
    {"type": "string", "title": "Language", "enum": ["English", "French"], "default": "English"},
)
app.setting(
    "length", {"type": "integer", "title": "Questions", "minimum": 3, "maximum": 15, "default": 8}
)
app.rule("Send the summary by email", applies_to="send", behaviour="ask_first")


@app.start
async def opening(session: Session) -> None:
    consent = await session.ask(
        ChoiceQuestion("May this interview be recorded, to be read by the team?", ("Yes", "No"))
    )
    session.state["consent"] = consent == "Yes"
    if not session.state["consent"]:
        await session.send("Understood: I ask nothing more. Thank you.")
        return
    session.state["goal"] = await session.ask("What do you want to learn from this interview?")
    session.state["insights"] = []


@app.message
async def reply(session: Session, text: str) -> None:
    if not session.state.get("consent"):
        await session.send("This interview was not consented to; I ask nothing more.")
        return
    async with session.step("Choosing the next question", kind="model", input=text) as step:
        answer = await session.agent.run(
            text,
            goal=session.state["goal"],
            language=session.settings["language"],
            questions=session.settings["length"],
        )
        step.output = answer.text
    await session.send(answer.text)


@app.action("save")
async def save(session: Session, payload: dict) -> None:
    if not session.state.get("consent"):
        return
    insight = {"insight": payload.get("insight", ""), "quote": payload.get("quote", "")}
    session.state.setdefault("insights", []).append(insight)
    await session.record(insight, summary="An insight", kind="feedback")


@app.action("finish")
async def finish(session: Session, payload: dict) -> None:
    async with session.step("Writing the result", kind="model") as step:
        answer = await session.agent.run(
            "The interview is over. List the questions it left open, one per line.",
            goal=session.state.get("goal", ""),
        )
        step.output = answer.text
    result = {
        "goal": session.state.get("goal", ""),
        "insights": session.state.get("insights", []),
        "open_questions": [line for line in answer.text.splitlines() if line.strip()],
    }
    await session.record(result, summary="The interview's result")
    await session.send(answer.text)
