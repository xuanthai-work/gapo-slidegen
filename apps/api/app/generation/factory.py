from ..config import get_settings
from .company_gateway_provider import CompanyGatewayProvider
from .gemini_provider import GoogleAIStudioProvider
from .gemini_image_provider import GoogleAIStudioImageProvider
from .provider import ProviderConfigurationError
from .stub_provider import StubPresentationProvider


def build_provider():
    settings = get_settings()
    provider_name = settings.generation_provider.strip().lower()
    if provider_name == "stub":
        return StubPresentationProvider()
    if provider_name in {"google-ai-studio", "gemini"}:
        api_key = settings.google_api_key.get_secret_value().strip() if settings.google_api_key else ""
        model = settings.google_model.strip() if settings.google_model else ""
        missing = [
            name
            for name, value in (
                ("SLIDEGEN_GOOGLE_API_KEY", api_key),
                ("SLIDEGEN_GOOGLE_MODEL", model),
            )
            if not value
        ]
        if missing:
            raise ProviderConfigurationError(
                "Google AI Studio provider is missing: " + ", ".join(missing)
            )
        return GoogleAIStudioProvider(
            api_key=api_key,
            model=model,
            max_input_chars=settings.google_max_input_chars,
        )
    if provider_name == "company-gateway":
        api_key = (
            settings.company_gateway_api_key.get_secret_value().strip()
            if settings.company_gateway_api_key
            else ""
        )
        base_url = (settings.company_gateway_url or "").strip()
        model = (settings.company_gateway_model or "").strip()
        missing = [
            name
            for name, value in (
                ("SLIDEGEN_COMPANY_GATEWAY_URL", base_url),
                ("SLIDEGEN_COMPANY_GATEWAY_API_KEY", api_key),
                ("SLIDEGEN_COMPANY_GATEWAY_MODEL", model),
            )
            if not value
        ]
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
        "Use 'stub', 'google-ai-studio', or 'company-gateway'."
    )


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
        missing = [
            name
            for name, value in (
                ("SLIDEGEN_GOOGLE_API_KEY", api_key),
                ("SLIDEGEN_GOOGLE_IMAGE_MODEL", model),
            )
            if not value
        ]
        if missing:
            raise ProviderConfigurationError(
                "Google AI Studio image provider is missing: " + ", ".join(missing)
            )
        return GoogleAIStudioImageProvider(api_key=api_key, model=model)
    raise ProviderConfigurationError(
        f"Image provider {provider_name!r} is not configured. "
        "Use 'disabled' or 'google-ai-studio'."
    )
