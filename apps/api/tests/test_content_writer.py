from uuid import uuid4

from app.generation.layouts import ContentConstraints
from app.generation.models import SlideContent
from app.generation.provider import GenerationRequest, ProviderResponseError
from app.generation.stages.content_writer import OutlineContentWriter, ProviderContentWriter
from app.generation.stages.deck_planner import OutlineDeckPlanner
from app.generation.stages.models import StoryOutline, StoryOutlineItem


def test_outline_content_writer_fills_named_slots_within_layout_constraints() -> None:
    writer = OutlineContentWriter()
    item = StoryOutlineItem(
        id="comparison",
        title="A title that must be shortened for the selected layout",
        content="A summary that is too long for the selected layout and must be shortened.",
        blocks=[
            {"heading": "First heading is too long", "body": "First body is also too long"},
            {"heading": "Second heading", "body": "Second body"},
            {"heading": "Third heading", "body": "Third body"},
        ],
    )
    constraints = ContentConstraints(
        title_max_chars=24,
        content_max_chars=32,
        block_heading_max_chars=16,
        block_body_max_chars=18,
        max_items=2,
    )

    content = writer.write(
        item,
        layout_id="comparison-2col",
        constraints=constraints,
    )

    assert content.layout_id == "comparison-2col"
    assert len(content.title) <= 24
    assert len(content.slots["body"]) <= 32
    assert len(content.slots["items"]) == 2
    assert all(
        len(block["heading"]) <= 16 and len(block["body"]) <= 18
        for block in content.slots["items"]
    )


def test_outline_content_writer_preserves_metric_slots() -> None:
    writer = OutlineContentWriter()
    item = StoryOutlineItem(
        id="metrics",
        title="Results",
        content="The launch improved core metrics.",
        blocks=[
            {
                "heading": "Adoption",
                "body": "More teams activated",
                "label": "Weekly users",
                "value": "+42%",
            }
        ],
    )

    content = writer.write(
        item,
        layout_id="highlight-metrics",
        constraints=ContentConstraints(80, 180, 55, 120, 4),
    )

    assert content.slots["items"] == [
        {
            "heading": "Adoption",
            "body": "More teams activated",
            "label": "Weekly users",
            "value": "+42%",
        }
    ]


class OversizedBatchProvider:
    def write_content_batch(self, **kwargs):
        outline = kwargs["outline"]
        return {
            item.id: SlideContent(
                slide_id=item.id,
                layout_id=item.layout_id or "",
                title="Generated title that is much too long",
                slots={
                    "body": "Generated body that is much too long for this layout",
                    "items": [
                        {
                            "heading": "Generated heading that is too long",
                            "body": "Generated item body that is too long",
                            "label": "",
                            "value": "",
                        }
                    ],
                },
            )
            for item in outline.items
        }


class FailingBatchProvider:
    def write_content_batch(self, **kwargs):
        del kwargs
        raise ProviderResponseError("invalid content")


def _batch_context():
    item = StoryOutlineItem(
        id="detail",
        title="Reviewed title",
        content="Reviewed body",
        layout_id="layout",
        blocks=[{"heading": "Reviewed heading", "body": "Reviewed item"}],
    )
    outline = StoryOutline(items=[item])
    request = GenerationRequest(
        presentation_id=uuid4(),
        title="Deck",
        text="Source",
        sections=[],
        language="en",
        slide_count=1,
    )
    return outline, OutlineDeckPlanner().plan(request, outline)


def test_provider_content_writer_enforces_constraints_on_generated_copy() -> None:
    outline, deck = _batch_context()
    writer = ProviderContentWriter(
        OversizedBatchProvider(),
        fallback=OutlineContentWriter(),
    )
    constraints = {"detail": ContentConstraints(18, 22, 16, 18, 1)}

    contents = writer.write_batch(
        outline=outline,
        deck_plan=deck,
        constraints=constraints,
        language="en",
    )

    assert contents["detail"].title.startswith("Generated")
    assert len(contents["detail"].title) <= 18
    assert len(contents["detail"].slots["body"]) <= 22
    assert len(contents["detail"].slots["items"][0]["heading"]) <= 16


def test_provider_content_writer_falls_back_to_reviewed_copy() -> None:
    outline, deck = _batch_context()
    writer = ProviderContentWriter(
        FailingBatchProvider(),
        fallback=OutlineContentWriter(),
    )

    contents = writer.write_batch(
        outline=outline,
        deck_plan=deck,
        constraints={"detail": ContentConstraints(80, 180, 55, 120, 1)},
        language="en",
    )

    assert contents["detail"].title == "Reviewed title"
    assert contents["detail"].slots["body"] == "Reviewed body"
