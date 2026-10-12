# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""UI specs: every spec is well formed, and every agent names one that exists."""

from __future__ import annotations

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"


def _plugins() -> dict[str, dict]:
    return {path.stem: yaml.safe_load(path.read_text()) for path in sorted((ROOT / "ui").glob("*.yaml"))}


def test_a_plugin_file_is_named_for_its_id_and_says_what_it_is():
    plugins = _plugins()
    assert {"a2ui", "mcp-apps", "mcp-ui"} <= set(plugins)
    for stem, spec in plugins.items():
        assert spec["id"] == stem
        assert spec["name"] and spec["description"].strip()
        assert spec["docs_url"].startswith("https://")
        assert isinstance(spec["enabled"], bool)


def test_an_agent_names_a_plugin_that_exists():
    plugins = _plugins()
    named = 0
    for path in sorted((ROOT / "agents").rglob("*.yaml")):
        spec = yaml.safe_load(path.read_text()) or {}
        if spec.get("ui"):
            named += 1
            assert spec["ui"] in plugins, f"{path.name}: no spec under ui for {spec['ui']!r}"
    assert named > 0


def test_the_old_names_are_gone():
    """`ui-plugins` is `ui` (AGENT_PROTOCOLS PS-03): no spec says the old field, no folder keeps the old name."""
    assert not (ROOT / "ui-plugins").exists()
    for path in sorted([*(ROOT / "agents").rglob("*.yaml"), *(ROOT / "cogs").rglob("*.yaml")]):
        spec = yaml.safe_load(path.read_text()) or {}
        assert "ui_plugin" not in spec, f"{path.name}: `ui_plugin` is now `ui`"
