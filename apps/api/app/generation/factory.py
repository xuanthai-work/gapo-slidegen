from ..config import get_settings
from .company_gateway_provider import CompanyGatewayProvider
from .gemini_image_provider import GoogleAIStudioImageProvider
from .provider import ProviderConfigurationError
from .stages.asset_planner import StubAssetPlanner
from .stages.content_generator import ThemeDispatchContentGenerator
from .stages.content_understanding import build_content_understanding
from .stages.orchestrator import GenerationPipeline, NullAssetGenerator
from .stub_provider import StubPresentationProvider


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


def build_story_provider() -> GenerationPipeline:
    """Build the full generation pipeline used by the worker."""
    story_planner = _build_story_planner()
    return GenerationPipeline(
        story_planner=story_planner,
        content_generator=ThemeDispatchContentGenerator(),
        content_understanding=build_content_understanding(story_planner),
        asset_planner=StubAssetPlanner(),
        asset_generator=NullAssetGenerator(),
    )


# Backward-compatible alias used by older callers; prefer build_story_provider.
build_provider = build_story_provider


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
    settings = get_settings()
    provider_name = settings.image_provider.strip().lower()
    if provider_name in {"", "disabled", "none"}:
        raise ProviderConfigurationError(
            "Image generation is not configured. Set SLIDEGEN_IMAGE_PROVIDER and an image model."
        )
    if provider_name in {"google-ai-studio", "gemini"}:
        api_key = settings.google_api_key.get_secret_value().strip() if settings.google_api_key else ""
        model = settings.google_image_model.strip() if settings.google_image_model else ""
        missing = _missing_settings(
            ("SLIDEGEN_GOOGLE_API_KEY", api_key),
            ("SLIDEGEN_GOOGLE_IMAGE_MODEL", model),
        )
        if missing:
            raise ProviderConfigurationError(
                "Google AI Studio image provider is missing: " + ", ".join(missing)
            )
        return GoogleAIStudioImageProvider(api_key=api_key, model=model)
    raise ProviderConfigurationError(
        f"Image provider {provider_name!r} is not configured. "
        "Use 'disabled' or 'google-ai-studio'."
    )
