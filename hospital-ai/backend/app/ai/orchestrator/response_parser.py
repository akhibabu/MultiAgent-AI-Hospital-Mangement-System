"""
ResponseParser — converts raw LLM text into validated, structured JSON.

Every AI response is validated against the caller-specified Pydantic
model before it is returned by the orchestrator — raw LLM output never
reaches a pipeline or the frontend directly.

LLMs (Groq, Ollama, OpenAI, …) routinely emit JSON `null` for fields
they don't know (e.g. `url: null`). Pydantic's `str = ""` defaults only
apply when the key is *missing*, not when it is explicitly null — so
this parser coerces nulls to the field's declared default (or `""` /
`[]`) before validation, while leaving genuine `Optional[...]` nulls
alone.

Truncation is the other common failure mode: `max_tokens` cuts the
model off mid-string (`"url": "http`). When that happens we salvage every
*complete* object that was already emitted rather than failing the whole
pipeline — a partial evidence list is far more useful than an empty one.
"""
from __future__ import annotations

import json
import re
from types import UnionType
from typing import Any, Dict, List, Optional, Type, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from app.ai.orchestrator.interfaces import IResponseParser, ModelT
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.parser")

_FENCE_PATTERN = re.compile(r"```(?:json)?\s*([\[{].*?[\]}])\s*```", re.DOTALL)
_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
_ARRAY_PATTERN = re.compile(r"\[.*\]", re.DOTALL)


class AIResponseParseError(RuntimeError):
    """Raised when LLM output cannot be parsed/validated into the expected schema."""


def _allows_none(annotation: Any) -> bool:
    """True if the annotation is Optional[T] / T | None / Union[T, None]."""
    if annotation is type(None):
        return True
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        return any(arg is type(None) for arg in get_args(annotation))
    return False


def _unwrap_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _inner_model(annotation: Any) -> Optional[Type[BaseModel]]:
    annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)
    if origin in (list, List):
        args = get_args(annotation)
        if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
            return args[0]
        return None
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


def _default_for_null(field: FieldInfo) -> Any:
    """Best-effort replacement for an explicit JSON null on a non-Optional field."""
    if field.default is not PydanticUndefined:
        return field.default
    if field.default_factory is not None:
        return field.default_factory()
    annotation = _unwrap_optional(field.annotation)
    origin = get_origin(annotation)
    if annotation is str:
        return ""
    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if annotation is bool:
        return False
    if origin in (list, List) or annotation is list:
        return []
    if origin in (dict, Dict) or annotation is dict:
        return {}
    return None


_SCALARS = (str, int, float, bool)


def _list_element_type(annotation: Any) -> Any:
    args = get_args(_unwrap_optional(annotation))
    return args[0] if args else Any


def _coerce_shape(value: Any, annotation: Any) -> Any:
    """
    Reconcile list/scalar drift between what the model emitted and what the
    schema declares. LLMs routinely collapse a one-item `List[str]` into a bare
    sentence, or expand a `str` field into a list of bullets; both are the same
    content in the wrong container, so reshape rather than fail the whole call.
    """
    target = _unwrap_optional(annotation)
    origin = get_origin(target)

    if origin in (list, List) or target is list:
        if isinstance(value, list):
            return value
        element = _list_element_type(annotation)
        if isinstance(value, _SCALARS):
            # A str element type is the common case; anything else would only
            # trade one validation error for another, so leave it alone.
            if element in (str, Any) or not isinstance(element, type):
                return [value]
            return [value] if isinstance(value, element) else value
        if isinstance(value, dict):
            wants_object = isinstance(element, type) and (
                issubclass(element, BaseModel) or element is dict
            )
            return [value] if wants_object or element is Any else value
        return value

    if target is str and isinstance(value, list):
        parts = [str(item).strip() for item in value if isinstance(item, _SCALARS)]
        if len(parts) == len(value):
            return "; ".join(p for p in parts if p)

    return value


