import logging
from pathlib import Path

from ..config import get_settings
from .company_gateway_provider import CompanyGatewayProvider
from .provider import ProviderConfigurationError
from .checkpoint_repository import GenerationCheckpointRepository
from .checkpoints import GenerationCheckpointService
from .event_factory import build_generation_event_publisher
from .stages.content_generator import ThemeDispatchContentGenerator
from .stages.content_understanding import build_content_understanding
from .stages.content_writer import OutlineContentWriter, ProviderContentWriter
from .stages.deck_planner import OutlineDeckPlanner, ProviderDeckPlanner
from .stages.layout_selector import ThemeDispatchLayoutSelector
from .stages.orchestrator import GenerationPipeline, NullAssetGenerator, NullAssetPlanner
from .stages.slide_rasterizer import CliSlideRasterizer
from .stages.slide_repairer import DeterministicSlideRepairer
from .stages.slide_validator import RuleBasedSlideValidator
from .stages.slide_planner import OutlineSlidePlanner, ProviderSlidePlanner
from .stages.visual_gate import CompanyGatewayOcrVisualGate
from .stub_provider import StubPresentationProvider

logger = logging.getLogger(__name__)


def _resolve_repo_root() -> Path:
    """Locate the monorepo root (contains packages/slide-rasterizer when built)."""
    start = Path(__file__).resolve().parent
    for parent in (start, *start.parents):
        if (parent / "packages" / "slide-rasterizer").is_dir():
            return parent
    return Path(__file__).resolve().parents[3]


# Legacy Gemini provider is kept as a disabled fallback. To re-enable, import
# GoogleAIStudioProvider from .gemini_provider and add the branch below.
# from .gemini_provider import GoogleAIStudioProvider


def _missing_settings(*items: tuple[str, str]) -> list[str]:
    return [name for name, value in items if not value]


def _build_story_planner():
    settings = get_settings()
    provider_name = settings.generation_provider.strip().lower()
    if provider_name == "stub":
        return StubPresentationProvider()
    if provider_name == "company-gateway":
        api_key = (
            settings.company_gateway_api_key.get_secret_value().strip()
            if settings.company_gateway_api_key
            else ""
        )
        base_url = (settings.company_gateway_url or "").strip()
        model = (settings.company_gateway_model or "").strip()
        missing = _missing_settings(
            ("SLIDEGEN_COMPANY_GATEWAY_URL", base_url),
            ("SLIDEGEN_COMPANY_GATEWAY_API_KEY", api_key),
            ("SLIDEGEN_COMPANY_GATEWAY_MODEL", model),
        )
        if missing:
            raise ProviderConfigurationError(
                "Company gateway provider is missing: " + ", ".join(missing)
            )
        return CompanyGatewayProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            chat_path=settings.company_gateway_chat_path,
            max_input_chars=settings.google_max_input_chars,
        )
    raise ProviderConfigurationError(
        f"Generation provider {provider_name!r} is not configured. "
        "Use 'stub' or 'company-gateway'."
    )


def _build_visual_stages(settings, story_planner_name: str):
    """Return (slide_rasterizer, visual_gate) per enable rules in spec §3.2."""
    if not settings.visual_gate_enabled:
        return None, None

    provider_name = settings.generation_provider.strip().lower()
    if provider_name == "stub":
        logger.warning(
            "Visual gate is enabled but generation_provider is stub; "
            "leaving visual gate disabled (story planner=%s)",
            story_planner_name,
        )
        return None, None

    if provider_name != "company-gateway":
        return None, None

    model = (settings.visual_gate_model or "").strip()
    if not model:
        raise ProviderConfigurationError(
            "Visual gate is enabled but SLIDEGEN_VISUAL_GATE_MODEL is missing"
        )

    api_key = (
        settings.company_gateway_api_key.get_secret_value().strip()
        if settings.company_gateway_api_key
        else ""
    )
    rasterizer = CliSlideRasterizer(
        command=settings.visual_gate_rasterizer_cmd,
        repo_root=_resolve_repo_root(),
        save_screenshots=settings.visual_gate_save_screenshots,
        storage_root=settings.storage_root,
    )
    gate = CompanyGatewayOcrVisualGate(
        base_url=(settings.company_gateway_url or "").strip(),
        api_key=api_key,
        model=model,
        chat_path=settings.company_gateway_chat_path,
    )
    return rasterizer, gate


def build_story_provider() -> GenerationPipeline:
    """Build the full generation pipeline used by the worker."""
    settings = get_settings()
    story_planner = _build_story_planner()
    outline_deck_planner = OutlineDeckPlanner()
    outline_slide_planner = OutlineSlidePlanner()
    outline_content_writer = OutlineContentWriter()
    if hasattr(story_planner, "plan_deck") and hasattr(story_planner, "plan_slide"):
        deck_planner = ProviderDeckPlanner(
            story_planner,
            fallback=outline_deck_planner,
        )
        slide_planner = ProviderSlidePlanner(
            story_planner,
            fallback=outline_slide_planner,
        )
    else:
        deck_planner = outline_deck_planner
        slide_planner = outline_slide_planner
    content_writer = (
        ProviderContentWriter(
            story_planner,
            fallback=outline_content_writer,
        )
        if hasattr(story_planner, "write_content_batch")
        else outline_content_writer
    )
    slide_rasterizer, visual_gate = _build_visual_stages(settings, story_planner.name)
    return GenerationPipeline(
        story_planner=story_planner,
        content_generator=ThemeDispatchContentGenerator(),
        content_understanding=build_content_understanding(story_planner),
        deck_planner=deck_planner,
        slide_planner=slide_planner,
        layout_selector=ThemeDispatchLayoutSelector(),
        content_writer=content_writer,
        slide_validator=RuleBasedSlideValidator(),
        slide_repairer=DeterministicSlideRepairer(),
        asset_planner=NullAssetPlanner(),
        asset_generator=NullAssetGenerator(),
        slide_rasterizer=slide_rasterizer,
        visual_gate=visual_gate,
        visual_gate_max_repairs=settings.visual_gate_max_repairs,
    )


# Backward-compatible alias used by older callers; prefer build_story_provider.
build_provider = build_story_provider


class SessionCheckpointAdapter:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def record_event(self, event, *, validated_canonical_slide=None):
        with self.session_factory() as session:
            recorded = GenerationCheckpointService(
                GenerationCheckpointRepository(session)
            ).record_event(
                event,
                validated_canonical_slide=validated_canonical_slide,
            )
            session.commit()
            return recorded


def build_generation_worker(session_factory):
    """Build the worker. Streaming stays off until SLIDEGEN_GENERATION_STREAMING_ENABLED=true."""
    from .worker import GenerationWorker

    settings = get_settings()
    publisher = None
    if settings.generation_streaming_enabled:
        try:
            publisher = build_generation_event_publisher(settings)
        except Exception as error:
            logger.warning("generation Redis publisher unavailable: %s", error)
    return GenerationWorker(
        session_factory,
        build_story_provider(),
        event_publisher=publisher,
        checkpoint_service=SessionCheckpointAdapter(session_factory),
        streaming_enabled=settings.generation_streaming_enabled,
    )


def build_rewrite_provider():
    """Return a provider that implements rewrite operations.

    The stub provider intentionally does not support rewriting.
    """
    planner = _build_story_planner()
    if not hasattr(planner, "rewrite_text"):
        raise ProviderConfigurationError(
            "The configured generation provider does not support text rewriting."
        )
    return planner


def build_image_provider():
    raise ProviderConfigurationError(
        "Text-to-image generation has been disabled."
    )
