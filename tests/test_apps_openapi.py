# Copyright (c) 2025-2026 Datalayer, Inc.
# Distributed under the terms of the Modified BSD License.

"""An application's `openapi`: the one source of what it answers when called."""

import copy
from pathlib import Path

import pytest
import yaml

import agentspecs.apps
from agentspecs.apps import load_app, parse_app
from agentspecs.openapi import ASK, ask_document, openapi_operations, openapi_problems

BASE = yaml.safe_load((Path(agentspecs.apps.__file__).parent / "web-research.yaml").read_text())

DOCUMENT = {
    "openapi": "3.1.0",
    "info": {"title": "Shop", "version": "1"},
    "paths": {
        "/products/{product_id}": {
            "get": {
                "operationId": "getProduct",
                "summary": "One product",
                "description": "Answer the product with its price and stock.",
                "parameters": [
                    {"name": "product_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                    {"name": "currency", "in": "query", "schema": {"type": "string"}, "description": "ISO code"},
                ],
                "responses": {
                    "200": {
                        "description": "The product",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Product"}}},
                    }
                },
            }
        },
        "/quote": {
            "post": {
                "operationId": "quote",
                "summary": "The total of a basket",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"items": {"type": "array", "items": {"type": "integer"}}},
                                "required": ["items"],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "The total",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object", "properties": {"total": {"type": "number"}}}
                            }
                        },
                    }
                },
            }
        },
    },
    "components": {
        "schemas": {
            "Product": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "price": {"type": "number"}},
                "required": ["title", "price"],
            }
        }
    },
}


def with_openapi(document: object):  # type: ignore[no-untyped-def]
    return parse_app({**BASE, "openapi": document})


def test_an_application_says_what_it_answers_in_openapi() -> None:
    spec = with_openapi(DOCUMENT)
    assert spec.openapi == DOCUMENT
    product, quote = openapi_operations(spec.openapi)
    assert (product.operation_id, product.method, product.path) == ("getProduct", "get", "/products/{product_id}")
    assert product.instruction == "One product\n\nAnswer the product with its price and stock."
    # Its inputs: path and query parameters, one JSON object.
    assert product.input_schema["properties"]["product_id"] == {"type": "integer"}
    assert product.input_schema["properties"]["currency"] == {"type": "string", "description": "ISO code"}
    assert product.input_schema["required"] == ["product_id"]
    assert product.parameters == (("product_id", "path"), ("currency", "query"))
    # Its answer: the 200's JSON schema, its references written in place.
    assert product.output_schema["required"] == ["title", "price"]
    assert quote.body and quote.input_schema["required"] == ["items"]
    assert quote.input_schema["additionalProperties"] is False


def test_without_openapi_an_application_answers_ask() -> None:
    assert parse_app(BASE).openapi is None
    document = ask_document("Web Research", "Researches the web")
    assert openapi_problems(document) == []
    [ask] = openapi_operations(document)
    assert ask.operation_id == ASK
    assert ask.input_schema["required"] == ["question"]
    assert ask.output_schema["required"] == ["answer"]


def _changed(change):  # type: ignore[no-untyped-def]
    document = copy.deepcopy(DOCUMENT)
    change(document)
    return document


@pytest.mark.parametrize(
    ("change", "says"),
    [
        (lambda d: d.update(openapi="3.0.3"), "OpenAPI 3.1 document"),
        (lambda d: d["info"].pop("version"), "not valid OpenAPI 3.1: 'version' is a required property"),
        (lambda d: d["paths"]["/quote"]["post"].pop("operationId"), "names no `operationId`"),
        (lambda d: d["paths"]["/quote"]["post"].update(operationId="a quote"), "not an operation id"),
        (lambda d: d["paths"]["/quote"]["post"].pop("summary"), "says what it does"),
        (
            lambda d: d["paths"]["/quote"]["post"]["requestBody"].update(
                content={"text/plain": {"schema": {"type": "string"}}}
            ),
            "is JSON alone",
        ),
        (
            lambda d: d["paths"]["/quote"]["post"]["requestBody"]["content"]["application/json"].update(
                schema={"type": "array"}
            ),
            "is a JSON object",
        ),
        (
            lambda d: d["paths"]["/quote"]["post"].update(
                responses={"201": {"description": "Made", "content": {"application/json": {"schema": {}}}}}
            ),
            "answers `200`",
        ),
        (
            lambda d: d["paths"]["/products/{product_id}"]["get"]["parameters"].append(
                {"name": "X-Key", "in": "header", "schema": {"type": "string"}}
            ),
            "inputs are JSON, path or query",
        ),
        (lambda d: d["paths"]["/quote"]["post"].update(operationId="getProduct"), "is not unique"),
        (lambda d: d.update(paths={}), "at least one operation"),
    ],
)
def test_an_openapi_is_checked(change, says: str) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match=says):
        with_openapi(_changed(change))


def test_an_openapi_is_a_document_not_a_word() -> None:
    with pytest.raises(ValueError, match="valid dictionary"):
        with_openapi("shop.yaml")


def test_in_a_file_openapi_is_a_path_beside_the_spec(tmp_path: Path) -> None:
    (tmp_path / "shop.openapi.yaml").write_text(yaml.safe_dump(DOCUMENT))
    (tmp_path / "shop.yaml").write_text(yaml.safe_dump({**BASE, "openapi": "shop.openapi.yaml"}))
    assert load_app(tmp_path / "shop.yaml").openapi == DOCUMENT
    (tmp_path / "gone.yaml").write_text(yaml.safe_dump({**BASE, "openapi": "missing.yaml"}))
    with pytest.raises(ValueError, match="not a file beside it"):
        load_app(tmp_path / "gone.yaml")
