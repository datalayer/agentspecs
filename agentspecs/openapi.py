# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""An application's ``openapi``: the one source of what it does when called.

An Appspec's top-level ``openapi`` is an OpenAPI 3.1 document. Each of its
operations is something the application answers when called — as an MCP tool,
as a REST endpoint, and, when it carries ``x-pap``, as a Personal Agent
Protocol operation — and nothing else lists them:

- its ``summary`` and ``description`` are its instruction to the agent;
- its inputs are its JSON request body and its path and query parameters, one
  JSON object;
- its ``200`` response's JSON schema is the JSON the agent must answer.

One operation may carry ``x-datalayer-gallery``: the one whose answer the
application's web page shows as a gallery of product cards (photo, title,
price, rating), read by calling it (:func:`gallery_operation`).

An application without ``openapi`` answers one operation, ``ask``: a question
in, the agent's answer out (:func:`ask_document`).
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

#: The HTTP methods an operation is written under.
METHODS: Tuple[str, ...] = ("get", "post", "put", "patch", "delete")

#: An operation's id, which is also its MCP tool's name.
OPERATION_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")

#: The one media type an operation takes and answers.
JSON = "application/json"

#: The operation an application without ``openapi`` answers.
ASK = "ask"

#: The extension that names the operation whose answer the web page shows as a gallery.
GALLERY = "x-datalayer-gallery"

#: What a gallery's answer holds: a list of items under ``products``, each with these.
GALLERY_ITEMS = "products"
GALLERY_FIELDS: Tuple[str, ...] = ("title", "image")


@dataclass(frozen=True)
class OpenApiOperation:
    """One operation of an application's ``openapi``."""

    operation_id: str
    method: str
    path: str
    summary: str
    description: str
    #: Its inputs as one JSON object: the request body's properties, then the
    #: path and query parameters.
    input_schema: Dict[str, Any]
    #: The JSON its ``200`` response carries.
    output_schema: Dict[str, Any]
    #: Its path and query parameters, ``(name, "path" | "query")``.
    parameters: Tuple[Tuple[str, str], ...] = ()
    #: Whether it takes a JSON request body.
    body: bool = False
    #: Its ``x-pap`` extension, as written.
    pap: Optional[Dict[str, Any]] = None
    tags: Tuple[str, ...] = field(default=())
    #: Its ``x-datalayer-gallery`` extension (``{}`` for ``true``, else its ``title``):
    #: the web page shows its answer as a gallery.
    gallery: Optional[Dict[str, Any]] = None

    @property
    def instruction(self) -> str:
        """What the agent is told to do: the summary, then the description."""
        return "\n\n".join(part for part in (self.summary.strip(), self.description.strip()) if part)


