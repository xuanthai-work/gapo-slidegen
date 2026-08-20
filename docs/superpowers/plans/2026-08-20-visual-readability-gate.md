# Visual Readability Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After geometry validation, generation screenshots each slide at 1280×720, OCR-checks intended copy, and either truncates, switches to the next ranked layout, or fails the job.

**Architecture:** Keep `RuleBasedSlideValidator` geometry-only. Add optional `SlideRasterizer` + `VisualGate` on `GenerationPipeline.accept_slide`. `RepairDispatcher` executes a closed catalog (`tighter_truncate` | `next_ranked_layout` | `fail`). Playwright lives in `packages/slide-rasterizer` (Node CLI); Python shells out. Default flag off.

**Tech Stack:** Python 3.12, pytest, Pydantic, httpx, React 19.2.8, Konva 10.3.0, Playwright 1.50, Vite

**Spec:** `docs/superpowers/specs/2026-08-20-visual-readability-gate-design.md`

## Global Constraints

- Do not change `RuleBasedSlideValidator` issue codes (`ELEMENT_OUT_OF_BOUNDS`, `ELEMENT_OVERLAP`, `FONT_TOO_SMALL`).
- Do not add Presenton layouts, Art Director, VisualPlan, or `repair_instruction: str`.
- Do not add Playwright to `apps/api` Python dependencies.
- Konva 10.3.0, react-konva 19.2.5, React 19.2.8, Playwright 1.50.
- Screenshot the editor Konva tree (`SlideCanvas` read-only), never `SlideThumbnail`.
- Default `SLIDEGEN_VISUAL_GATE_ENABLED=false`. Stub provider never enables the gate.
- Default pytest must not launch Chromium or call the gateway.
- Windows: rasterizer CLI is `node …`, not a Unix-only shell script.
- Reuse `constrain_slide_content`; do not add a third truncate helper.
- Job `error_code` stays `generation_failed`; visual codes go in `SlideValidationFailed` message.
- Drop unknown visual issue codes; never execute free-form model prose.

## File map

| File | Responsibility |
|---|---|
| `apps/api/app/generation/stages/visual_gate.py` | `VisualIssue` types, coverage classifier, `VisualGate` protocol, `CompanyGatewayOcrVisualGate` |
| `apps/api/app/generation/stages/repair_dispatcher.py` | Choose/apply closed repair actions |
| `apps/api/app/generation/stages/slide_rasterizer.py` | `SlideRasterizer` protocol + `CliSlideRasterizer` |
| `apps/api/app/generation/stages/layout_selector.py` | `rank()` on dispatch + native |
| `apps/api/app/generation/stages/protocols.py` | `LayoutSelector.rank` |
| `apps/api/app/generation/stages/orchestrator.py` | `accept_slide` / `accept_document` |
| `apps/api/app/generation/factory.py` | Flag wiring |
| `apps/api/app/generation/worker.py` | Call `accept_slide` after compile (batch + stream compile closure) |
| `apps/api/app/config.py`, `.env.example` | Settings |
| `packages/slide-rasterizer/` | Konva + Playwright CLI |
| `docs/generation-pipeline-architecture.md` | Operational call counts |

---

### Task 1: OCR coverage classifier

**Files:**
- Create: `apps/api/app/generation/stages/visual_gate.py`
- Test: `apps/api/tests/test_visual_gate.py`

**Interfaces:**
- Consumes: `SlideContent` (`apps/api/app/generation/models/plans.py`)
- Produces: `VisualIssue`, `VisualGateResult`, `classify_extracted_text(...)`, `intended_slots(...)`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/test_visual_gate.py`:

```python
from app.generation.models import SlideContent
from app.generation.stages.visual_gate import classify_extracted_text


def _content(*, title: str, body: str, items: list[dict[str, str]] | None = None) -> SlideContent:
    slots: dict[str, object] = {"body": body}
    if items is not None:
        slots["items"] = items
    return SlideContent(slide_id="s1", title=title, layout_id="list", slots=slots)


def test_substring_match_is_readable() -> None:
    result = classify_extracted_text(
        extracted="Quarterly Review Teams lost 12 hours formatting slides.",
        unreadable=False,
        content=_content(
            title="Quarterly Review",
            body="Teams lost 12 hours formatting slides.",
        ),
    )
    assert result.readable
    assert result.issues == []


def test_missing_title_emits_text_missing() -> None:
    result = classify_extracted_text(
        extracted="Some other chrome on the canvas",
        unreadable=False,
        content=_content(title="Quarterly Review", body=""),
    )
    assert [issue.code for issue in result.issues] == ["TEXT_MISSING"]
    assert result.issues[0].slot == "title"


def test_partial_body_emits_text_truncated() -> None:
    body = "Teams lost twelve hours every week formatting slides for the board."
    result = classify_extracted_text(
        extracted="Quarterly Review Teams lost twelve hours every",
        unreadable=False,
        content=_content(title="Quarterly Review", body=body),
    )
    codes = {(issue.slot, issue.code) for issue in result.issues}
    assert ("body", "TEXT_TRUNCATED") in codes


def test_model_unreadable_flag_wins() -> None:
    result = classify_extracted_text(
        extracted="Quarterly Review Teams lost 12 hours formatting slides.",
        unreadable=True,
        content=_content(
            title="Quarterly Review",
            body="Teams lost 12 hours formatting slides.",
        ),
    )
    assert [issue.code for issue in result.issues] == ["TEXT_UNREADABLE"]


def test_empty_extraction_with_copy_is_unreadable() -> None:
    result = classify_extracted_text(
        extracted="",
        unreadable=False,
        content=_content(title="Quarterly Review", body="Body copy here."),
    )
    assert [issue.code for issue in result.issues] == ["TEXT_UNREADABLE"]


def test_vietnamese_diacritics_match_after_nfc() -> None:
    title = "Báo cáo quý"
    result = classify_extracted_text(
        extracted="Báo cáo quý Nội dung slide.",
        unreadable=False,
        content=_content(title=title, body="Nội dung slide."),
    )
    assert result.readable
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --project apps/api pytest apps/api/tests/test_visual_gate.py -v
```

Expected: FAIL with `ModuleNotFoundError: visual_gate`

- [ ] **Step 3: Write the classifier**

Create `apps/api/app/generation/stages/visual_gate.py`:

```python
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
```

Do not add `CompanyGatewayOcrVisualGate` in this task.

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run --project apps/api pytest apps/api/tests/test_visual_gate.py -v
```

Expected: PASS. If `test_partial_body_emits_text_truncated` fails because coverage ≥ 0.85, lengthen the fixture body until truncated, do not loosen thresholds.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/generation/stages/visual_gate.py apps/api/tests/test_visual_gate.py
git commit -m "$(cat <<'EOF'
feat: classify OCR coverage into visual readability issues

