"""JSON schemas shown to LLMs, without copy-length constraints."""

from __future__ import annotations

import json
from typing import Any

_LENGTH_KEYS = frozenset({"minLength", "maxLength"})


def llm_json_schema(schema_model: type) -> str:
    """Dump a Pydantic model as JSON Schema without string length caps.

    Validation still uses the model. This dump is prompt-only, so the model is
    not steered toward writing under ``maxLength``.
    """

    return json.dumps(_strip_for_llm(schema_model.model_json_schema()), ensure_ascii=False)


def _strip_for_llm(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            key: _strip_for_llm(value)
            for key, value in node.items()
            if key not in _LENGTH_KEYS
        }
    if isinstance(node, list):
        return [_strip_for_llm(item) for item in node]
    return node
