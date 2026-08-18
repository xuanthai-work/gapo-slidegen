from uuid import uuid4

from .provider import (
    GenerationRequest,
    OutlineRequest,
    ProviderConfigurationError,
    RewriteRequest,
    RewriteTextItem,
    SlideRewriteRequest,
)
from .stages.content_generator import build_content_generator
from .stages.native_content_generator import _automatic_slide_count, _chunks
from .stages.orchestrator import GenerationPipeline, NullAssetGenerator, NullAssetPlanner


class StubPresentationProvider:
    """Deterministic local provider and backward-compatible facade.

    The actual rendering logic now lives in the generation pipeline's
    ContentGenerator stages. This class keeps the original public interface so
    existing tests and the factory can use it unchanged.
    """

    name = "stub"

    def rewrite_text(self, request: RewriteRequest) -> str:
        raise ProviderConfigurationError(
            "AI rewrite is unavailable with the local stub provider. Configure an AI provider first."
        )

    def rewrite_slide(self, request: SlideRewriteRequest) -> list[RewriteTextItem]:
        raise ProviderConfigurationError(
            "AI rewrite is unavailable with the local stub provider. Configure an AI provider first."
        )

    def generate_outline(
        self,
        request: OutlineRequest,
        understanding: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        del understanding
        slide_count = request.slide_count or _automatic_slide_count(request.text)
        content_count = max(0, slide_count - 1)
        section_texts = [
            str(section.get("text", "")).strip() for section in request.sections if section.get("text")
        ]
        bodies = section_texts[:content_count]
        if len(bodies) < content_count:
            bodies.extend(_chunks(request.text, content_count - len(bodies)))
        items: list[dict[str, object]] = [
            {"id": str(uuid4()), "title": request.title, "content": ""}
        ]
        for index, body in enumerate(bodies, start=1):
            section = request.sections[index - 1] if index - 1 < len(request.sections) else {}
            items.append(
                {
                    "id": str(uuid4()),
                    "title": str(section.get("title") or f"Key point {index}"),
                    "content": body,
                }
            )
        return items

    def generate(self, request: GenerationRequest) -> dict[str, object]:
        pipeline = GenerationPipeline(
            story_planner=self,
            content_generator=build_content_generator(request.theme_id),
            asset_planner=NullAssetPlanner(),
            asset_generator=NullAssetGenerator(),
        )
        return pipeline.generate(request)
