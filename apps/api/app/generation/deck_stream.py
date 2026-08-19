from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .events import SLIDE_COMPLETED, SLOT_SNAPSHOT, GenerationEvent
from .models import DeckPlan, SlideContent, SlidePlan

_ITEM_SLOT_PATTERN = re.compile(
    r"items\.(?P<index>0|[1-9]\d*)\.(?P<field>[A-Za-z_][A-Za-z0-9_-]*)"
)


class DeckStreamError(ValueError):
    """The streamed deck violated its grammar or generation constraints."""


@dataclass(frozen=True, slots=True)
class StreamLimits:
    max_stream_chars: int = 2_000_000
    max_slot_chars: int = 100_000

    def __post_init__(self) -> None:
        if self.max_stream_chars <= 0 or self.max_slot_chars <= 0:
            raise ValueError("Stream limits must be positive")


class TaggedDeckStreamParser:
    """Incrementally parses ordered slide and named-slot markers.

    Grammar:
        deck  := slide*
        slide := [[SLIDE <id>]] slot+ [[/SLIDE]]
        slot  := [[SLOT <name>]] text [[/SLOT]]

    Slide order comes from ``DeckPlan.slides``. Slot order comes from the
    selected layout's entry in ``layout_slots``.
    """

    def __init__(
        self,
        deck_plan: DeckPlan,
        *,
        job_id: str,
        selected_layouts: Mapping[str, str],
        layout_slots: Mapping[str, Sequence[str]],
        attempt: int = 1,
        limits: StreamLimits | None = None,
    ) -> None:
        if not job_id:
            raise ValueError("Job ID must not be empty")
        if attempt < 1:
            raise ValueError("Attempt must be positive")
        slide_ids = [slide.id for slide in deck_plan.slides]
        if len(slide_ids) != len(set(slide_ids)):
            raise ValueError("Deck plan slide IDs must be unique")

        self._slides = list(deck_plan.slides)
        self._slide_ids = frozenset(slide_ids)
        self._selected_layouts = dict(selected_layouts)
        if set(self._selected_layouts) != self._slide_ids:
            raise ValueError("Selected layouts must match the deck plan slide IDs")
        self._layout_slots = {
            layout_id: tuple(slot_names)
            for layout_id, slot_names in layout_slots.items()
        }
        for layout_id, slot_names in self._layout_slots.items():
            if (
                not slot_names
                or slot_names[0] != "title"
                or len(slot_names) != len(set(slot_names))
            ):
                raise ValueError(
                    f"Layout {layout_id!r} slots must be unique and start with 'title'"
                )
            self._validate_item_slots(layout_id, slot_names)
        unknown_layouts = set(self._selected_layouts.values()) - set(self._layout_slots)
        if unknown_layouts:
            raise ValueError(
                f"Selected layouts have no slot constraints: {sorted(unknown_layouts)!r}"
            )

        self._job_id = job_id
        self._attempt = attempt
        self._limits = limits or StreamLimits()
        self._buffer = ""
        self._stream_chars = 0
        self._sequence = 0
        self._slide_index = 0
        self._current_slide: SlidePlan | None = None
        self._current_layout = ""
        self._expected_slots: tuple[str, ...] = ()
        self._slot_index = 0
        self._current_slot: str | None = None
        self._slot_text = ""
        self._slot_values: dict[str, str] = {}
        self._finished = False

    def feed(self, chunk: str) -> list[GenerationEvent]:
        if self._finished:
            raise DeckStreamError("Cannot feed a completed deck stream")
        if not isinstance(chunk, str):
            raise TypeError("Deck stream chunks must be strings")

        self._stream_chars += len(chunk)
        if self._stream_chars > self._limits.max_stream_chars:
            raise DeckStreamError("Stream output limit exceeded")
        self._buffer += chunk

        events: list[GenerationEvent] = []
        while self._buffer:
            marker_start = self._buffer.find("[[")
            if marker_start < 0:
                retained = 1 if self._buffer.endswith("[") else 0
                boundary = len(self._buffer) - retained
                events.extend(self._consume_text(self._buffer[:boundary]))
                self._buffer = self._buffer[boundary:]
                break

            if marker_start:
                events.extend(self._consume_text(self._buffer[:marker_start]))
                self._buffer = self._buffer[marker_start:]
                continue

            marker_end = self._buffer.find("]]", 2)
            if marker_end < 0:
                break
            marker = self._buffer[2:marker_end]
            self._buffer = self._buffer[marker_end + 2 :]
            events.extend(self._consume_marker(marker))

        return events

    def finish(self) -> None:
        if self._finished:
            return
        if self._buffer:
            if self._buffer.startswith("[["):
                raise DeckStreamError("Deck stream ended with an incomplete marker")
            self._consume_text(self._buffer)
            self._buffer = ""

        if self._current_slot is not None:
            raise DeckStreamError(
                f"Deck stream ended with incomplete slot {self._current_slot!r}"
            )
        if self._current_slide is not None:
            raise DeckStreamError(
                f"Deck stream ended with incomplete slide {self._current_slide.id!r}"
            )
        if self._slide_index != len(self._slides):
            raise DeckStreamError("Deck stream ended before all planned slides completed")
        self._finished = True

    def _consume_text(self, text: str) -> list[GenerationEvent]:
        if not text:
            return []
        if self._current_slot is None:
            if text.strip():
                raise DeckStreamError("Text is only allowed inside a slot")
            return []

        self._slot_text += text
        if len(self._slot_text) > self._limits.max_slot_chars:
            raise DeckStreamError(
                f"Slot output limit exceeded for {self._current_slot!r}"
            )
        return [
            self._event(
                type=SLOT_SNAPSHOT,
                slot=self._current_slot,
                data={"value": self._slot_text},
            )
        ]

    def _consume_marker(self, marker: str) -> list[GenerationEvent]:
        if marker.startswith("SLIDE "):
            self._open_slide(marker.removeprefix("SLIDE "))
            return []
        if marker.startswith("SLOT "):
            self._open_slot(marker.removeprefix("SLOT "))
            return []
        if marker == "/SLOT":
            self._close_slot()
            return []
        if marker == "/SLIDE":
            return [self._close_slide()]
        raise DeckStreamError(f"Unknown marker [[{marker}]]")

    def _open_slide(self, slide_id: str) -> None:
        if self._current_slide is not None:
            raise DeckStreamError("Cannot open a slide before closing the current slide")
        if self._slide_index >= len(self._slides):
            raise DeckStreamError(f"Unknown slide {slide_id!r}")

        expected = self._slides[self._slide_index]
        if slide_id not in self._slide_ids:
            raise DeckStreamError(f"Unknown slide {slide_id!r}")
        if slide_id != expected.id:
            raise DeckStreamError(
                f"Expected slide {expected.id!r}, received {slide_id!r}"
            )
        layout_id = self._selected_layouts[slide_id]

        self._current_slide = expected
        self._current_layout = layout_id
        self._expected_slots = self._layout_slots[layout_id]
        self._slot_index = 0
        self._slot_values = {}

    def _open_slot(self, slot: str) -> None:
        if self._current_slide is None:
            raise DeckStreamError("Cannot open a slot outside a slide")
        if self._current_slot is not None:
            raise DeckStreamError("Cannot open a slot before closing the current slot")
        if (
            slot == "items" or slot.startswith("items.")
        ) and _ITEM_SLOT_PATTERN.fullmatch(slot) is None:
            raise DeckStreamError(f"Malformed item slot {slot!r}")
        if slot not in self._expected_slots:
            raise DeckStreamError(
                f"Unknown slot {slot!r} for layout {self._current_layout!r}"
            )
        if self._slot_index >= len(self._expected_slots):
            raise DeckStreamError(f"Unexpected duplicate slot {slot!r}")

        expected = self._expected_slots[self._slot_index]
        if slot != expected:
            raise DeckStreamError(f"Expected slot {expected!r}, received {slot!r}")
        self._current_slot = slot
        self._slot_text = ""

    def _close_slot(self) -> None:
        if self._current_slot is None:
            raise DeckStreamError("Cannot close a slot when no slot is open")
        self._slot_values[self._current_slot] = self._slot_text
        self._slot_index += 1
        self._current_slot = None
        self._slot_text = ""

    def _close_slide(self) -> GenerationEvent:
        if self._current_slide is None:
            raise DeckStreamError("Cannot close a slide when no slide is open")
        if self._current_slot is not None:
            raise DeckStreamError("Cannot close a slide before closing its slot")
        if self._slot_index < len(self._expected_slots):
            missing = self._expected_slots[self._slot_index]
            raise DeckStreamError(
                f"Cannot close slide {self._current_slide.id!r}: missing slot {missing!r}"
            )

        slide = self._current_slide
        content = SlideContent(
            slide_id=slide.id,
            title=self._slot_values["title"],
            layout_id=self._current_layout,
            slots=self._assemble_slots(),
        )
        event = self._event(
            type=SLIDE_COMPLETED,
            slot=None,
            data={"content": content},
        )
        self._slide_index += 1
        self._current_slide = None
        self._current_layout = ""
        self._expected_slots = ()
        self._slot_index = 0
        self._slot_values = {}
        return event

    def _assemble_slots(self) -> dict[str, object]:
        slots: dict[str, object] = {}
        items: dict[int, dict[str, str]] = {}
        for slot in self._expected_slots:
            if slot == "title":
                continue
            item_slot = _ITEM_SLOT_PATTERN.fullmatch(slot)
            if item_slot is None:
                slots[slot] = self._slot_values[slot]
                continue
            index = int(item_slot.group("index"))
            field = item_slot.group("field")
            items.setdefault(index, {})[field] = self._slot_values[slot]
        if items:
            slots["items"] = [items[index] for index in range(len(items))]
        return slots

    @staticmethod
    def _validate_item_slots(layout_id: str, slot_names: Sequence[str]) -> None:
        item_indices: set[int] = set()
        for slot in slot_names:
            if slot == "items" or slot.startswith("items."):
                item_slot = _ITEM_SLOT_PATTERN.fullmatch(slot)
                if item_slot is None:
                    raise ValueError(
                        f"Malformed item slot {slot!r} for layout {layout_id!r}"
                    )
                item_indices.add(int(item_slot.group("index")))
            elif "." in slot:
                raise ValueError(
                    f"Malformed dotted slot {slot!r} for layout {layout_id!r}"
                )
        if item_indices and item_indices != set(range(max(item_indices) + 1)):
            raise ValueError(
                f"Item slots for layout {layout_id!r} must use contiguous indices"
            )

    def _event(
        self,
        *,
        type: str,
        slot: str | None,
        data: dict[str, object],
    ) -> GenerationEvent:
        if self._current_slide is None:
            raise RuntimeError("Cannot emit an event outside a slide")
        self._sequence += 1
        return GenerationEvent(
            version=1,
            type=type,
            job_id=self._job_id,
            attempt=self._attempt,
            sequence=self._sequence,
            slide_id=self._current_slide.id,
            slot=slot,
            data=data,
        )
