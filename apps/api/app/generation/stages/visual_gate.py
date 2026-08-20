from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Literal, Protocol

from ..models import SlideContent

VisualIssueCode = Literal["TEXT_MISSING", "TEXT_TRUNCATED", "TEXT_UNREADABLE"]
_ALLOWED_CODES = frozenset({"TEXT_MISSING", "TEXT_TRUNCATED", "TEXT_UNREADABLE"})


@dataclass(frozen=True, slots=True)
class VisualIssue:
    code: VisualIssueCode
    message: str
    slot: str | None = None
    element_ids: tuple[str, ...] = ()
    expected: str = ""
    observed: str = ""


@dataclass(frozen=True, slots=True)
class VisualGateResult:
    extracted_text: str
    issues: list[VisualIssue] = field(default_factory=list)

    @property
    def readable(self) -> bool:
        return not self.issues


class VisualGate(Protocol):
    name: str

    def inspect(
        self,
        *,
        png: bytes,
        slide: dict[str, object],
        content: SlideContent,
    ) -> VisualGateResult:
        ...


def intended_slots(content: SlideContent) -> list[tuple[str, str]]:
    slots: list[tuple[str, str]] = []
    title = content.title.strip()
    if title:
        slots.append(("title", title))
    body = content.slots.get("body")
    if isinstance(body, str) and body.strip():
        slots.append(("body", body.strip()))
    items = content.slots.get("items")
    if isinstance(items, list):
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for field_name in ("heading", "body", "label", "value"):
                value = item.get(field_name)
                if isinstance(value, str) and value.strip():
                    slots.append((f"items.{index}.{field_name}", value.strip()))
    return slots


def normalize_text(value: str) -> str:
    collapsed = " ".join(value.split())
    return unicodedata.normalize("NFC", collapsed).casefold()


def _lcs_len(left: str, right: str) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    for left_ch in left:
        current = [0]
        for index, right_ch in enumerate(right):
            if left_ch == right_ch:
                current.append(previous[index] + 1)
            else:
                current.append(max(previous[index + 1], current[-1]))
        previous = current
    return previous[-1]


def coverage(expected: str, extracted: str) -> float:
    if not expected:
        return 1.0
    if expected in extracted:
        return 1.0
    return _lcs_len(expected, extracted) / len(expected)


def classify_extracted_text(
    *,
    extracted: str,
    unreadable: bool,
    content: SlideContent,
) -> VisualGateResult:
    slots = intended_slots(content)
    observed = normalize_text(extracted)
    if not slots:
        return VisualGateResult(extracted_text=extracted, issues=[])
    concat = normalize_text(" ".join(text for _, text in slots))
    first_slot, first_expected = slots[0]
    if unreadable or (not observed and concat) or (
        len(concat) >= 20 and coverage(concat, observed) < 0.30
    ):
        return VisualGateResult(
            extracted_text=extracted,
            issues=[
                VisualIssue(
                    code="TEXT_UNREADABLE",
                    message=f"Slide text is not readable in the screenshot ({first_slot}).",
                    slot=first_slot,
                    expected=first_expected,
                    observed=extracted,
                )
            ],
        )
    issues: list[VisualIssue] = []
    for slot, expected_raw in slots:
        expected = normalize_text(expected_raw)
        score = coverage(expected, observed)
        code: VisualIssueCode | None = None
        if score < 0.50:
            code = "TEXT_MISSING"
        elif 0.50 <= score < 0.85:
            code = "TEXT_TRUNCATED"
        elif (
            len(expected) >= 24
            and score < 0.95
            and expected[: max(1, len(expected) // 2)] in observed
        ):
            code = "TEXT_TRUNCATED"
        if code is None:
            continue
        issues.append(
            VisualIssue(
                code=code,
                message=f"Slot {slot!r} failed visual readability ({code}).",
                slot=slot,
                expected=expected_raw,
                observed=extracted,
            )
        )
    return VisualGateResult(extracted_text=extracted, issues=issues)
