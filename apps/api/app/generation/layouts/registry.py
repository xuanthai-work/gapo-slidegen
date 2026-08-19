from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ContentConstraints:
    title_max_chars: int
    content_max_chars: int
    block_heading_max_chars: int
    block_body_max_chars: int
    max_items: int

    def as_budget(self) -> dict[str, int]:
        return {
            "title_max_chars": self.title_max_chars,
            "content_max_chars": self.content_max_chars,
            "block_heading_max_chars": self.block_heading_max_chars,
            "block_body_max_chars": self.block_body_max_chars,
        }


@dataclass(frozen=True, slots=True)
class NativeLayoutContext:
    title: str
    body: str
    theme_id: str
    colors: dict[str, str]
    fonts: dict[str, str]
    index: int = 0
    total: int = 1
    blocks: list[dict[str, object]] = field(default_factory=list)


NativeLayoutCompiler = Callable[[NativeLayoutContext], dict[str, object]]


@dataclass(frozen=True, slots=True)
class NativeLayoutDefinition:
    id: str
    constraints: ContentConstraints
    compile: NativeLayoutCompiler


class NativeLayoutRegistry:
    def __init__(self) -> None:
        self._layouts: dict[str, NativeLayoutDefinition] = {}

    @property
    def layout_ids(self) -> tuple[str, ...]:
        return tuple(self._layouts)

    def register(self, definition: NativeLayoutDefinition) -> None:
        if definition.id in self._layouts:
            raise ValueError(f"Native layout {definition.id!r} is already registered")
        self._layouts[definition.id] = definition

    def content_constraints(self, layout_id: str) -> ContentConstraints:
        return self._get(layout_id).constraints

    def compile(
        self,
        layout_id: str,
        context: NativeLayoutContext,
    ) -> dict[str, object]:
        return self._get(layout_id).compile(context)

    def _get(self, layout_id: str) -> NativeLayoutDefinition:
        try:
            return self._layouts[layout_id]
        except KeyError as error:
            raise ValueError(f"Unknown native layout: {layout_id}") from error