EOF
)"
```

---

### Task 2: RepairDispatcher

**Files:**
- Create: `apps/api/app/generation/stages/repair_dispatcher.py`
- Test: `apps/api/tests/test_repair_dispatcher.py`

**Interfaces:**
- Consumes: `VisualIssue` from Task 1; `ContentConstraints`; `constrain_slide_content`; `LayoutCandidateScore`
- Produces: `choose_repair_action`, `apply_repair_action`, `scale_constraints`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/test_repair_dispatcher.py`:

```python
import pytest

from app.generation.layouts import ContentConstraints
from app.generation.models import SlideContent
from app.generation.stages.layout_selector import LayoutCandidateScore
from app.generation.stages.models import StoryOutlineItem
from app.generation.stages.repair_dispatcher import (
    apply_repair_action,
    choose_repair_action,
)
from app.generation.stages.visual_gate import VisualIssue


def _issue(code: str, slot: str = "body") -> VisualIssue:
    return VisualIssue(code=code, message=code, slot=slot, expected="x", observed="y")


def test_unreadable_chooses_next_layout() -> None:
    assert choose_repair_action([_issue("TEXT_UNREADABLE", "title")]) == "next_ranked_layout"


def test_missing_title_chooses_next_layout() -> None:
    assert choose_repair_action([_issue("TEXT_MISSING", "title")]) == "next_ranked_layout"


def test_truncated_body_chooses_tighter_truncate() -> None:
    assert choose_repair_action([_issue("TEXT_TRUNCATED", "body")]) == "tighter_truncate"


def test_unknown_codes_are_ignored_then_fail_if_nothing_left() -> None:
    mystery = VisualIssue(code="TEXT_MISSING", message="x")  # no slot → fail path after ignore? 
    assert choose_repair_action([]) == "fail"


def test_tighter_truncate_shrinks_body_and_drops_last_item() -> None:
    content = SlideContent(
        slide_id="s1",
        title="Title text that is long enough",
        layout_id="grid",
        slots={
            "body": "Sentence one. Sentence two. Sentence three. Sentence four.",
            "items": [
                {"heading": "A", "body": "Alpha point with a full sentence."},
                {"heading": "B", "body": "Bravo point with a full sentence."},
            ],
        },
    )
    item = StoryOutlineItem(id="s1", title="Title", content="x", layout_id="grid")
    constraints = ContentConstraints(72, 100, 40, 80, 2)
    next_content = apply_repair_action(
        "tighter_truncate",
        item=item,
        content=content,
        constraints=constraints,
        ranking=[],
        tried=set(),
        issues=[_issue("TEXT_TRUNCATED", "items.1.body")],
    )
    assert item.layout_id == "grid"
    assert isinstance(next_content.slots["items"], list)
    assert len(next_content.slots["items"]) == 1
    original_body = str(content.slots["body"])
    repaired_body = str(next_content.slots["body"])
    assert len(repaired_body) <= max(48, int(100 * 0.7))
    assert len(repaired_body) <= len(original_body)


def test_next_ranked_layout_sets_layout_id_and_skips_tried() -> None:
    content = SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "Hello world."})
    item = StoryOutlineItem(id="s1", title="T", content="Hello world.", layout_id="grid")
    ranking = [
        LayoutCandidateScore("grid", 10, ("current",)),
        LayoutCandidateScore("list", 8, ("next",)),
    ]
    next_content = apply_repair_action(
        "next_ranked_layout",
        item=item,
        content=content,
        constraints=ContentConstraints(72, 240, 60, 180, 6),
        ranking=ranking,
        tried={"grid"},
        issues=[_issue("TEXT_UNREADABLE", "title")],
    )
    assert item.layout_id == "list"
    assert next_content.layout_id == "list"


def test_next_ranked_layout_fails_when_exhausted() -> None:
    from app.generation.stages.orchestrator import SlideValidationFailed

    content = SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "Hi"})
    item = StoryOutlineItem(id="s1", title="T", content="Hi", layout_id="grid")
    with pytest.raises(SlideValidationFailed, match="TEXT_UNREADABLE"):
        apply_repair_action(
            "next_ranked_layout",
            item=item,
            content=content,
            constraints=ContentConstraints(72, 240, 60, 180, 6),
            ranking=[LayoutCandidateScore("grid", 10, ("only",))],
            tried={"grid"},
            issues=[_issue("TEXT_UNREADABLE", "title")],
        )
```

Fix `test_unknown_codes_are_ignored_then_fail_if_nothing_left` before committing to this exact assertion:

```python
def test_empty_issues_choose_fail() -> None:
    assert choose_repair_action([]) == "fail"
```

Delete the broken `mystery` test. Add:

```python
def test_priority_unreadable_beats_truncated() -> None:
    assert (
        choose_repair_action(
            [
                _issue("TEXT_TRUNCATED", "body"),
                _issue("TEXT_UNREADABLE", "title"),
            ]
        )
        == "next_ranked_layout"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run --project apps/api pytest apps/api/tests/test_repair_dispatcher.py -v
```

Expected: FAIL with `ModuleNotFoundError: repair_dispatcher`

- [ ] **Step 3: Implement the dispatcher**

Create `apps/api/app/generation/stages/repair_dispatcher.py`:

```python
from __future__ import annotations

from typing import Literal

from ..content_schema import constrain_slide_content
from ..layouts import ContentConstraints
from ..models import SlideContent
from .layout_selector import LayoutCandidateScore
from .models import StoryOutlineItem
from .orchestrator import SlideValidationFailed
from .visual_gate import VisualIssue

RepairAction = Literal["tighter_truncate", "next_ranked_layout", "fail"]
VISUAL_GATE_MAX_REPAIRS = 2


def choose_repair_action(issues: list[VisualIssue]) -> RepairAction:
    if any(issue.code == "TEXT_UNREADABLE" for issue in issues):
        return "next_ranked_layout"
    if any(issue.code == "TEXT_MISSING" and issue.slot == "title" for issue in issues):
        return "next_ranked_layout"
    if any(
        issue.code in {"TEXT_MISSING", "TEXT_TRUNCATED"}
        and (issue.slot or "").startswith(("body", "items"))
        for issue in issues
    ):
        return "tighter_truncate"
    return "fail"


def scale_constraints(constraints: ContentConstraints, *, drop_last_item: bool) -> ContentConstraints:
    max_items = constraints.max_items
    if drop_last_item and max_items > 1:
        max_items -= 1
    return ContentConstraints(
        title_max_chars=max(24, int(constraints.title_max_chars * 0.7)),
        content_max_chars=max(48, int(constraints.content_max_chars * 0.7)),
        block_heading_max_chars=max(16, int(constraints.block_heading_max_chars * 0.7)),
        block_body_max_chars=max(32, int(constraints.block_body_max_chars * 0.7)),
        max_items=max(1, max_items),
    )


def apply_repair_action(
    action: RepairAction,
    *,
    item: StoryOutlineItem,
    content: SlideContent,
    constraints: ContentConstraints,
    ranking: list[LayoutCandidateScore],
    tried: set[str],
    issues: list[VisualIssue],
) -> SlideContent:
    if action == "fail":
        _fail(item.id, issues)
    if action == "tighter_truncate":
        drop_last = any((issue.slot or "").startswith("items") for issue in issues)
        next_constraints = scale_constraints(constraints, drop_last_item=drop_last)
        return constrain_slide_content(content, next_constraints)
    next_id = next(
        (
            candidate.layout_id
            for candidate in ranking
            if candidate.layout_id not in tried and candidate.layout_id != item.layout_id
        ),
        None,
    )
    if next_id is None:
        _fail(item.id, issues)
    item.layout_id = next_id
    return SlideContent(
        slide_id=content.slide_id,
        title=content.title,
        layout_id=next_id,
        slots=content.slots,
    )


def _fail(slide_id: str, issues: list[VisualIssue]) -> None:
    codes = ", ".join(issue.code for issue in issues) or "fail"
    raise SlideValidationFailed(
        f"Slide {slide_id!r} failed visual validation: {codes}"
    )
```

