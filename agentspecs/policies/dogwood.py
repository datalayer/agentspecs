# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Dogwood policy sets: the parser, AgentCore's quotas and the lowering to Cedar (AC-42).

Dogwood (github.com/dogwood-policy/dogwood, Apache 2.0) is Cedar plus
``when temporal { … }`` / ``unless temporal { … }`` conditions over the
session's earlier events; AgentCore Policy writes its temporal policies in it.
This module reads a policy set: each policy's annotations, effect and scope,
its plain Cedar clauses kept as text, its temporal clauses parsed into a
small syntax tree. The Cedar part is never interpreted here: a set is
**lowered** the way Dogwood lowers it — each temporal clause becomes a
boolean ``context.dogwood.p<i>c<j>`` — and the lowered text is standard
Cedar, which ``cedarpy`` (Cedar 4) parses and decides
(``agent_shield.policy.temporal`` computes the slots from the history).

The temporal grammar read (Dogwood's guide, *Temporal expressions*)::

    cond      := since ('&&' since)*
    since     := unary ['since' 'within' WINDOW unary]
    unary     := '!' unary | 'formerly' 'within' WINDOW unary
               | 'previous' 'within' WINDOW unary
               | 'exists' '(' NAME ':' TYPE ')' '.' cond
               | operand [arith-tail] [CMP arith]
    operand   := '(' cond-or-term ')' | 'tp' '(' NAME ')' | predicate | term | aggregate
    predicate := NS '::' 'Action' '::' STRING '::' KIND ('{' fields '}')*
    aggregate := 'count' 'for' domain '.' 'where' cond
               | 'sum' NAME 'for' domain '.' 'where' cond
    term      := INT | STRING | 'true' | 'false' | 'decimal' '(' STRING ')' | ENTITY
               | 'context' ('.' NAME)+ | ('principal' | 'resource') ('.' NAME)*
               | NAME | '_' | '*' | '[' terms ']'

with ``+ - *`` in comparison operands and windows ``<n>s|m|h|d``. Not read:
macros (``def temporal`` / ``def cedar``), ``?``-parameters, ``||`` (Dogwood
has none). Every variable must be bound by ``exists`` or an aggregation's
``for``, and a ``sum``'s variable must be in its domain.

AgentCore's quotas are held as the set is read: at most **20** temporal
policies in a set, at most **3** temporal operators (``formerly``,
``previous``, ``since``, ``count``, ``sum``) in one policy, no window over
**24 hours**. A set that breaks one is refused in a sentence.

The module uses the standard library alone (``cedarpy`` is optional), so
agentspecs carries it verbatim to validate the policies spec's ``dogwood``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Union

#: AgentCore's quotas on temporal policies.
MAX_TEMPORAL_POLICIES = 20
MAX_TEMPORAL_OPERATORS = 3
MAX_WINDOW_SECONDS = 24 * 3600

#: The units a window is written in, and their seconds.
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

#: The context record the lowered set reads the temporal slots from.
SLOT_RECORD = "dogwood"


class DogwoodRefused(ValueError):
    """A policy set that cannot be read, said in a sentence."""


# -- the syntax tree -------------------------------------------------------------------------


@dataclass(frozen=True)
class Window:
    """A ``within <n><unit>`` window."""

    seconds: int
    text: str


@dataclass(frozen=True)
class Lit:
    """A literal: an integer, a string, a boolean, or a decimal kept as text."""

    value: Any
    decimal: bool = False


@dataclass(frozen=True)
class Var:
    """A bound variable."""

    name: str


@dataclass(frozen=True)
class Wild:
    """``_`` or ``*``: matches anything, binds nothing."""


@dataclass(frozen=True)
class CtxRef:
    """``context.a.b``: a path into the current request's context."""

    path: tuple[str, ...]


@dataclass(frozen=True)
class ScopeRef:
    """``principal`` or ``resource``, with an optional attribute path."""

    name: str
    attrs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Entity:
    """An entity literal, ``Type::"id"``, kept normalised."""

    uid: str


@dataclass(frozen=True)
class Arr:
    """An array of terms."""

    items: tuple[Any, ...]


@dataclass(frozen=True)
class Agg:
    """``count`` or ``sum v`` over a ``for`` domain, where a condition holds."""

    kind: str
    value: str | None
    domain: tuple[tuple[str, str], ...]
    where: Any


@dataclass(frozen=True)
class Arith:
    """``left + right``, ``left - right`` or ``left * right``."""

    op: str
    left: Any
    right: Any


@dataclass(frozen=True)
class Pred:
    """A predicate on one event: its action, its kind and its field patterns."""

    action: str
    kind: str
    fields: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class Tp:
    """``tp(t)``: binds ``t`` to the timepoint evaluated."""

    var: str


@dataclass(frozen=True)
class Formerly:
    """``formerly within W body``."""

    window: Window
    body: Any


@dataclass(frozen=True)
class Previous:
    """``previous within W body``."""

    window: Window
    body: Any


@dataclass(frozen=True)
class Since:
    """``left since within W right``."""

    left: Any
    window: Window
    right: Any


@dataclass(frozen=True)
class Not:
    """``!body``."""

    body: Any


@dataclass(frozen=True)
class And:
    """``left && right``."""

    left: Any
    right: Any


@dataclass(frozen=True)
class Exists:
    """``exists (x: T). body``."""

    var: str
    type: str
    body: Any


@dataclass(frozen=True)
class Compare:
    """``left <op> right``."""

    op: str
    left: Any
    right: Any


Term = Union[Lit, Var, Wild, CtxRef, ScopeRef, Entity, Arr, Agg, Arith]  # noqa: UP007 - an alias evaluated at import, on Python 3.9 too
_TERMS = (Lit, Var, Wild, CtxRef, ScopeRef, Entity, Arr, Agg, Arith)
Cond = Union[Pred, Tp, Formerly, Previous, Since, Not, And, Exists, Compare]  # noqa: UP007 - an alias evaluated at import, on Python 3.9 too


@dataclass(frozen=True)
class Clause:
    """One ``when`` or ``unless`` of a policy: Cedar text, or a temporal condition."""

    keyword: str
    temporal: Cond | None
    text: str
    slot: str | None = None


@dataclass(frozen=True)
class DogwoodPolicy:
    """One policy of a set."""

    index: int
    effect: str
    annotations: dict[str, str]
    head: str
    actions: tuple[str, ...] | None
    clauses: tuple[Clause, ...]

    @property
    def name(self) -> str:
        """The policy's ``@id``, else its position."""
        return self.annotations.get("id") or f"policy {self.index}"

    @property
    def temporal(self) -> bool:
        """Whether a clause is temporal."""
        return any(clause.temporal is not None for clause in self.clauses)

    @property
    def operators(self) -> int:
        """The temporal operators the policy's clauses hold."""
        return sum(count_operators(c.temporal) for c in self.clauses if c.temporal is not None)

    def windows(self) -> list[Window]:
        """Every window the policy's temporal clauses name."""
        found: list[Window] = []
        for clause in self.clauses:
            if clause.temporal is not None:
                found.extend(windows_of(clause.temporal))
        return found


@dataclass(frozen=True)
class DogwoodSet:
    """A parsed policy set and its lowering."""

    text: str
    policies: tuple[DogwoodPolicy, ...]
    lowered: str = field(repr=False, default="")

    @property
    def temporal_policies(self) -> list[DogwoodPolicy]:
        """The policies with a temporal clause."""
        return [policy for policy in self.policies if policy.temporal]

    def slots(self) -> list[tuple[str, Cond]]:
        """Each temporal clause's slot and its condition, in order."""
        return [
            (clause.slot, clause.temporal)
            for policy in self.policies
            for clause in policy.clauses
            if clause.temporal is not None and clause.slot is not None
        ]


def count_operators(cond: Any) -> int:
    """The temporal operators in a condition: formerly, previous, since, count and sum."""
    own = 1 if isinstance(cond, (Formerly, Previous, Since, Agg)) else 0
    return own + sum(count_operators(child) for child in _children(cond))


def windows_of(cond: Any) -> list[Window]:
    """Every window in a condition."""
    own = [cond.window] if isinstance(cond, (Formerly, Previous, Since)) else []
    return own + [w for child in _children(cond) for w in windows_of(child)]


def _children(node: Any) -> list[Any]:
    if isinstance(node, (Formerly, Previous)):
        return [node.body]
    if isinstance(node, Since):
        return [node.left, node.right]
    if isinstance(node, (Not, Exists)):
        return [node.body]
    if isinstance(node, (And, Compare, Arith)):
        return [node.left, node.right]
    if isinstance(node, Agg):
        return [node.where]
    if isinstance(node, Arr):
        return list(node.items)
    if isinstance(node, Pred):
        return [term for _, term in node.fields]
    return []


# -- the lexer -------------------------------------------------------------------------------

_TOKEN = re.compile(
    r"""
    (?P<space>\s+|//[^\n]*)
  | (?P<window>\d+[smhd](?![A-Za-z0-9_]))
  | (?P<int>\d+)
  | (?P<string>"(?:[^"\\]|\\.)*")
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>::|&&|\|\||==|!=|<=|>=|[<>!(){}\[\],:.;@+\-*?$])
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class _Tok:
    kind: str
    value: str
    start: int
    end: int


def _lex(text: str) -> list[_Tok]:
    tokens: list[_Tok] = []
    at = 0
    while at < len(text):
        found = _TOKEN.match(text, at)
        if found is None:
            line = text.count("\n", 0, at) + 1
            raise DogwoodRefused(f"line {line}: {text[at : at + 20]!r} is not Dogwood")
        kind = found.lastgroup or ""
        if kind != "space":
            tokens.append(_Tok(kind, found.group(), found.start(), found.end()))
        at = found.end()
    return tokens


def _uid(path: list[str], ident: str) -> str:
    return "::".join(path) + "::" + json.dumps(ident)


def normalize_uid(text: str) -> str:
    """An entity's uid written ``Type::"id"`` with no spaces, as the evaluator compares them."""
    head, _, rest = text.partition('::"')
    if not rest:
        raise DogwoodRefused(f'{text!r} is not an entity uid (Type::"id")')
    ident = json.loads('"' + rest)
    return _uid([part.strip() for part in head.split("::")], ident)


# -- the temporal parser ---------------------------------------------------------------------

_CMP = ("==", "!=", "<", "<=", ">", ">=")
_UNSUPPORTED = {
    "def": "macros (def temporal / def cedar) are not read by the Shield's evaluator",
    "?": "macro parameters (?w, ?s) are not read outside a macro, and macros are not read",
    "$": "macro binders ($t) are not read: macros are not read",
    "||": "Dogwood has no '||' in a temporal block: write two policies",
}


class _Parser:
    def __init__(self, tokens: list[_Tok], where: str) -> None:
        self.tokens = tokens
        self.at = 0
        self.where = where

    # helpers

    def peek(self, offset: int = 0) -> _Tok | None:
        index = self.at + offset
        return self.tokens[index] if index < len(self.tokens) else None

    def is_(self, value: str, offset: int = 0) -> bool:
        tok = self.peek(offset)
        return tok is not None and tok.value == value and tok.kind in ("op", "name")

    def fail(self, said: str) -> DogwoodRefused:
        tok = self.peek()
        near = f" near {tok.value!r}" if tok else " at its end"
        return DogwoodRefused(f"{self.where}: {said}{near}")

    def take(self, value: str | None = None, kind: str | None = None) -> _Tok:
        tok = self.peek()
        if tok is None:
            raise self.fail(f"expected {value or kind}")
        if tok.value in _UNSUPPORTED and tok.kind == "op":
            raise self.fail(_UNSUPPORTED[tok.value])
        if (value is not None and tok.value != value) or (kind is not None and tok.kind != kind):
            raise self.fail(f"expected {value or kind}")
        self.at += 1
        return tok

    def name(self) -> str:
        return self.take(kind="name").value

    def window(self) -> Window:
        self.take("within")
        tok = self.peek()
        if tok is not None and tok.value == "?":
            raise self.fail(_UNSUPPORTED["?"])
        text = self.take(kind="window").value
        return Window(int(text[:-1]) * UNITS[text[-1]], text)

    # conditions

    def cond(self) -> Any:
        left = self.since()
        while self.is_("&&"):
            self.take("&&")
            left = And(self.as_cond(left), self.as_cond(self.since()))
        if self.is_("||"):
            raise self.fail(_UNSUPPORTED["||"])
        return left

    def since(self) -> Any:
        left = self.unary()
        if self.is_("since"):
            self.take("since")
            window = self.window()
            return Since(left, window, self.unary())
        return left

    def unary(self) -> Any:
        if self.is_("!"):
            self.take("!")
            return Not(self.unary())
        for word, node in (("formerly", Formerly), ("previous", Previous)):
            if self.is_(word) and self.peek(1) is not None and self.is_("within", 1):
                self.take(word)
                window = self.window()
                return node(window, self.unary())
        if self.is_("exists") and self.is_("(", 1):
            self.take("exists")
            self.take("(")
            var = self.name()
            self.take(":")
            kind = self.type_name()
            self.take(")")
            self.take(".")
            return Exists(var, kind, self.cond())
        return self.comparison()

    def type_name(self) -> str:
        parts = [self.name()]
        while self.is_("::"):
            self.take("::")
            parts.append(self.name())
        return "::".join(parts)

    def comparison(self) -> Any:
        left = self.arith(self.operand())
        tok = self.peek()
        if tok is not None and tok.kind == "op" and tok.value in _CMP:
            op = self.take().value
            right = self.arith(self.operand(term_only=True))
            return Compare(op, self.as_term(left), self.as_term(right))
        return left

    def arith(self, left: Any) -> Any:
        while self.peek() is not None and self.peek().kind == "op" and self.peek().value in "+-*":
            op = self.take().value
            right = self.operand(term_only=True)
            left = self._fold(op, self.as_term(left), self.as_term(right))
        return left

    @staticmethod
    def _fold(op: str, left: Any, right: Any) -> Any:
        # '*' binds tighter than '+' and '-': fold into the right edge of a sum.
        if op == "*" and isinstance(left, Arith) and left.op in ("+", "-"):
            return Arith(left.op, left.left, Arith("*", left.right, right))
        return Arith(op, left, right)

    def as_cond(self, node: Any) -> Any:
        if isinstance(node, _TERMS):
            raise self.fail("a term stands where a condition is expected")
        return node

    def as_term(self, node: Any) -> Any:
        if isinstance(node, _TERMS):
            return node
        raise self.fail("a condition stands where a term is compared")

    def operand(self, term_only: bool = False) -> Any:
        tok = self.peek()
        if tok is None:
            raise self.fail("expected a condition or a term")
        if tok.value == "(" and tok.kind == "op":
            self.take("(")
            inner = self.cond()
            self.take(")")
            return inner
        if tok.value == "tp" and self.is_("(", 1) and not term_only:
            self.take("tp")
            self.take("(")
            var = self.name()
            self.take(")")
            return Tp(var)
        if tok.value in ("count", "sum") and tok.kind == "name":
            return self.aggregate()
        return self.term(allow_predicate=not term_only)

    def aggregate(self) -> Agg:
        kind = self.name()
        value = self.name() if kind == "sum" else None
        self.take("for")
        domain = [self.binder()]
        while self.is_(","):
            self.take(",")
            domain.append(self.binder())
        self.take(".")
        self.take("where")
        return Agg(kind, value, tuple(domain), self.cond())

    def binder(self) -> tuple[str, str]:
        self.take("(")
        var = self.name()
        self.take(":")
        kind = self.type_name()
        self.take(")")
        return (var, kind)

    def term(self, allow_predicate: bool = False) -> Any:
        tok = self.take()
        if tok.kind == "int":
            return Lit(int(tok.value))
        if tok.kind == "string":
            return Lit(json.loads(tok.value))
        if tok.value == "-" and self.peek() is not None and self.peek().kind == "int":
            return Lit(-int(self.take().value))
        if tok.value in ("*", "_"):
            return Wild()
        if tok.value == "[":
            return self.array()
        if tok.kind != "name":
            self.at -= 1
            raise self.fail("expected a term")
        return self.named(tok.value, allow_predicate)

    def array(self) -> Arr:
        items: list[Any] = []
        while not self.is_("]"):
            items.append(self.term())
            if not self.is_("]"):
                self.take(",")
        self.take("]")
        return Arr(tuple(items))

    def named(self, word: str, allow_predicate: bool) -> Any:
        if word in ("true", "false"):
            return Lit(word == "true")
        if word == "decimal" and self.is_("("):
            self.take("(")
            text = json.loads(self.take(kind="string").value)
            self.take(")")
            return Lit(text, decimal=True)
        if word == "context":
            return CtxRef(tuple(self.attrs()))
        if word in ("principal", "resource"):
            return ScopeRef(word, tuple(self.attrs()))
        if self.is_("::"):
            return self.path(word, allow_predicate)
        return Var(word)

    def attrs(self) -> list[str]:
        found: list[str] = []
        while self.is_("."):
            self.take(".")
            found.append(self.name())
        return found

    def path(self, first: str, allow_predicate: bool) -> Any:
        parts = [first]
        while self.is_("::"):
            self.take("::")
            tok = self.take()
            if tok.kind == "string":
                return self.after_id(parts, json.loads(tok.value), allow_predicate)
            if tok.kind != "name":
                raise self.fail("expected a name or a quoted id in a path")
            parts.append(tok.value)
        raise self.fail(f'{"::".join(parts)} names no entity (Type::"id")')

    def after_id(self, parts: list[str], ident: str, allow_predicate: bool) -> Any:
        uid = _uid(parts, ident)
        if not self.is_("::"):
            return Entity(uid)
        if not allow_predicate:
            raise self.fail("a predicate stands where a term is expected")
        self.take("::")
        kind = self.name()
        fields: list[tuple[str, Any]] = []
        while self.is_("{"):
            fields.extend(self.fields())
        return Pred(uid, kind, tuple(fields))

    def fields(self) -> list[tuple[str, Any]]:
        self.take("{")
        found: list[tuple[str, Any]] = []
        while not self.is_("}"):
            path = [self.name()]
            while self.is_("."):
                self.take(".")
                path.append(self.name())
            self.take(":")
            found.append((".".join(path), self.term()))
            if not self.is_("}"):
                self.take(",")
        self.take("}")
        return found


def parse_temporal(text: str, where: str = "a temporal block") -> Cond:
    """Parse the body of a ``temporal { … }`` block.

    Parameters
    ----------
    text : str
        The body between the braces.
    where : str
        What the sentences say the block is.

    Returns
    -------
    Cond
        The condition's syntax tree, checked closed.
    """
    parser = _Parser(_lex(text), where)
    cond = parser.as_cond(parser.cond())
    if parser.peek() is not None:
        raise parser.fail("unexpected text after the condition")
    _check_closed(cond, frozenset(), where)
    return cond


def _check_closed(node: Any, bound: frozenset[str], where: str) -> None:
    if isinstance(node, Var) and node.name not in bound:
        raise DogwoodRefused(
            f"{where}: the variable {node.name!r} is bound by no 'exists' or 'for'; write '*' for any value"
        )
    if isinstance(node, Tp) and node.var not in bound:
        raise DogwoodRefused(f"{where}: tp({node.var}) names a variable bound by no 'for'")
    if isinstance(node, Exists):
        _check_closed(node.body, bound | {node.var}, where)
        return
    if isinstance(node, Agg):
        names = {name for name, _ in node.domain}
        if node.value is not None and node.value not in names:
            raise DogwoodRefused(f"{where}: 'sum {node.value}' sums a variable its 'for' domain does not declare")
        _check_closed(node.where, bound | names, where)
        return
    for child in _children(node):
        _check_closed(child, bound, where)


# -- the policy set --------------------------------------------------------------------------


def _matching(tokens: list[_Tok], at: int, opening: str, closing: str) -> int:
    depth = 0
    for index in range(at, len(tokens)):
        if tokens[index].kind != "op":
            continue
        if tokens[index].value == opening:
            depth += 1
        elif tokens[index].value == closing:
            depth -= 1
            if depth == 0:
                return index
    raise DogwoodRefused(f"an unclosed {opening!r}")


def _scope_actions(tokens: list[_Tok]) -> tuple[str, ...] | None:
    """The actions a scope names (``action == A``, ``action in [A, B]``); None for any."""
    for index, tok in enumerate(tokens):
        if tok.value != "action" or tok.kind != "name":
            continue
        rest = tokens[index + 1 :]
        if not rest or rest[0].value not in ("==", "in"):
            return None
        uids = _uids_in(rest[1:])
        return tuple(uids) if uids else None
    return None


def _uids_in(tokens: list[_Tok]) -> list[str]:
    uids: list[str] = []
    path: list[str] = []
    depth = 0
    for tok in tokens:
        if tok.kind == "op" and tok.value == "[":
            depth += 1
        elif tok.kind == "op" and (tok.value == "]" or (tok.value == "," and depth == 0)):
            break
        elif tok.kind == "name":
            path.append(tok.value)
        elif tok.kind == "string" and path:
            uids.append(_uid(path, json.loads(tok.value)))
            path = []
            if depth == 0:
                break
    return uids


def _annotation(tokens: list[_Tok], at: int, where: str) -> tuple[str, str, int]:
    if at + 1 >= len(tokens) or tokens[at + 1].kind != "name":
        raise DogwoodRefused(f"{where}: '@' names no annotation")
    key = tokens[at + 1].value
    if at + 4 < len(tokens) and tokens[at + 2].value == "(" and tokens[at + 3].kind == "string":
        if tokens[at + 4].value != ")":
            raise DogwoodRefused(f"{where}: the annotation @{key} is not closed")
        return key, json.loads(tokens[at + 3].value), at + 5
    return key, "", at + 2


class _SetReader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.tokens = _lex(text)
        self.at = 0

    def tok(self) -> _Tok | None:
        return self.tokens[self.at] if self.at < len(self.tokens) else None

    def policies(self) -> list[DogwoodPolicy]:
        found: list[DogwoodPolicy] = []
        while self.tok() is not None:
            found.append(self.policy(len(found)))
        return found

    def policy(self, index: int) -> DogwoodPolicy:
        where = f"policy {index}"
        annotations: dict[str, str] = {}
        start = self.tokens[self.at].start
        while self.tok() is not None and self.tok().value == "@":
            key, value, self.at = _annotation(self.tokens, self.at, where)
            annotations[key] = value
        if annotations.get("id"):
            where = f"policy {annotations['id']!r}"
        effect = self.tok()
        if effect is not None and effect.value == "def":
            raise DogwoodRefused(f"{where}: {_UNSUPPORTED['def']}")
        if effect is None or effect.value not in ("permit", "forbid"):
            raise DogwoodRefused(f"{where}: a policy starts with permit or forbid")
        self.at += 1
        if self.tok() is None or self.tok().value != "(":
            raise DogwoodRefused(f"{where}: {effect.value} names its scope in parentheses")
        close = _matching(self.tokens, self.at, "(", ")")
        actions = _scope_actions(self.tokens[self.at + 1 : close])
        head = self.text[start : self.tokens[close].end]
        self.at = close + 1
        clauses: list[Clause] = []
        while self.tok() is not None and self.tok().value in ("when", "unless"):
            clauses.append(self.clause(index, len(clauses), where))
        if self.tok() is None or self.tok().value != ";":
            raise DogwoodRefused(f"{where}: a policy ends with ';'")
        self.at += 1
        return DogwoodPolicy(index, effect.value, annotations, head, actions, tuple(clauses))

    def clause(self, policy: int, index: int, where: str) -> Clause:
        keyword = self.tokens[self.at].value
        self.at += 1
        tag = None
        if self.tok() is not None and self.tok().kind == "name":
            tag = self.tok().value
            if tag not in ("temporal", "guardrails"):
                raise DogwoodRefused(f"{where}: '{keyword} {tag}' is not a clause Dogwood knows")
            self.at += 1
        if self.tok() is None or self.tok().value != "{":
            raise DogwoodRefused(f"{where}: '{keyword}' opens a block with '{{'")
        close = _matching(self.tokens, self.at, "{", "}")
        body = self.text[self.tokens[self.at].end : self.tokens[close].start]
        self.at = close + 1
        if tag != "temporal":
            return Clause(keyword, None, f"{keyword} {{{body}}}")
        slot = f"p{policy}c{index}"
        cond = parse_temporal(body, f"{where}, {keyword} temporal")
        return Clause(keyword, cond, f"{keyword} {{ context.{SLOT_RECORD}.{slot} }}", slot)


def lower(policies: list[DogwoodPolicy]) -> str:
    """The set as standard Cedar: each temporal clause a boolean ``context.dogwood`` slot.

    Parameters
    ----------
    policies : list of DogwoodPolicy
        The parsed policies.

    Returns
    -------
    str
        The lowered Cedar policy set, one policy per paragraph, in order.
    """
    return "\n\n".join(
        " ".join([policy.head, *(clause.text for clause in policy.clauses)]) + ";" for policy in policies
    )


def quota_problems(policies: list[DogwoodPolicy]) -> list[str]:
    """Why AgentCore would refuse the set, in sentences; empty when it would take it."""
    problems: list[str] = []
    temporal = [policy for policy in policies if policy.temporal]
    if len(temporal) > MAX_TEMPORAL_POLICIES:
        problems.append(
            f"the set holds {len(temporal)} temporal policies, over AgentCore's quota of "
            f"{MAX_TEMPORAL_POLICIES} per policy engine"
        )
    for policy in temporal:
        if policy.operators > MAX_TEMPORAL_OPERATORS:
            problems.append(
                f"{policy.name} holds {policy.operators} temporal operators, over AgentCore's "
                f"quota of {MAX_TEMPORAL_OPERATORS} per policy"
            )
        for window in policy.windows():
            if window.seconds > MAX_WINDOW_SECONDS:
                problems.append(f"{policy.name} looks back {window.text}, over the 24-hour window AgentCore allows")
    return problems


def parse_set(text: str) -> DogwoodSet:
    """Parse a Dogwood policy set and hold AgentCore's quotas.

    Parameters
    ----------
    text : str
        The policy set, Cedar and Dogwood.

    Returns
    -------
    DogwoodSet
        The policies and their lowering to Cedar.

    Raises
    ------
    DogwoodRefused
        When the set does not parse, a variable is unbound, or a quota is broken.
    """
    if not text.strip():
        raise DogwoodRefused("the policy set is empty: deny by default would refuse everything")
    policies = _SetReader(text).policies()
    problems = quota_problems(policies)
    if problems:
        raise DogwoodRefused("; ".join(problems))
    return DogwoodSet(text=text, policies=tuple(policies), lowered=lower(policies))


def cedar_problem(lowered: str) -> str | None:
    """Why ``cedarpy`` refuses the lowered set; ``None`` when it parses, or ``"unavailable"``.

    Parameters
    ----------
    lowered : str
        The lowered Cedar text.

    Returns
    -------
    str or None
        ``None`` when Cedar parses it; ``"unavailable"`` when cedarpy is not installed;
        else Cedar's own message.
    """
    try:
        import cedarpy  # optional: the [cedar] extra
    except ImportError:
        return "unavailable"
    try:
        cedarpy.policies_to_json_str(lowered)
    except Exception as error:  # cedarpy raises its own error types
        return str(error).strip() or type(error).__name__
    return None


def validate(text: str) -> tuple[list[str], list[str]]:
    """Validate a policy set as the policies spec reads it: problems, and what was not checked.

    Parameters
    ----------
    text : str
        The policy set.

    Returns
    -------
    tuple of (list of str, list of str)
        The problems (empty when the set holds) and notes on what could not be checked.
    """
    try:
        parsed = parse_set(text)
    except DogwoodRefused as refused:
        return [str(refused)], []
    said = cedar_problem(parsed.lowered)
    if said == "unavailable":
        return [], ["cedarpy is not installed: the temporal clauses and the quotas were checked, the Cedar was not"]
    if said is not None:
        return [f"Cedar refuses the set: {said}"], []
    return [], []


__all__ = [
    "MAX_TEMPORAL_OPERATORS",
    "MAX_TEMPORAL_POLICIES",
    "MAX_WINDOW_SECONDS",
    "SLOT_RECORD",
    "UNITS",
    "Agg",
    "And",
    "Arith",
    "Arr",
    "Clause",
    "Compare",
    "Cond",
    "CtxRef",
    "DogwoodPolicy",
    "DogwoodRefused",
    "DogwoodSet",
    "Entity",
    "Exists",
    "Formerly",
    "Lit",
    "Not",
    "Pred",
    "Previous",
    "ScopeRef",
    "Since",
    "Term",
    "Tp",
    "Var",
    "Wild",
    "Window",
    "cedar_problem",
    "count_operators",
    "lower",
    "normalize_uid",
    "parse_set",
    "parse_temporal",
    "quota_problems",
    "validate",
    "windows_of",
]
