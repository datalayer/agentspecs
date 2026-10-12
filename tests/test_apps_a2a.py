# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The Appspec's `a2a` block: the extensions an application's Agent Card advertises (AGENT_PROTOCOLS PR-02)."""

import pytest
from pydantic import ValidationError

from agentspecs.apps import AppSpec

BASE = {"id": "shop", "name": "Shop", "kind": "chat", "agent": "a"}
GIFT = {
    "uri": "https://shop.example/extensions/gift-wrap/v1",
    "description": "Wraps an order as a gift.",
    "params": {"papers": ["red", "gold"], "max_message": 140},
}


def test_an_extension_is_its_uri_and_public_params():
    spec = AppSpec.model_validate({**BASE, "a2a": {"extensions": [GIFT, {"uri": "urn:example:loyalty"}]}})
    gift, loyalty = spec.a2a.extensions
    assert (gift.uri, gift.required, gift.params["max_message"]) == (GIFT["uri"], False, 140)
    assert (loyalty.uri, loyalty.description, loyalty.params) == ("urn:example:loyalty", "", {})
    assert AppSpec.model_validate(BASE).a2a.extensions == []
    # What the runtime's card reads: the declared extensions as A2A writes them.
    assert spec.model_dump(by_alias=True)["a2a"]["extensions"][0] == {**GIFT, "required": False}


@pytest.mark.parametrize(
    "change,why",
    [
        ({"uri": "shop.example/gift"}, "not an extension URI"),
        ({"uri": "http://shop.example/gift"}, "not an extension URI"),
        ({"uri": "https://user@shop.example/gift"}, "not an extension URI"),
        ({"uri": "https://datalayer.ai/extensions/face/v1"}, "Datalayer's own"),
        ({"params": {"api_key": "x"}}, "credential"),
        ({"params": {"nested": [{"accessToken": "x"}]}}, "credential"),
        ({"params": {"when": object()}}, "JSON values"),
        ({"secret": "x"}, "Extra inputs"),
    ],
)
def test_what_an_extension_refuses(change, why):
    with pytest.raises(ValidationError, match=why):
        AppSpec.model_validate({**BASE, "a2a": {"extensions": [{**GIFT, **change}]}})


def test_an_extension_is_declared_once():
    with pytest.raises(ValidationError, match="declared twice"):
        AppSpec.model_validate({**BASE, "a2a": {"extensions": [GIFT, {**GIFT, "required": True}]}})