Avoid importing `SlideValidationFailed` from `orchestrator` if that creates a cycle (`orchestrator` will import dispatcher later). Move `SlideValidationFailed` to `apps/api/app/generation/stages/errors.py` **only if** a cycle appears. Prefer importing from `orchestrator` first; if `repair_dispatcher` → `orchestrator` → `repair_dispatcher`, extract:

```python
# apps/api/app/generation/stages/errors.py
class SlideValidationFailed(ValueError):
    pass
```

Then change `orchestrator.py` to `from .errors import SlideValidationFailed` and re-export it from `stages/__init__.py`. Keep the public name `SlideValidationFailed`.

If you extract, add a one-liner test import in `test_repair_dispatcher.py` that `from app.generation.stages import SlideValidationFailed` still works.

- [ ] **Step 4: Run tests**

```bash
uv run --project apps/api pytest apps/api/tests/test_repair_dispatcher.py apps/api/tests/test_staged_pipeline.py apps/api/tests/test_slide_validator.py apps/api/tests/test_slide_repairer.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/generation/stages/repair_dispatcher.py apps/api/tests/test_repair_dispatcher.py
# plus errors.py and orchestrator.py if extracted
git commit -m "$(cat <<'EOF'
feat: dispatch closed visual repair actions

EOF
)"
```

---

### Task 3: `LayoutSelector.rank`

**Files:**
- Modify: `apps/api/app/generation/stages/protocols.py`
- Modify: `apps/api/app/generation/stages/layout_selector.py` (`NativeLayoutSelector.rank`, `ThemeDispatchLayoutSelector.rank`)
- Modify: `apps/api/tests/test_staged_pipeline.py` (`FakeLayoutSelector.rank`)
- Test: `apps/api/tests/test_layout_selector_rank.py`

**Interfaces:**
- Produces: `rank(...) -> list[LayoutCandidateScore]` matching `PresentonLayoutSelector.rank`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_layout_selector_rank.py`:

```python
from app.generation.stages.layout_selector import (
    NativeLayoutSelector,
    PresentonLayoutSelector,
    ThemeDispatchLayoutSelector,
)
from app.generation.stages.models import StoryOutlineItem


def test_dispatch_rank_matches_presenton_top_layout() -> None:
    item = StoryOutlineItem(
        id="p1",
        title="Wasted hours",
        content="Teams lose time formatting slides.",
        role="problem",
    )
    presenton = PresentonLayoutSelector()
    dispatch = ThemeDispatchLayoutSelector()
    expected = presenton.rank(item, index=1, theme_id="modern:blue")
    got = dispatch.rank(item, index=1, theme_id="modern:blue")
    assert got[0].layout_id == expected[0].layout_id
    assert len(got) == len(expected)


def test_native_rank_is_single_select_result() -> None:
    item = StoryOutlineItem(id="c", title="Cover", content="", role="cover")
    selector = NativeLayoutSelector()
    ranked = selector.rank(item, index=0, theme_id="editorial-cobalt")
    assert len(ranked) == 1
    assert ranked[0].layout_id == selector.select(item, index=0, theme_id="editorial-cobalt")
```

Use the same `theme_id` string `PresentonLayoutSelector` tests use (`modern-blue` in `test_presenton_role_layout.py`). Match that exactly (`modern-blue`, not `modern:blue`) unless `parse_theme_ref` expects `template:scheme`. Check `apps/api/app/generation/themes.py` before writing the test; copy a theme id from `test_presenton_role_layout.py`.

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run --project apps/api pytest apps/api/tests/test_layout_selector_rank.py -v
```

Expected: FAIL `AttributeError: rank`

- [ ] **Step 3: Implement rank**

In `protocols.py`, add to `LayoutSelector` (same kwargs as `PresentonLayoutSelector.rank`):

```python
    def rank(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        assets: Mapping[tuple[int, str], str] | None = None,
        plan: SlidePlan | None = None,
    ) -> list[LayoutCandidateScore]:
        ...
```

This import of `LayoutCandidateScore` into `protocols.py` can stay as `from .layout_selector import LayoutCandidateScore` only if it does not cycle. If it does, move `LayoutCandidateScore` to `apps/api/app/generation/stages/layout_score.py`. Prefer defining `rank` on the concrete classes first and adding the protocol method after the dataclass is import-safe.

`NativeLayoutSelector.rank`:

```python
    def rank(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        assets: Mapping[tuple[int, str], str] | None = None,
        plan: SlidePlan | None = None,
    ) -> list[LayoutCandidateScore]:
        layout_id = self.select(item, index=index, theme_id=theme_id, assets=assets, plan=plan)
        return [LayoutCandidateScore(layout_id, 1.0, ("native-select",))]
```

`ThemeDispatchLayoutSelector.rank`:

```python
    def rank(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        assets: Mapping[tuple[int, str], str] | None = None,
        plan: SlidePlan | None = None,
    ) -> list[LayoutCandidateScore]:
        return self._delegate(theme_id).rank(
            item,
            index=index,
            theme_id=theme_id,
            assets=assets,
            plan=plan,
        )
```

Add `rank` to `FakeLayoutSelector` in `test_staged_pipeline.py`:

```python
    def rank(self, item, *, index, theme_id, assets=None, plan=None):
        layout_id = self.select(item, index=index, theme_id=theme_id, plan=plan)
        from app.generation.stages.layout_selector import LayoutCandidateScore
        return [LayoutCandidateScore(layout_id, 1.0, ("fake",))]
```

- [ ] **Step 4: Run tests**

