"""Legacy Google AI Studio provider tests.

The live `GoogleAIStudioProvider` is commented out in `gemini_provider.py` so
these tests are skipped by default. They remain as a reference for re-enabling
the provider later.
"""

from __future__ import annotations

import pytest

from app.generation.outline_schema import GeneratedOutlineResponse


pytestmark = pytest.mark.skip(reason="Gemini provider is disabled; kept as legacy fallback")


def _placeholder() -> None:
    """Keep the module importable when no live provider is present."""
    schema = GeneratedOutlineResponse.model_json_schema()
    assert "items" in schema