def coerce_nulls(data: Any, model: Type[BaseModel]) -> Any:
    """
    Recursively replace JSON `null` with the field's declared default for
    non-Optional fields, and reshape scalar/list container drift. Nested
    BaseModel / List[BaseModel] fields are walked the same way.
    """
    if not isinstance(data, dict):
        return data

    result: Dict[str, Any] = dict(data)
    for name, field in model.model_fields.items():
        if name not in result:
            continue
        value = result[name]
        annotation = field.annotation
        inner = _inner_model(annotation)

        if value is None:
            if _allows_none(annotation):
                continue
            replacement = _default_for_null(field)
            if replacement is not None or (
                field.default is not PydanticUndefined and field.default is None
            ):
                result[name] = replacement
            continue

        value = _coerce_shape(value, annotation)
        result[name] = value

        origin = get_origin(_unwrap_optional(annotation))
        if isinstance(value, dict) and inner is not None and origin not in (list, List):
            result[name] = coerce_nulls(value, inner)
        elif isinstance(value, list) and inner is not None and origin in (list, List):
            result[name] = [
                coerce_nulls(item, inner) if isinstance(item, dict) else item
                for item in value
            ]
    return result


_CONTROL_ESCAPES = {
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
}


def _escape_control_chars(text: str) -> str:
    """Escape raw control characters that appear *inside* JSON string literals.

    Tasks that ask for prose in a JSON field — the referral letter's
    `letter_body` is the clearest case — reliably come back with a real
    formatted letter: literal newlines between paragraphs, inside the quotes.
    That is invalid JSON (`Invalid control character at ...`) even though the
    content is perfectly good, so escape rather than discard it.

    Structural whitespace between tokens is left untouched; only characters
    within a string are rewritten.
    """
    out: List[str] = []
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                out.append(ch)
                escape = False
                continue
            if ch == "\\":
                out.append(ch)
                escape = True
                continue
            if ch == '"':
                in_string = False
                out.append(ch)
                continue
            mapped = _CONTROL_ESCAPES.get(ch)
            if mapped is not None:
                out.append(mapped)
                continue
            if ord(ch) < 0x20:
                out.append(f"\\u{ord(ch):04x}")
                continue
            out.append(ch)
            continue
        if ch == '"':
            in_string = True
        out.append(ch)
    return "".join(out)


def _strip_json_comments(text: str) -> str:
    """Remove `//` and `/* */` comments that sit outside string literals.

    Models like to annotate code-ish output — `"I21.9", // Myocardial
    infarction` is the classic form on the insurance coding task. JSON has no
    comment syntax, so the payload is unparseable even though the codes are
    correct. Line comments are replaced by nothing but their newline is kept,
    so the structure (and any later repair) still lines up.
    """
    out: List[str] = []
    in_string = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                newline = text.find("\n", i)
                if newline < 0:
                    break
                i = newline
                continue
            if nxt == "*":
                close = text.find("*/", i + 2)
                if close < 0:
                    break
                i = close + 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _strip_trailing_commas(text: str) -> str:
    """Drop `,` that immediately precedes a `}` or `]`, outside string literals.

    Removing a comment often leaves one behind (`"x", // note` at the end of a
    list), and models emit them unprompted too.
    """
    out: List[str] = []
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            continue
        if ch in "]}":
            k = len(out) - 1
            while k >= 0 and out[k].isspace():
                k -= 1
            if k >= 0 and out[k] == ",":
                del out[k]
        out.append(ch)
    return "".join(out)


def _repair_variants(text: str) -> List[str]:
    """Progressively repaired forms of `text`, cheapest and least invasive first.

    Each step is additive, so a response with both comments and a raw newline
    in a string is still recovered. The unmodified text is always first: a
    valid response must never be rewritten.
    """
    variants = [text]
    stripped = _strip_trailing_commas(_strip_json_comments(text))
    if stripped != text:
        variants.append(stripped)
    for base in list(variants):
        escaped = _escape_control_chars(base)
        if escaped != base:
            variants.append(escaped)
    return variants