```bash
uv run --project apps/api pytest apps/api/tests/test_layout_selector_rank.py apps/api/tests/test_presenton_role_layout.py apps/api/tests/test_staged_pipeline.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/generation/stages/protocols.py apps/api/app/generation/stages/layout_selector.py apps/api/tests/test_layout_selector_rank.py apps/api/tests/test_staged_pipeline.py
git commit -m "$(cat <<'EOF'
feat: expose layout ranking through the theme dispatcher

EOF
)"
```

---

### Task 4: `GenerationPipeline.accept_slide`

**Files:**
- Modify: `apps/api/app/generation/stages/orchestrator.py`
- Modify: `apps/api/app/generation/stages/__init__.py` (export new names if needed)
- Test: `apps/api/tests/test_accept_slide.py`

**Interfaces:**
- Consumes: Task 1 `VisualGate`, Task 2 dispatcher, Task 3 `rank`, `content_generator.render_slide`
- Produces: `accept_slide(...)`, `accept_document(...)`; `render()` calls `accept_document`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/test_accept_slide.py` with fakes. `CountingGate` returns truncated once then readable. `FakeRasterizer.rasterize` appends to `self.calls` and returns `b"\x89PNG\r\n\x1a\n" + b"x"`. `RecordingGenerator.render_slide` records `outline.items[index].layout_id` and returns a slide dict with that layout_id.

Required cases:

1. `visual_gate is None` → rasterizer never called, slide returned after geometry.
2. Truncated then readable → `rasterize` called twice, layout_id unchanged, body shorter.
3. Unreadable with two ranked layouts → `item.layout_id` becomes the second id.
4. Always unreadable + single layout → `SlideValidationFailed` after ranking exhausted (may happen on first repair). Cap: never more than `VISUAL_GATE_MAX_REPAIRS + 1` inspects.
5. Missing `SlideContent` for the slide id → skip gate (rasterize not called).

Sketch for skip-when-disabled:

```python
def test_accept_slide_skips_gate_when_unwired() -> None:
    rasterizer = FakeRasterizer()
    pipeline = GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=RecordingGenerator(),
        slide_validator=None,
        slide_rasterizer=rasterizer,
        visual_gate=None,
        layout_selector=RankingSelector(["grid", "list"]),
    )
    slide = {"id": "s1", "elements": []}
    outline = StoryOutline(items=[StoryOutlineItem(id="s1", title="T", content="B", layout_id="grid")])
    request = GenerationRequest(
        presentation_id=uuid4(),
        title="T",
        text="B",
        sections=[],
        language="en",
        slide_count=1,
    )
    contents = {
        "s1": SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "B"}),
    }
    out = pipeline.accept_slide(
        slide,
        request=request,
        outline=outline,
        index=0,
        assets={},
        contents=contents,
        plan=None,
    )
    assert out is slide
    assert rasterizer.calls == []
```

Copy `FakeStoryPlanner` / `GenerationRequest` imports from `test_staged_pipeline.py`. Implement `RankingSelector.select` as `rank(...)[0].layout_id` and `content_constraints` as `ContentConstraints(72, 240, 60, 180, 4)`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run --project apps/api pytest apps/api/tests/test_accept_slide.py -v
```

Expected: FAIL `TypeError: unexpected keyword slide_rasterizer` or `AttributeError: accept_slide`

- [ ] **Step 3: Implement accept_slide**

Extend `GenerationPipeline.__init__` with:

```python
        slide_rasterizer: SlideRasterizer | None = None,
        visual_gate: VisualGate | None = None,
        visual_gate_max_repairs: int = VISUAL_GATE_MAX_REPAIRS,
```

Assign `self.slide_rasterizer`, `self.visual_gate`, `self.visual_gate_max_repairs`.

Add `accept_slide` exactly as spec §7.1:

1. `slide = self.validate_slide(slide)`
2. If gate or rasterizer is None: return slide
3. If `contents.get(outline.items[index].id)` is None: return slide
4. `tried = {outline.items[index].layout_id or ""}`
5. Loop `attempt in range(self.visual_gate_max_repairs + 1)`:
   - `png = self.slide_rasterizer.rasterize(slide)` — wrap OSError/TimeoutExpired/CalledProcessError as `SlideValidationFailed` with `VISUAL_RASTERIZE_FAILED`
   - `result = self.visual_gate.inspect(png=png, slide=slide, content=content)`
   - if `result.readable`: return slide
   - if `attempt == self.visual_gate_max_repairs`: raise `SlideValidationFailed` with issue codes
   - `action = choose_repair_action(result.issues)`
   - `ranking = self.layout_selector.rank(...)` if selector is not None else `[]`
   - `content = apply_repair_action(...)`; `contents[item.id] = content`; `tried.add(item.layout_id or "")`
   - `slide = self.content_generator.render_slide(request, outline, index=index, assets=assets, contents=contents)`
   - `slide = self.validate_slide(slide)`

`accept_document` walks `document["slides"]` and writes back `accept_slide` results. Change `render()` to call `accept_document` instead of `validate_document` (pass `contents` as a **mutable** `dict`; if `contents` was a mapping, `dict(contents)` first).

Leave `validate_slide` / `validate_document` working for existing tests. `generate()` uses `render()`, so it picks up the gate automatically when injected.

If `layout_selector` is None during `next_ranked_layout`, treat ranking as empty → fail.

- [ ] **Step 4: Run tests**

```bash
uv run --project apps/api pytest apps/api/tests/test_accept_slide.py apps/api/tests/test_staged_pipeline.py -v
```

Expected: PASS. Existing generate tests still only geometry-validate.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/generation/stages/orchestrator.py apps/api/app/generation/stages/__init__.py apps/api/tests/test_accept_slide.py
git commit -m "$(cat <<'EOF'
feat: accept slides through the visual readability loop

EOF
)"
```

---

### Task 5: Settings and factory wiring

**Files:**
- Modify: `apps/api/app/config.py`
- Modify: `.env.example`
- Modify: `apps/api/app/generation/factory.py`
- Test: `apps/api/tests/test_visual_gate_factory.py`

**Interfaces:**
- Produces: settings fields; factory injects rasterizer+gate only for company-gateway + flag + model

- [ ] **Step 1: Write the failing tests**

```python
from app.generation import factory
from app.generation.provider import ProviderConfigurationError
from app.generation.stub_provider import StubPresentationProvider
import pytest


def test_factory_leaves_gate_off_by_default(monkeypatch) -> None:
    monkeypatch.setattr(factory, "_build_story_planner", lambda: StubPresentationProvider())
    pipeline = factory.build_story_provider()
    assert pipeline.visual_gate is None
    assert pipeline.slide_rasterizer is None


