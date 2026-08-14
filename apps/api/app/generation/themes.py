from typing import Final


THEMES: Final[dict[str, dict[str, object]]] = {
    "modern-blue": {
        "id": "modern-blue",
        "name": "Modern Blue",
        "colors": {
            "background": "#FFFFFF",
            "surface": "#F5F8FE",
            "primary": "#1E4CD9",
            "secondary": "#234CD9",
            "accent": "#1E4CD9",
            "text": "#334155",
            "muted": "#64748B",
        },
        "fonts": {"heading": "Montserrat", "body": "Montserrat"},
    },
    "editorial-cobalt": {
        "id": "editorial-cobalt",
        "name": "Editorial Cobalt",
        "colors": {
            "background": "#F3F5F8",
            "surface": "#FFFFFF",
            "primary": "#2457C5",
            "secondary": "#10182A",
            "accent": "#E8B04A",
            "text": "#172033",
            "muted": "#667085",
        },
        "fonts": {"heading": "Aptos Display", "body": "Aptos"},
    },
    "warm-studio": {
        "id": "warm-studio",
        "name": "Warm Studio",
        "colors": {
            "background": "#F2EDE5",
            "surface": "#FFFCF7",
            "primary": "#B94D32",
            "secondary": "#292521",
            "accent": "#D7A642",
            "text": "#292521",
            "muted": "#756B63",
        },
        "fonts": {"heading": "Georgia", "body": "Aptos"},
    },
    "midnight-signal": {
        "id": "midnight-signal",
        "name": "Midnight Signal",
        "colors": {
            "background": "#0D1526",
            "surface": "#17243B",
            "primary": "#4B7EF2",
            "secondary": "#080F1D",
            "accent": "#F2B95F",
            "text": "#F8FAFC",
            "muted": "#A9B6CA",
        },
        "fonts": {"heading": "Aptos Display", "body": "Aptos"},
    },
}

DEFAULT_THEME_ID: Final = "modern-blue"


def get_theme(theme_id: str) -> dict[str, object]:
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME_ID])