def ask_document(name: str, description: str = "") -> Dict[str, Any]:
    """The ``openapi`` of an application that declares none: one ``ask`` operation."""
    return {
        "openapi": "3.1.0",
        "info": {"title": name, "version": "1", **({"description": description} if description else {})},
        "paths": {
            "/ask": {
                "post": {
                    "operationId": ASK,
                    "summary": f"Ask {name}",
                    "description": "Answer the question, as yourself, in the `answer`.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            JSON: {
                                "schema": {
                                    "type": "object",
                                    "properties": {"question": {"type": "string", "description": "The question"}},
                                    "required": ["question"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "The answer",
                            "content": {
                                JSON: {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"answer": {"type": "string"}},
                                        "required": ["answer"],
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }


def _resolved(document: Mapping[str, Any], value: Any, depth: int = 0) -> Any:
    """``value`` with every local ``$ref`` (``#/components/...``) written in place."""
    if depth > 32:
        raise ValueError("a `$ref` refers to itself: an operation's schemas are finite")
    if isinstance(value, Mapping):
        ref = value.get("$ref")
        if isinstance(ref, str):
            if not ref.startswith("#/"):
                raise ValueError(f"`{ref}` is not in the document: only `#/components/...` references are read")
            target: Any = document
            for part in ref[2:].split("/"):
                part = part.replace("~1", "/").replace("~0", "~")
                if not isinstance(target, Mapping) or part not in target:
                    raise ValueError(f"`{ref}` refers to nothing in the document")
                target = target[part]
            return _resolved(document, target, depth + 1)
        return {key: _resolved(document, item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolved(document, item, depth + 1) for item in value]
    return value


def _json_schema(document: Mapping[str, Any], content: Any, where: str) -> Dict[str, Any]:
    if not isinstance(content, Mapping) or set(content) != {JSON}:
        raise ValueError(f"{where} is JSON alone (`{JSON}`)")
    schema = (content[JSON] or {}).get("schema")
    if not isinstance(schema, Mapping):
        raise ValueError(f"{where} gives its JSON schema")
    return dict(_resolved(document, schema))


def _operation(
    document: Mapping[str, Any], path: str, method: str, item: Mapping[str, Any], operation: Mapping[str, Any]
) -> OpenApiOperation:
    where = f"{method.upper()} {path}"
    operation_id = operation.get("operationId")
    if not isinstance(operation_id, str) or not operation_id:
        raise ValueError(f"{where} names no `operationId`: each operation is called by it")
    if not OPERATION_ID.fullmatch(operation_id):
        raise ValueError(
            f"`{operation_id}` ({where}) is not an operation id an MCP tool takes: "
            "a letter, then letters, digits or `_`, 64 at most"
        )
    summary = str(operation.get("summary") or "")
    description = str(operation.get("description") or "")
    if not (summary.strip() or description.strip()):
        raise ValueError(f"`{operation_id}` says what it does in its `summary` or `description`: the agent is told it")
    properties: Dict[str, Any] = {}
    required: List[str] = []
    body = False
    request = operation.get("requestBody")
    if request is not None:
        request = _resolved(document, request)
        schema = _json_schema(document, request.get("content"), f"The request body of `{operation_id}`")
        if schema.get("type") != "object":
            raise ValueError(f"The request body of `{operation_id}` is a JSON object (`type: object`)")
        properties.update(schema.get("properties") or {})
        required.extend(schema.get("required") or [])
        body = True
    parameters: List[Tuple[str, str]] = []
    for parameter in [*(item.get("parameters") or []), *(operation.get("parameters") or [])]:
        parameter = _resolved(document, parameter)
        location = parameter.get("in")
        name = str(parameter.get("name") or "")
        if location not in ("path", "query"):
            raise ValueError(f"`{name}` of `{operation_id}` is in its {location}: inputs are JSON, path or query")
        if name in properties:
            raise ValueError(f"`{name}` is an input of `{operation_id}` twice")
        properties[name] = dict(parameter.get("schema") or {"type": "string"})
        if parameter.get("description") and "description" not in properties[name]:
            properties[name]["description"] = parameter["description"]
        if parameter.get("required") or location == "path":
            required.append(name)
        parameters.append((name, location))
    responses = operation.get("responses") or {}
    answer = responses.get("200")
    if answer is None:
        raise ValueError(f"`{operation_id}` answers `200` with the JSON the agent returns")
    output = _json_schema(document, _resolved(document, answer).get("content"), f"The `200` answer of `{operation_id}`")
    input_schema: Dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        input_schema["required"] = sorted(set(required), key=required.index)
    pap = operation.get("x-pap")
    if pap is not None and not isinstance(pap, Mapping):
        raise ValueError(f"The `x-pap` of `{operation_id}` is a mapping")
    gallery = _gallery(operation_id, method, input_schema, output, operation.get(GALLERY))
    return OpenApiOperation(
        operation_id=operation_id,
        method=method,
        path=path,
        summary=summary,
        description=description,
        input_schema=input_schema,
        output_schema=output,
        parameters=tuple(parameters),
        body=body,
        pap=copy.deepcopy(dict(pap)) if pap is not None else None,
        tags=tuple(str(tag) for tag in operation.get("tags") or ()),
        gallery=gallery,
    )


def _gallery(
    operation_id: str, method: str, inputs: Mapping[str, Any], output: Mapping[str, Any], written: Any
) -> Optional[Dict[str, Any]]:
    """An operation's ``x-datalayer-gallery``, checked: a ``get`` that needs no input and
    answers ``products``, a list of items each with a ``title`` and an ``image``."""
    if written is None or written is False:
        return None
    where = f"The `{GALLERY}` of `{operation_id}`"
    if written is True:
        gallery: Dict[str, Any] = {}
    elif isinstance(written, Mapping):
        unknown = sorted(set(written) - {"title"})
        if unknown:
            raise ValueError(f"{where} says only its `title`, not {', '.join(f'`{key}`' for key in unknown)}")
        title = written.get("title")
        if title is not None and (not isinstance(title, str) or not title.strip()):
            raise ValueError(f"{where} has a `title` in words")
        gallery = {"title": title.strip()} if title else {}
    else:
        raise ValueError(f"{where} is `true` or a mapping with its `title`")
    if method != "get":
        raise ValueError(f"{where} is on a `get`: the page reads it, it changes nothing")
    if inputs.get("required"):
        raise ValueError(f"{where} needs no input: the page calls it with none")
    items = (output.get("properties") or {}).get(GALLERY_ITEMS) or {}
    fields = ((items.get("items") or {}).get("properties") or {}) if items.get("type") == "array" else None
    if fields is None:
        raise ValueError(f"{where} answers `{GALLERY_ITEMS}`, a list: the items the gallery shows")
    missing = [name for name in GALLERY_FIELDS if name not in fields]
    if missing:
        raise ValueError(
            f"{where} answers items each with {', '.join(f'`{name}`' for name in missing)}: what a card shows"
        )
    return gallery


def openapi_operations(document: Mapping[str, Any]) -> List[OpenApiOperation]:
    """The operations of a valid document, in the order it writes them.

    Raises
    ------
    ValueError
        When an operation is not one an application answers (see
        :func:`openapi_problems`).
    """
    found: List[OpenApiOperation] = []
    for path, item in (document.get("paths") or {}).items():
        item = _resolved(document, item)
        for method in METHODS:
            operation = item.get(method)
            if isinstance(operation, Mapping):
                found.append(_operation(document, str(path), method, item, operation))
    ids = [operation.operation_id for operation in found]
    twice = sorted({identity for identity in ids if ids.count(identity) > 1})
    if twice:
        raise ValueError(f"{', '.join(f'`{identity}`' for identity in twice)} names two operations")
    galleries = [operation.operation_id for operation in found if operation.gallery is not None]
    if len(galleries) > 1:
        raise ValueError(
            f"{', '.join(f'`{identity}`' for identity in galleries)} each carry `{GALLERY}`: a page shows one gallery"
        )
    return found


def gallery_operation(operations: Sequence[OpenApiOperation]) -> Optional[OpenApiOperation]:
    """The operation whose answer the web page shows as a gallery, or none."""
    for operation in operations:
        if operation.gallery is not None:
            return operation
    return None


def openapi_problems(document: Any) -> List[str]:
    """Why ``document`` is not an application's ``openapi``, or nothing.

    It is an OpenAPI 3.1 document (checked by ``openapi-spec-validator``),
    with at least one operation, each named by its ``operationId``, said in its
    ``summary`` or ``description``, taking JSON (a JSON object body, path and
    query parameters) and answering ``200`` with JSON.
    """
    if not isinstance(document, Mapping):
        return ["`openapi` is an OpenAPI document: a mapping, written in the spec"]
    version = str(document.get("openapi") or "")
    if not version.startswith("3.1."):
        return [f"`openapi` is an OpenAPI 3.1 document (`openapi: 3.1.0`), not {version or 'unversioned'}"]
    from openapi_spec_validator import OpenAPIV31SpecValidator  # noqa: PLC0415

    problems = [
        f"`openapi` is not valid OpenAPI 3.1: {error.message}"
        f"{' (at ' + '.'.join(str(part) for part in error.absolute_path) + ')' if error.absolute_path else ''}"
        for error in OpenAPIV31SpecValidator(dict(document)).iter_errors()
    ]
    if problems:
        return problems
    try:
        operations = openapi_operations(document)
    except ValueError as error:
        return [str(error)]
    if not operations:
        return ["`openapi` describes at least one operation"]
    return []


__all__ = [
    "ASK",
    "GALLERY",
    "GALLERY_FIELDS",
    "GALLERY_ITEMS",
    "JSON",
    "METHODS",
    "OpenApiOperation",
    "ask_document",
    "gallery_operation",
    "openapi_operations",
    "openapi_problems",
]