def test_factory_skips_gate_for_stub_even_when_flag_on(monkeypatch) -> None:
    settings = factory.get_settings()
    monkeypatch.setattr(settings, "visual_gate_enabled", True)
    monkeypatch.setattr(settings, "visual_gate_model", "ocr-vision")
    monkeypatch.setattr(settings, "generation_provider", "stub")
    monkeypatch.setattr(factory, "_build_story_planner", lambda: StubPresentationProvider())
    pipeline = factory.build_story_provider()
    assert pipeline.visual_gate is None


def test_factory_requires_model_when_gateway_flag_on(monkeypatch) -> None:
    monkeypatch.setattr(settings_module_or_get_settings, ...)
```

`get_settings` is `lru_cache`. Prefer monkeypatching `factory.get_settings` to return a simple namespace that includes **every** field `build_story_provider` / `_build_story_planner` reads (`generation_provider`, `visual_gate_enabled`, `visual_gate_model`, `visual_gate_max_repairs`, `visual_gate_rasterizer_cmd`, `visual_gate_save_screenshots`, `storage_root`, company gateway fields, `google_max_input_chars`, `company_gateway_chat_path`).

For the stub+flag case, `_build_story_planner` still returns stub; visual builder sees `generation_provider == "stub"` and returns `(None, None)`.

For company-gateway + flag + empty model: `_build_visual_stages` raises `ProviderConfigurationError` matching `SLIDEGEN_VISUAL_GATE_MODEL`.

For company-gateway + flag + model: monkeypatch `_build_story_planner` to a dummy object with `plan_deck`/`plan_slide`/`write_content_batch` **or** patch `_build_visual_stages` unit-style. Cleanest unit test: extract `_build_visual_stages(settings, story_planner_name)` and test that function with a namespace. Then `build_story_provider` just unpacks it.

Do not construct a real `CompanyGatewayOcrVisualGate` until Task 7. In this task, if the model is set, inject **fakes are wrong for factory**. Factory should import the real classes; Task 7 can add the class as a stub:

In Task 5, inject `CliSlideRasterizer` (Task 8) is also missing. To keep this task independently testable:

- Task 5 factory assigns `pipeline.visual_gate` / `slide_rasterizer` only when `_build_visual_stages` returns them.
- Implement `_build_visual_stages` returning `(None, None)` always except when enabled+gateway+model, in which it instantiates placeholder classes defined in `visual_gate.py` / `slide_rasterizer.py` **in this task as empty named classes**, replaced in Tasks 7–8.

Minimal placeholders so factory tests can `assert pipeline.visual_gate.name == "company-gateway-ocr"`:

```python
# at bottom of visual_gate.py until Task 7 fills inspect()
class CompanyGatewayOcrVisualGate:
    name = "company-gateway-ocr"
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
    def inspect(self, *, png, slide, content):
        raise RuntimeError("OCR visual gate is not implemented")
```

```python
# slide_rasterizer.py placeholder until Task 8
class CliSlideRasterizer:
    name = "cli"
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
    def rasterize(self, slide):
        raise RuntimeError("CLI rasterizer is not implemented")
```

Factory tests assert types/names, not `inspect()`.

- [ ] **Step 2: Run tests to fail**

```bash
uv run --project apps/api pytest apps/api/tests/test_visual_gate_factory.py -v
```

- [ ] **Step 3: Add settings + factory**

`config.py` (inside `Settings`, `env_prefix=SLIDEGEN_` already applies):

```python
    visual_gate_enabled: bool = False
    visual_gate_model: str | None = None
    visual_gate_max_repairs: int = Field(default=2, ge=0, le=4)
    visual_gate_rasterizer_cmd: str = "node packages/slide-rasterizer/dist/cli.js"
    visual_gate_save_screenshots: bool = False
```

`.env.example`:

```
SLIDEGEN_VISUAL_GATE_ENABLED=false
SLIDEGEN_VISUAL_GATE_MODEL=
SLIDEGEN_VISUAL_GATE_MAX_REPAIRS=2
SLIDEGEN_VISUAL_GATE_RASTERIZER_CMD=node packages/slide-rasterizer/dist/cli.js
SLIDEGEN_VISUAL_GATE_SAVE_SCREENSHOTS=false
```

`factory.py` `_build_visual_stages()` as spec §3.2 / §8. Pass `visual_gate_max_repairs` into `GenerationPipeline`.

- [ ] **Step 4: Run tests**

```bash
uv run --project apps/api pytest apps/api/tests/test_visual_gate_factory.py apps/api/tests/test_asset_planning.py -v
```

Expected: PASS. Default factory still no-ops assets and gate.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/config.py .env.example apps/api/app/generation/factory.py apps/api/app/generation/stages/visual_gate.py apps/api/app/generation/stages/slide_rasterizer.py apps/api/tests/test_visual_gate_factory.py
git commit -m "$(cat <<'EOF'
feat: wire an optional visual readability gate behind a flag

EOF
)"
```

---

### Task 6: Worker uses `accept_slide`

**Files:**
- Modify: `apps/api/app/generation/worker.py`
- Test: `apps/api/tests/test_generation_worker_stream.py` (assert compile closure still works)
- Add: `apps/api/tests/test_worker_accept_slide.py` if the existing worker tests cannot see the hook

**Interfaces:**
- Consumes: `GenerationPipeline.accept_slide`
- Streamer signature **unchanged**. Put accept inside the worker `compile_slide` closure. Batch path `_render_slide_by_slide` calls `accept_slide` instead of `validate_slide`.

- [ ] **Step 1: Write a failing test**

In a new test file or existing worker test, build a `GenerationWorker` with a pipeline whose `accept_slide` appends to a list. Drive `_render_slide_by_slide` with `FakeGenerator.render_slides` returning one slide.

If `_render_slide_by_slide` is awkward to call, test via a pipeline spy:

```python
class SpyPipeline:
    def __init__(self, inner):
        self.inner = inner
        self.accepted = []
    def __getattr__(self, name):
        return getattr(self.inner, name)
    def accept_slide(self, slide, **kwargs):
        self.accepted.append(slide)
        return self.inner.accept_slide(slide, **kwargs)
```

Simplest reliable test: unit-test the worker method by constructing `GenerationWorker` like `test_generation_worker_stream.py` and calling `_render_slide_by_slide`. Assert `pipeline.accept_slide` was used by replacing it:

```python
calls = []
def accept_slide(slide, **kwargs):
    calls.append(slide)
    return slide
worker.pipeline.accept_slide = accept_slide  # type: ignore
```

After one render, `len(calls) == 1`.

Add a second test that the stream compile closure calls `accept_slide`: monkeypatch `IncrementalSlideStreamer` is heavier. Instead, read `_write_or_stream_content` and change `compile_slide` to call `accept_slide`. Test by instantiating worker with `streaming_enabled=True` only if existing tests already cover compile. **Minimum:** batch path test above. Then grep worker for `validate_slide` — the only remaining production call should be inside `accept_slide`.

