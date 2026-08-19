"""Shared copy-length helpers for generation stages."""


def truncate_content_text(text: str, limit: int) -> str:
    """Fit copy to a layout bound, preferring a complete sentence over a mid-word cut."""

    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    if limit <= 0:
        return ""
    window = cleaned[:limit]
    sentence_end = -1
    for index, char in enumerate(window):
        if char not in ".!?":
            continue
        nxt = window[index + 1] if index + 1 < len(window) else ""
        if nxt == "" or nxt.isspace():
            sentence_end = index
    if sentence_end + 1 >= max(limit // 2, 1):
        return cleaned[: sentence_end + 1].strip()
    last_space = window.rfind(" ")
    if last_space > int(limit * 0.7):
        return window[:last_space].rstrip(" .,;:-")
    return window.rstrip(" .,;:-")
