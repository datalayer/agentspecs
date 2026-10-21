# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The session file, `datalayer-session/1` (MH-12)."""

from __future__ import annotations

import pytest

from agentspecs import sessions

SESSION = {
    "record_type": "session",
    "format": "datalayer-session/1",
    "uid": "e67a52b2-0001",
    "app": {"id": "shield-mvp-claude-code", "version": 3},
    "agent": "shield-mvp-claude-code",
    "harness": "claude-code",
    "owner": {"uid": "01jq"},
    "state": "paused",
    "turns": 4,
    "title": "The refactor",
    "archived": False,
    "lineage": {"forked_from": None, "imported_from": None},
    "kinds": ["session", "turn", "tool_call"],
    "entries": 9,
    "exported_at": "2026-10-21T10:12:00Z",
    "exported_by": {"uid": "01jq"},
    "redactions": 2,
}
ENTRY = {"record_type": "entry", "kind": "turn", "at": "2026-10-21T10:00:00Z", "payload": {"asked": "Hi", "answered": "Hello"}}
TEAM = {
    "record_type": "team_session",
    "format": "datalayer-session/1",
    "execution_id": "exec-1",
    "team": {"id": "coding-agents", "version": "0.0.1"},
    "owner": {"uid": "01jq"},
    "state": "ended",
    "seats": [{"id": "coder", "session_uid": "e67a52b2-0001", "agent": "shield-mvp-codex", "harness": "codex"}],
    "lineage": {"forked_from": None, "imported_from": None},
    "exported_at": "2026-10-21T10:12:00Z",
    "exported_by": {"uid": "01jq"},
    "redactions": 0,
}


def test_the_format_is_what_the_spec_says():
    assert sessions.FORMAT == "datalayer-session/1"
    assert sessions.STATES == ("open", "paused", "ended")
    assert (sessions.MAX_BYTES, sessions.MAX_ENTRIES) == (64 * 1024 * 1024, 20_000)
    assert {"session", "turn", "tool_call", "paused", "ended", "swapped", "cloned", "imported", "exported", "titled"} <= set(sessions.ENTRY_KINDS)
    assert set(sessions.REDACTION_RULES) == {
        "authorization_header", "bearer_token", "declared_secret", "url_userinfo", "signed_user", "runtime_address",
    }


def test_the_three_lines_parse():
    session = sessions.parse_line(SESSION)
    assert isinstance(session, sessions.SessionLine) and session.state is sessions.SessionState.PAUSED
    entry = sessions.parse_line(ENTRY, line=2)
    assert isinstance(entry, sessions.EntryLine) and entry.kind == "turn"
    team = sessions.parse_line(TEAM)
    assert isinstance(team, sessions.TeamLine) and team.seats[0].session_uid == "e67a52b2-0001"


def test_an_unversioned_first_line_is_refused():
    with pytest.raises(sessions.SessionFileError, match="first line is a session line that says its format"):
        sessions.parse_line({k: v for k, v in SESSION.items() if k != "format"})
    with pytest.raises(sessions.SessionFileError, match="first line is a session line that says its format"):
        sessions.parse_line({"uid": "x"})


def test_another_version_is_refused_naming_both():
    with pytest.raises(sessions.SessionFileError, match="The file is datalayer-session/2; this runtime reads datalayer-session/1."):
        sessions.parse_line({**SESSION, "format": "datalayer-session/2"})


def test_an_unknown_kind_is_refused():
    with pytest.raises(sessions.SessionFileError, match="kind 'shell', which the record does not have"):
        sessions.parse_line({**ENTRY, "kind": "shell"}, line=7)
    with pytest.raises(sessions.SessionFileError, match="kinds the record does not have: shell"):
        sessions.parse_line({**SESSION, "kinds": ["turn", "shell"]})


def test_an_entry_without_at_is_refused():
    with pytest.raises(sessions.SessionFileError, match="Line 3 is an entry that does not say when it was recorded"):
        sessions.parse_line({k: v for k, v in ENTRY.items() if k != "at"}, line=3)


def test_a_team_line_without_its_seats_is_refused():
    with pytest.raises(sessions.SessionFileError, match="names its seats, in order, each with its session uid; this one names none"):
        sessions.parse_line({**TEAM, "seats": []})
    with pytest.raises(sessions.SessionFileError, match="named twice"):
        sessions.parse_line({**TEAM, "seats": [TEAM["seats"][0], TEAM["seats"][0]]})


def test_a_line_that_is_none_of_the_three_is_refused():
    with pytest.raises(sessions.SessionFileError, match="Line 4 of the file is not a session, team_session or entry line"):
        sessions.parse_line({"record_type": "item"}, line=4)
    with pytest.raises(sessions.SessionFileError, match="Line 2 is refused: uid"):
        sessions.parse_line({**SESSION, "uid": "x"}, line=2)
    with pytest.raises(sessions.SessionFileError, match="Line 1 is refused: lineage.imported_from.digest"):
        sessions.parse_line({**SESSION, "lineage": {"forked_from": None, "imported_from": {"digest": "md5:1", "exported_at": "x", "exported_by": {"uid": "a"}}}})


def test_the_caps():
    assert sessions.within_caps(10, 10) is None
    assert sessions.within_caps(70 * 1024 * 1024, 31_204) == (
        "The file has 31 204 entries over 70 MB; a session file holds at most 20 000 entries in 64 MB."
    )


def test_the_schema_and_the_reference_are_the_spec():
    assert sessions.SCHEMA_PATH.read_text() == sessions.schema_text()
    schema = sessions.json_schema()
    assert {ref["$ref"].rsplit("/", 1)[1] for ref in schema["oneOf"]} == {"SessionLine", "EntryLine", "TeamLine"}
    if sessions.REFERENCE_PATH.is_file():
        assert sessions.REFERENCE_PATH.read_text() == sessions.reference_text()