- [ ] **Step 2: Run test to fail**

Expected: `calls == []` because worker still uses `validate_slide`.

- [ ] **Step 3: Wire worker**

`_render_slide_by_slide`: add `deck_plan: DeckPlan | None = None`. Replace `validate_slide` with:

```python
            plan = None
            if deck_plan is not None:
                plans = {entry.id: entry for entry in deck_plan.slides}
                plan = plans.get(outline.items[index].id)
            slide = self.pipeline.accept_slide(
                slide,
                request=request,
                outline=outline,
                index=index,
                assets=assets,
                contents=contents,
                plan=plan,
            )
```

Pass `deck_plan` from `process_once`.

Stream `compile_slide` closure:

```python
            def compile_slide(index: int, written: dict[str, SlideContent]) -> dict[str, object]:
                contents.update(written)
                slide = self.pipeline.content_generator.render_slide(
                    request,
                    outline,
                    index=index,
                    assets=assets,
                    contents=written,
                )
                plan = None
                if deck_plan is not None:
                    plans = {entry.id: entry for entry in deck_plan.slides}
                    plan = plans.get(outline.items[index].id)
                return self.pipeline.accept_slide(
                    slide,
                    request=request,
                    outline=outline,
                    index=index,
                    assets=assets,
                    contents=contents,
                    plan=plan,
                )
```

Keep `validate_slide=lambda slide: slide` on the streamer **or** `validate_slide=self.pipeline.validate_slide` (geometry only; accept already ran). Prefer **identity** to avoid a second geometry pass fighting a visual recompile. Update existing streamer tests that pass `validate_slide=lambda slide: slide` — no change required.

- [ ] **Step 4: Run tests**

```bash
uv run --project apps/api pytest apps/api/tests/test_generation_worker_stream.py apps/api/tests/test_worker_accept_slide.py apps/api/tests/test_accept_slide.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/generation/worker.py apps/api/tests/test_worker_accept_slide.py apps/api/tests/test_generation_worker_stream.py
git commit -m "$(cat <<'EOF'
feat: run visual acceptance on compiled generation slides

EOF
)"
```

---

### Task 7: Company gateway OCR gate

**Files:**
- Modify: `apps/api/app/generation/stages/visual_gate.py` (replace placeholder `inspect`)
- Test: `apps/api/tests/test_company_gateway_visual_gate.py`

**Interfaces:**
- Consumes: same gateway URL/key/chat_path; `SLIDEGEN_VISUAL_GATE_MODEL`; Task 1 `classify_extracted_text`
- Produces: `CompanyGatewayOcrVisualGate.inspect`

- [ ] **Step 1: Write the failing tests**

Reuse `FakeClient` / `FakeResponse` pattern from `test_company_gateway_provider.py`.

```python
def test_ocr_gate_sends_image_url_and_classifies(monkeypatch) -> None:
    client = FakeClient({"extracted_text": "Quarterly Review Visible body copy.", "unreadable": False, "notes": ""})
    gate = CompanyGatewayOcrVisualGate(
        base_url="http://127.0.0.1:5000",
        api_key="secret",
        model="ocr-vision",
        chat_path="/v1/chat/completions",
        client=client,
    )
    content = SlideContent(
        slide_id="s1",
        title="Quarterly Review",
        layout_id="list",
        slots={"body": "Visible body copy."},
    )
    result = gate.inspect(png=b"\x89PNG\r\n\x1a\n", slide={"id": "s1"}, content=content)
    assert result.readable
    payload = client.calls[0]["json"]
    assert payload["model"] == "ocr-vision"
    assert payload["temperature"] == 0
    user = payload["messages"][1]["content"]
    assert any(part.get("type") == "image_url" for part in user)


def test_ocr_gate_invalid_json_raises_slide_validation_failed() -> None:
    ...
```

For invalid JSON: FakeClient returns `{"choices":[{"message":{"content":"not-json"}}]}`. `inspect` must raise `SlideValidationFailed` matching `VISUAL_GATE_UNAVAILABLE` (map `ProviderResponseError`).

Retry: first response status 503, second 200 — copy `_is_retryable_status` logic; one retry then success. If that requires a richer fake, a `SequenceClient` with two responses is enough.

- [ ] **Step 2: Run tests to fail**

Expected: placeholder `RuntimeError: OCR visual gate is not implemented`

- [ ] **Step 3: Implement inspect**

Pydantic models in `visual_gate.py`:

```python
class _OcrResponse(BaseModel):
    extracted_text: str = ""
    unreadable: bool = False
    notes: str = ""
```

POST JSON:

```python
{
    "model": self.model,
    "messages": [
        {"role": "system", "content": "Return only JSON. Extract visible slide text in reading order. Do not suggest layouts or repairs."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt + "\n" + llm_json_schema(_OcrResponse)},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode("ascii")}},
            ],
        },
    ],
    "temperature": 0,
    "max_tokens": 2048,
}
```

Parse with the same `_json_object` / `model_validate_json` approach as `CompanyGatewayProvider` (copy the small helpers; do not add methods onto `CompanyGatewayProvider`). Retry once on 429/5xx. On failure raise `SlideValidationFailed(f"Slide failed visual validation: VISUAL_GATE_UNAVAILABLE")`.

Call `classify_extracted_text(extracted=parsed.extracted_text, unreadable=parsed.unreadable, content=content)`.

Do not send `slide` JSON to the model.

- [ ] **Step 4: Run tests**

```bash
uv run --project apps/api pytest apps/api/tests/test_company_gateway_visual_gate.py apps/api/tests/test_visual_gate.py apps/api/tests/test_visual_gate_factory.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/generation/stages/visual_gate.py apps/api/tests/test_company_gateway_visual_gate.py
git commit -m "$(cat <<'EOF'
feat: inspect slide screenshots through gateway OCR

EOF
)"
```

---

### Task 8: CLI rasterizer subprocess

**Files:**
- Modify: `apps/api/app/generation/stages/slide_rasterizer.py`
- Test: `apps/api/tests/test_slide_rasterizer.py`

**Interfaces:**
- Produces: `CliSlideRasterizer.rasterize(slide) -> png bytes`

- [ ] **Step 1: Write the failing tests**

Use a tiny stand-in command that writes a PNG. From the test, create a Python script path is fragile on Windows; write a **PNG file in a temp dir** and use a command the OS has:

On Windows/Linux, `python` writing the file:

The rasterizer should run `command --slide <in> --out <out>`. Test injects:

```python
cmd = f'{sys.executable} -c "import sys,pathlib; src=pathlib.Path(sys.argv[sys.argv.index(\"--out\")+1]); src.write_bytes(b\"\\x89PNG\\r\\n\\x1a\\n\" + b\"ok\")"'
```

