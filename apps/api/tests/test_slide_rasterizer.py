from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.generation.stages.orchestrator import SlideValidationFailed
from app.generation.stages.slide_rasterizer import CliSlideRasterizer

REPO_ROOT = Path(__file__).resolve().parents[3]
FAKE_RASTERIZE = "apps/api/tests/fixtures/fake_rasterize.py"
FAKE_RASTERIZE_BAD = "apps/api/tests/fixtures/fake_rasterize_bad.py"


def _command(script: str) -> str:
    return f"{sys.executable} {script}"


def test_cli_rasterizer_returns_png() -> None:
    rasterizer = CliSlideRasterizer(
        command=_command(FAKE_RASTERIZE),
        repo_root=REPO_ROOT,
        timeout_seconds=10,
    )
    png = rasterizer.rasterize({"id": "s1", "background": "#fff", "elements": []})
    assert png.startswith(b"\x89PNG")


def test_cli_rasterizer_non_png_fails() -> None:
    rasterizer = CliSlideRasterizer(
        command=_command(FAKE_RASTERIZE_BAD),
        repo_root=REPO_ROOT,
        timeout_seconds=10,
    )
    with pytest.raises(SlideValidationFailed, match="VISUAL_RASTERIZE_FAILED"):
        rasterizer.rasterize({"id": "s1", "background": "#fff", "elements": []})


def test_cli_rasterizer_nonzero_exit_fails() -> None:
    rasterizer = CliSlideRasterizer(
        command=_command("-c \"raise SystemExit(1)\""),
        repo_root=REPO_ROOT,
        timeout_seconds=10,
    )
    with pytest.raises(SlideValidationFailed, match="VISUAL_RASTERIZE_FAILED"):
        rasterizer.rasterize({"id": "s1", "background": "#fff", "elements": []})
