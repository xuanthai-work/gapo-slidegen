"""CLI-backed slide rasterizer (placeholder until Task 8)."""

from __future__ import annotations


class CliSlideRasterizer:
    name = "cli"

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    def rasterize(self, slide: dict[str, object]) -> bytes:
        raise RuntimeError("CLI rasterizer is not implemented")