That quoting is painful. Prefer a helper script committed as `apps/api/tests/fixtures/fake_rasterize.py`:

```python
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--slide")
parser.add_argument("--out")
args = parser.parse_args()
Path(args.out).write_bytes(b"\x89PNG\r\n\x1a\n" + Path(args.slide).read_bytes()[:8])
```

Test:

```python
def test_cli_rasterizer_returns_png(tmp_path, monkeypatch) -> None:
    rasterizer = CliSlideRasterizer(
        command=f"{sys.executable} apps/api/tests/fixtures/fake_rasterize.py",
        repo_root=Path(__file__).resolve().parents[3],
        timeout_seconds=10,
    )
    png = rasterizer.rasterize({"id": "s1", "background": "#fff", "elements": []})
    assert png.startswith(b"\x89PNG")


def test_cli_rasterizer_non_png_fails() -> None:
    # command that writes "nope"
    with pytest.raises(SlideValidationFailed, match="VISUAL_RASTERIZE_FAILED"):
        ...
```

- [ ] **Step 2: Run tests to fail**

Expected: placeholder RuntimeError

- [ ] **Step 3: Implement CliSlideRasterizer**

```python
class SlideRasterizer(Protocol):
    name: str
    def rasterize(self, slide: dict[str, object]) -> bytes: ...


class CliSlideRasterizer:
    name = "cli"

    def __init__(
        self,
        *,
        command: str,
        repo_root: Path,
        timeout_seconds: float = 30,
    ) -> None:
        self.command = command
        self.repo_root = repo_root
        self.timeout_seconds = timeout_seconds

    def rasterize(self, slide: dict[str, object]) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            slide_path = Path(tmp) / "slide.json"
            out_path = Path(tmp) / "slide.png"
            slide_path.write_text(json.dumps(slide), encoding="utf-8")
            argv = [*shlex.split(self.command, posix=os.name != "nt"), "--slide", str(slide_path), "--out", str(out_path)]
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
            return data
```

On Windows, `shlex.split(..., posix=False)` keeps `node` and the script path intact.

Resolve `repo_root` in factory by walking parents from `__file__` until `packages/slide-rasterizer` exists (the folder may be added in Task 9; until then, tests pass `repo_root` explicitly). Factory can use `Path(__file__).resolve().parents[3]` only if that is the repo root (`apps/api/app/generation/factory.py` → parents[0]=generation, [1]=app, [2]=api, [3]=repo). Confirm with `parents[3]` == repo containing `packages/`.

- [ ] **Step 4: Run tests**

```bash
uv run --project apps/api pytest apps/api/tests/test_slide_rasterizer.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/generation/stages/slide_rasterizer.py apps/api/tests/test_slide_rasterizer.py apps/api/tests/fixtures/fake_rasterize.py
git commit -m "$(cat <<'EOF'
feat: rasterize slides through a Node CLI subprocess

EOF
)"
```

---

### Task 9: Konva Playwright rasterizer package

**Files:**
- Create: `packages/slide-rasterizer/package.json`
- Create: `packages/slide-rasterizer/tsconfig.json`
- Create: `packages/slide-rasterizer/vite.config.ts`
- Create: `packages/slide-rasterizer/index.html`
- Create: `packages/slide-rasterizer/src/main.tsx`
- Create: `packages/slide-rasterizer/src/cli.ts`
- Create: `packages/slide-rasterizer/tests/cli.test.ts` (skip without Chromium)
- Modify: root workspace already includes `packages/*`

**Interfaces:**
- Consumes: `@gapo-slidegen/slide-editor/canvas`, `@gapo-slidegen/slide-schema`
- Produces: `node packages/slide-rasterizer/dist/cli.js --slide x.json --out x.png`

- [ ] **Step 1: Scaffold package.json**

```json
{
  "name": "@gapo-slidegen/slide-rasterizer",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "bin": "./dist/cli.js",
  "scripts": {
    "build": "vite build",
    "test": "vitest run",
    "typecheck": "tsc -p tsconfig.json"
  },
  "dependencies": {
    "@gapo-slidegen/slide-editor": "0.1.0",
    "@gapo-slidegen/slide-schema": "0.1.0",
    "konva": "10.3.0",
    "playwright": "1.50.0",
    "react": "19.2.8",
    "react-dom": "19.2.8",
    "react-konva": "19.2.5"
  },
  "devDependencies": {
    "@types/node": "26.2.0",
    "@types/react": "19.2.18",
    "@types/react-dom": "19.2.4",
    "@vitejs/plugin-react": "5.2.0",
    "typescript": "7.0.2",
    "vite": "7.1.0"
  }
}
```

Pin `vite` to a current 7.x already compatible with `@vitejs/plugin-react` in `apps/web` if 7.1.0 is not in the lockfile — use the same plugin major as `apps/web` (`^5.2.0` resolved). After `npm install` at repo root, do not float versions.

`tsconfig.json`: copy `packages/slide-editor/tsconfig.json` and add `"types": ["node"]`.

- [ ] **Step 2: Render page**

`index.html`:

```html
<!doctype html>
<html>
  <body style="margin:0">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`src/main.tsx`:

```tsx
import { createRoot } from "react-dom/client";
import { SlideCanvas } from "@gapo-slidegen/slide-editor/canvas";
import { EDITOR_STAGE_HEIGHT, EDITOR_STAGE_WIDTH, type Slide } from "@gapo-slidegen/slide-schema";

const root = document.getElementById("root");
if (!root) throw new Error("missing root");
root.style.width = `${EDITOR_STAGE_WIDTH}px`;
root.style.height = `${EDITOR_STAGE_HEIGHT}px`;
root.style.overflow = "hidden";

const slide = JSON.parse(document.documentElement.dataset.slide ?? "{}") as Slide;
createRoot(root).render(
  <SlideCanvas
    elements={slide.elements ?? []}
    background={slide.background ?? "#FFFFFF"}
    selectedElementId={null}
    onSelectElement={() => undefined}
    onChangeElement={() => undefined}
    readOnly
  />,
);
```

CLI writes `dataset.slide` by serving a temp copy of `index.html` **or** (simpler) `page.addInitScript` / `page.goto` then `page.evaluate`. Prefer Playwright `page.goto(fileUrl)` of the Vite `preview`/`build` output and:

```ts
await page.evaluate((slide) => {
  document.documentElement.dataset.slide = JSON.stringify(slide);
}, slide);
```

That is too late if `main.tsx` already ran. **Do this instead:** CLI reads `--slide`, writes `dist/input.json`, and `main.tsx` fetches `./input.json` **or** CLI inlines JSON into a temp HTML. Simplest robust path:

CLI uses Playwright `page.setContent` is bad for module imports. Use `vite preview` or `file://` on `dist/index.html` plus query string:

