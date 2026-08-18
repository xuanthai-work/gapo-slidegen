from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_ICON_ROOT = Path(__file__).with_name("assets") / "icons" / "phosphor"
_MANIFEST_PATH = _ICON_ROOT / "manifest.json"
_SVG_DIR = _ICON_ROOT / "SVGs" / "regular"

ROLE_ICON_BASENAMES: dict[str, str] = {
    "cover": "presentation-chart",
    "agenda": "list-bullets",
    "section": "squares-four",
    "hook": "lightning",
    "problem": "warning-circle",
    "solution": "gear-six",
    "big-stat": "chart-line-up",
    "comparison": "arrows-left-right",
    "process": "flow-arrow",
    "timeline": "clock-countdown",
    "features": "sparkle",
    "case-study": "trend-up",
    "quote": "quotes",
    "team": "users-three",
    "cta": "rocket-launch",
    "summary": "check-circle",
    "content": "article",
}

SLOT_ICON_HINTS: tuple[tuple[str, str], ...] = (
    ("chart", "chart-line-up"),
    ("metric", "chart-bar"),
    ("data", "database"),
    ("team", "users-three"),
    ("code", "code"),
    ("flow", "flow-arrow"),
    ("network", "share-network"),
    ("security", "shield-check"),
    ("cloud", "cloud"),
    ("launch", "rocket-launch"),
    ("visual", "presentation-chart"),
    ("image", "image"),
    ("photo", "camera"),
    ("card", "identification-card"),
)

KEYWORD_ICON_BASENAMES: dict[str, str] = {
    "workflow": "flow-arrow",
    "automation": "gear-six",
    "integrate": "plugs-connected",
    "integration": "plugs-connected",
    "api": "code",
    "code": "code",
    "data": "database",
    "database": "database",
    "analytics": "chart-line-up",
    "metric": "chart-bar",
    "growth": "trend-up",
    "team": "users-three",
    "security": "shield-check",
    "cloud": "cloud",
    "launch": "rocket-launch",
    "target": "target",
    "process": "flow-arrow",
    "timeline": "clock-countdown",
    "compare": "arrows-left-right",
    "comparison": "scales",
    "quote": "quotes",
    "learn": "graduation-cap",
    "guide": "map-trifold",
    "build": "hammer",
    "deploy": "rocket-launch",
    "monitor": "pulse",
    "alert": "bell-ringing",
    "success": "check-circle",
    "error": "warning-circle",
    "bug": "bug",
    "network": "share-network",
    "branch": "git-branch",
    "node": "circles-three-plus",
    "json": "brackets-curly",
    "slack": "chat-circle-dots",
    "email": "envelope-simple",
    "webhook": "webhooks-logo",
}

_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "with", "is", "are",
    "was", "were", "be", "this", "that", "these", "those", "your", "our", "their",
    "from", "by", "at", "as", "it", "its", "we", "you", "they", "can", "will", "how",
    "what", "when", "where", "why", "who", "which", "into", "via", "using", "use",
})


@lru_cache(maxsize=1)
def _manifest() -> dict[str, object]:
    if not _MANIFEST_PATH.exists():
        return {}
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _svg_index() -> dict[str, Path]:
    if not _SVG_DIR.exists():
        return {}
    return {
        path.stem: path
        for path in _SVG_DIR.glob("*.svg")
        if path.is_file()
    }


def resolve_icon_path(key: str) -> Path | None:
    basename = ROLE_ICON_BASENAMES.get(key, key)
    indexed = _svg_index().get(basename)
    if indexed is not None:
        return indexed

    data = _manifest()
    if not isinstance(data, dict):
        return None
    icons = data.get("icons")
    base = data.get("basePath")
    if not isinstance(icons, dict) or not isinstance(base, str):
        return None
    filename = icons.get(key)
    if not isinstance(filename, str):
        return None
    path = _ICON_ROOT / base / filename
    return path if path.exists() else None


@lru_cache(maxsize=256)
def resolve_icon_svg(key: str) -> str | None:
    path = resolve_icon_path(key)
    if path is None:
        return None
    return path.read_text(encoding="utf-8")


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if len(token) > 2 and token not in _STOP_WORDS]


def _match_keyword_icon(text: str) -> str | None:
    tokens = _tokenize(text)
    for token in tokens:
        basename = KEYWORD_ICON_BASENAMES.get(token)
        if basename and basename in _svg_index():
            return basename
    for token in tokens:
        for keyword, basename in KEYWORD_ICON_BASENAMES.items():
            if keyword in token and basename in _svg_index():
                return basename
    return None


def _match_slot_icon(slot_name: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "_", slot_name.lower()).strip("_")
    for token, basename in SLOT_ICON_HINTS:
        if token in normalized and basename in _svg_index():
            return basename
    return None


def resolve_icon_for_context(
    *,
    role: str | None = None,
    slot_name: str = "",
    title: str = "",
    content: str = "",
) -> str | None:
    slot_match = _match_slot_icon(slot_name)
    if slot_match:
        svg = resolve_icon_svg(slot_match)
        if svg:
            return svg

    keyword_match = _match_keyword_icon(f"{title} {content}")
    if keyword_match:
        svg = resolve_icon_svg(keyword_match)
        if svg:
            return svg

    if role:
        role_basename = ROLE_ICON_BASENAMES.get(role)
        if role_basename and role_basename in _svg_index():
            svg = resolve_icon_svg(role_basename)
            if svg:
                return svg

    return resolve_icon_svg("presentation-chart")