def _extract_complete_objects(text: str) -> List[Dict[str, Any]]:
    """Pull every fully-closed `{...}` object out of truncated JSON text.

    Walks the string with a brace/string-aware scanner so an incomplete
    trailing object (the usual `max_tokens` casualty) is simply dropped
    while every earlier complete record is kept.
    """
    objects: List[Dict[str, Any]] = []
    i = 0
    n = len(text)
    while i < n:
        start = text.find("{", i)
        if start < 0:
            break
        depth = 0
        in_string = False
        escape = False
        end = -1
        for j in range(start, n):
            ch = text[j]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end < 0:
            # This `{` never closed (truncated outer wrapper, or cut mid-object).
            # Skip past it and keep scanning — complete *inner* objects may
            # still sit inside an unfinished `{"items":[ ...` envelope.
            i = start + 1
            continue
        chunk = text[start : end + 1]
        try:
            parsed = json.loads(chunk)
        except (json.JSONDecodeError, TypeError):
            i = start + 1
            continue
        if isinstance(parsed, dict):
            objects.append(parsed)
        i = end + 1
    return objects


def _salvage_truncated_json(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort recovery when `json.loads` fails on a cut-off response.

    Prefer an `"items"` array of complete objects (the shape every list-valued
    agent task uses). Fall back to the first complete top-level object if the
    response was a single record rather than a list.
    """
    objects = _extract_complete_objects(text)
    if not objects:
        return None

    # List-shaped tasks: `{"items":[...]}` — keep every complete element.
    # A single surrounding wrapper object that itself contains an incomplete
    # `items` array will not parse as one object, so we usually get the
    # inner records directly.
    if len(objects) == 1 and "items" in objects[0] and isinstance(
        objects[0].get("items"), list
    ):
        return objects[0]

    if len(objects) >= 1 and any(
        k in objects[0] for k in ("evidence_type", "title", "drug_a", "reference_id")
    ):
        logger.info(
            "Salvaged %d complete JSON object(s) from a truncated AI response.",
            len(objects),
        )
        return {"items": objects}

    # Single-record tasks (referral letter, drug analysis, …): take the
    # first complete object if it looks like a finished payload.
    if len(objects) == 1:
        logger.info("Salvaged a complete JSON object from a truncated AI response.")
        return objects[0]

    return {"items": objects}


class ResponseParser(IResponseParser):
    def extract_json(self, raw_text: str) -> Dict[str, Any]:
        text = (raw_text or "").strip()
        candidates = []

        fence_match = _FENCE_PATTERN.search(text)
        if fence_match:
            candidates.append(fence_match.group(1))

        candidates.append(text)

        object_match = _OBJECT_PATTERN.search(text)
        if object_match:
            candidates.append(object_match.group(0))

        # A bare array is a genuine response shape, but the pattern also matches
        # an array *nested inside* an object. Keeping it in a lower tier stops a
        # one-field list from being mistaken for the whole payload whenever the
        # enclosing object needs repair first.
        array_candidates = []
        array_match = _ARRAY_PATTERN.search(text)
        if array_match:
            array_candidates.append(array_match.group(0))

        # Every object-shaped candidate is exhausted — unrepaired first, then
        # progressively repaired — before a bare array is considered.
        for group in (candidates, array_candidates):
            for candidate in group:
                for variant in _repair_variants(candidate):
                    try:
                        parsed = json.loads(variant)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if isinstance(parsed, dict):
                        return parsed
                    if isinstance(parsed, list):
                        return {"items": parsed}

        for variant in _repair_variants(text):
            salvaged = _salvage_truncated_json(variant)
            if salvaged is not None:
                return salvaged

        raise AIResponseParseError(
            "Could not extract valid JSON from the AI response. "
            f"Raw response (truncated): {text[:300]!r}"
        )

    def parse(self, raw_text: str, response_model: Type[ModelT]) -> ModelT:
        data = self.extract_json(raw_text)
        data = coerce_nulls(data, response_model)
        try:
            return response_model.model_validate(data)
        except ValidationError as exc:
            raise AIResponseParseError(
                f"AI response did not match expected schema "
                f"'{response_model.__name__}': {exc}"
            ) from exc


_parser: ResponseParser | None = None


def get_response_parser() -> ResponseParser:
    global _parser
    if _parser is None:
        _parser = ResponseParser()
    return _parser
