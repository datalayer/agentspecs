# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""UI plugins: every spec is well formed, and every agent names one that exists."""

from __future__ import annotations

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"


def _plugins() -> dict[str, dict]:
    return {path.stem: yaml.safe_load(path.read_text()) for path in sorted((ROOT / "ui-plugins").glob("*.yaml"))}


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
        if spec.get("ui_plugin"):
            named += 1
            assert spec["ui_plugin"] in plugins, f"{path.name}: no spec under ui-plugins for {spec['ui_plugin']!r}"
    assert named > 0
