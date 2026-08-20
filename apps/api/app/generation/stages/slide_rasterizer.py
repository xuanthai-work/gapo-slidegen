"""CLI-backed slide rasterizer."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from .orchestrator import SlideValidationFailed


class CliSlideRasterizer:
    name = "cli"

    def __init__(
        self,
        *,
        command: str,
        repo_root: Path,
        timeout_seconds: float = 30,
        save_screenshots: bool = False,
        storage_root: Path | None = None,
    ) -> None:
        self.command = command
        self.repo_root = Path(repo_root)
        self.timeout_seconds = timeout_seconds
        self.save_screenshots = save_screenshots
        self.storage_root = storage_root

    def rasterize(self, slide: dict[str, object]) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            slide_path = Path(tmp) / "slide.json"
            out_path = Path(tmp) / "slide.png"
            slide_path.write_text(json.dumps(slide), encoding="utf-8")
            argv = [
                *shlex.split(self.command, posix=os.name != "nt"),
                "--slide",
                str(slide_path),
                "--out",
                str(out_path),
            ]
            try:
                completed = subprocess.run(
                    argv,
                    cwd=self.repo_root,
                    timeout=self.timeout_seconds,
                    check=False,
                    capture_output=True,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise SlideValidationFailed(
                    "Slide failed visual validation: VISUAL_RASTERIZE_FAILED"
                ) from error
            if completed.returncode != 0 or not out_path.is_file():
                raise SlideValidationFailed(
                    "Slide failed visual validation: VISUAL_RASTERIZE_FAILED"
                )
            data = out_path.read_bytes()
            if not data.startswith(b"\x89PNG"):
                raise SlideValidationFailed(
                    "Slide failed visual validation: VISUAL_RASTERIZE_FAILED"
                )
            self._maybe_dump_screenshot(slide, data)
            return data

    def _maybe_dump_screenshot(self, slide: dict[str, object], data: bytes) -> None:
        if not self.save_screenshots or self.storage_root is None:
            return
        slide_id = str(slide.get("id") or "unknown")
        dump_path = Path(self.storage_root) / "visual-gate" / f"{slide_id}.png"
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        dump_path.write_bytes(data)
