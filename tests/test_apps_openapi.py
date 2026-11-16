# Copyright (c) 2025-2026 Datalayer, Inc.
# Distributed under the terms of the Modified BSD License.

"""An application's `openapi`: the one source of what it answers when called."""

import copy
from pathlib import Path

import pytest
import yaml

import agentspecs.apps
from agentspecs.apps import load_app, parse_app
from agentspecs.openapi import ASK, GALLERY, ask_document, gallery_operation, openapi_operations, openapi_problems

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


# --- the web page's gallery ------------------------------------------------------------

PRODUCTS = {
    "type": "object",
    "properties": {
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "image": {"type": "string"}, "price": {"type": "number"}},
            },
        }
    },
}


def _with_gallery(gallery: object, method: str = "get", inputs: object = None, answer: object = None):  # type: ignore[no-untyped-def]
    document = copy.deepcopy(DOCUMENT)
    operation = {
        "operationId": "listProducts",
        "summary": "The products",
        GALLERY: gallery,
        "responses": {
            "200": {"description": "The products", "content": {"application/json": {"schema": answer or PRODUCTS}}}
        },
    }
    if inputs is not None:
        operation["parameters"] = inputs
    document["paths"]["/products"] = {method: operation}
    return document


def test_one_operation_feeds_the_web_pages_gallery() -> None:
    operations = openapi_operations(with_openapi(_with_gallery({"title": "Our products"})).openapi)
    found = gallery_operation(operations)
    assert found is not None and found.operation_id == "listProducts"
    assert found.gallery == {"title": "Our products"}
    assert openapi_operations(_with_gallery(True))[-1].gallery == {}
    # An optional input is fine: the page calls it with none.
    optional = [{"name": "category", "in": "query", "schema": {"type": "string"}}]
    assert gallery_operation(openapi_operations(_with_gallery(True, inputs=optional))) is not None
    assert gallery_operation(openapi_operations(DOCUMENT)) is None


@pytest.mark.parametrize(
    ("gallery", "method", "inputs", "answer", "says"),
    [
        ("yes", "get", None, None, "is `true` or a mapping"),
        ({"heading": "x"}, "get", None, None, "says only its `title`"),
        (True, "post", None, None, "is on a `get`"),
        (
            True,
            "get",
            [{"name": "category", "in": "query", "required": True, "schema": {"type": "string"}}],
            None,
            "needs no input",
        ),
        (True, "get", None, {"type": "object", "properties": {"items": {"type": "array"}}}, "answers `products`"),
        (
            True,
            "get",
            None,
            {"type": "object", "properties": {"products": {"type": "array", "items": {"properties": {"title": {}}}}}},
            "each with `image`",
        ),
    ],
)
def test_a_gallery_is_checked(gallery, method, inputs, answer, says) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match=says):
        with_openapi(_with_gallery(gallery, method, inputs, answer))


def test_a_page_shows_one_gallery() -> None:
    document = _with_gallery(True)
    document["paths"]["/more"] = {"get": {**copy.deepcopy(document["paths"]["/products"]["get"]), "operationId": "more"}}
    with pytest.raises(ValueError, match="a page shows one gallery"):
        with_openapi(document)


def test_the_demo_shops_page_shows_its_products() -> None:
    shop = load_app(Path(agentspecs.apps.__file__).parent / "demo-shop.yaml")
    found = gallery_operation(openapi_operations(shop.openapi))
    assert found is not None and found.operation_id == "listProducts"
    assert found.gallery == {"title": "The shop's products"}