`main.tsx`:

```tsx
const params = new URLSearchParams(location.search);
const encoded = params.get("slide");
if (!encoded) throw new Error("missing slide");
const slide = JSON.parse(decodeURIComponent(encoded)) as Slide;
```

Large decks may exceed URL limits. **Use a temp file served next to dist:**

CLI copies PNG-bound `slide.json` to `dist/slide.json` then `goto dist/index.html` with `main.tsx` doing `const slide = await fetch("./slide.json").then(r => r.json())` and rendering after fetch. Wait for `canvas` then screenshot.

`src/cli.ts`:

- parse `--slide` `--out`
- `npm run build` is a separate step; CLI assumes `dist/` exists
- `chromium.launch()`
- `page.setViewportSize({ width: 1280, height: 720 })`
- copy input JSON to `dist/slide.json`
- `page.goto(pathToFileURL(dist/index.html).href)`
- `await page.waitForSelector("canvas")`
- `await page.locator("canvas").first().screenshot({ path: out, type: "png" })`
- assert png size: `imagesize` optional; Python tests already check PNG magic. Add a Node assertion reading file length > 100.

Viewport must be 1280×720; host div is 1280px so Konva `scale === 1`.

- [ ] **Step 3: Vite config**

Build both the page and the CLI. Two builds is OK:

- `vite.config.ts` `build.outDir = dist/page`, rollup input `index.html`
- CLI compiled with `tsc` to `dist/cli.js` **or** a second vite `ssr: false` lib build with `target: node`

Minimal: `vite build` for the browser page; `npx esbuild src/cli.ts --platform=node --bundle --outfile=dist/cli.js --format=esm --packages=external` if esbuild is not a dep, use `tsc` with `"outDir": "dist"` for `cli.ts` only and keep page in `dist/`.

Practical split:

- `vite build` → `dist/index.html` + assets
- `"build:cli": "tsc -p tsconfig.cli.json"` emitting `dist/cli.js`

`tsconfig.cli.json`: `module: NodeNext`, `outDir: dist`, `include: ["src/cli.ts"]`.

`cli.ts` locates `dist/index.html` via `import.meta.url`.

- [ ] **Step 4: Optional Chromium test**

```ts
import { existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { describe, it, expect } from "vitest";

const hasChromium = process.env.SLIDEGEN_VISUAL_GATE_CHROMIUM !== "0";

describe.skipIf(!hasChromium)("rasterize cli", () => {
  it("writes a 1280 png", () => {
    // write fixture slide json from packages/slide-schema fixtures
    // execFileSync(process.execPath, [cli, "--slide", ..., "--out", ...])
    expect(existsSync(out)).toBe(true);
  });
});
```

Default CI: set nothing; if Playwright browsers are missing, skip (catch spawn error and `it.skip`). **Never fail `npm test` on machines without Chromium.**

```ts
try {
  execFileSync(...)
} catch (error) {
  if (String(error).includes("Executable doesn't exist")) return;
  throw error;
}
```

- [ ] **Step 5: Install, build, typecheck**

From repo root:

```bash
npm install
npm run build --workspace @gapo-slidegen/slide-rasterizer
npm run typecheck --workspace @gapo-slidegen/slide-rasterizer
```

Fix export issues (`SlideCanvas` is a client component; rasterizer is a Vite app, not Next — `"use client"` is ignored). If Konva needs `global.window`, Playwright provides it.

- [ ] **Step 6: Point factory command at the built CLI** (already the default settings string). Manually run once:

```bash
node packages/slide-rasterizer/dist/cli.js --slide packages/slide-rasterizer/fixtures/slide.json --out /tmp/slide.png
```

On Windows use `%TEMP%\slide.png`. Commit a tiny `fixtures/slide.json` copied from `canonicalPresentationFixture.slides[0]` in `packages/slide-schema/src/fixtures.ts`.

- [ ] **Step 7: Commit**

```bash
git add packages/slide-rasterizer package-lock.json
git commit -m "$(cat <<'EOF'
feat: rasterize canonical slides with Konva and Playwright

EOF
)"
```

---

### Task 10: Docs

**Files:**
- Modify: `docs/generation-pipeline-architecture.md`
- Modify: `docs/decisions/m1-generation-pipeline-stages.md`
- Modify: `docs/superpowers/plans/README.md`
- Modify: `docs/superpowers/specs/2026-08-20-visual-readability-gate-design.md` (status → approved)

- [ ] **Step 1: Update pipeline architecture**

In the worker-stages mermaid, after Validate:

```
Validate["8. Validate + repair geometry"] --> Visual["8b. Visual gate (optional)
screenshot + OCR, off by default"]
Visual --> Save["9. Save presentation"]
```

Document: flag off keeps `N + 4` text LLM. Flag on adds `N` vision (worst case `3N`). Rasterizer is Node CLI, not an LLM.

Replace “There is no screenshot or VLM critic” with a pointer to the spec and this plan. Keep the `futask/` sentence.

- [ ] **Step 2: Update ADR open questions**

Replace the VLM critic bullet with: visual readability gate is specified in `docs/superpowers/specs/2026-08-20-visual-readability-gate-design.md`; default off; not an aesthetic VLM.

- [ ] **Step 3: README for plans**

Add a bullet linking this plan.

- [ ] **Step 4: Mark spec status `approved 2026-08-20`**

- [ ] **Step 5: Run the default API suite**

```bash
uv run --project apps/api pytest apps/api/tests -q
```

Expected: PASS without Chromium.

- [ ] **Step 6: Commit**

```bash
git add docs/generation-pipeline-architecture.md docs/decisions/m1-generation-pipeline-stages.md docs/superpowers/plans/README.md docs/superpowers/specs/2026-08-20-visual-readability-gate-design.md
git commit -m "$(cat <<'EOF'
docs: describe the optional visual readability gate

EOF
)"
```

---

## Self-review

**Spec coverage**

| Spec section | Task |
|---|---|
| Rasterizer PNG 1280×720 Konva | 8, 9 |
| VisualGate OCR codes | 1, 7 |
| Repair catalog | 2, 4 |
| `LayoutSelector.rank` | 3 |
| `accept_slide` loop + max 2 repairs | 4 |
| Factory flag / stub skip / model required | 5 |
| Worker + stream compile | 6 |
| Fail closed rasterize/OCR | 7, 8 |
| VLM later / drop unknown codes | 1 (closed literal), 2 (no prose) |
| Docs / call counts | 10 |
| No new layouts / no validator code changes | global constraints |

**Placeholders:** none remaining in tasks. Task 5 uses short-lived placeholder classes that Tasks 7–8 replace.

**Types:** `VisualIssueCode`, `RepairAction`, `SlideRasterizer.rasterize`, `VisualGate.inspect`, `accept_slide` kwargs match the spec.
