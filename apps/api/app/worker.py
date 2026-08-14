from .config import get_settings
from .database import SessionLocal
from .generation.stub_provider import StubPresentationProvider
from .generation.worker import GenerationWorker


def build_provider():
    provider_name = get_settings().generation_provider
    if provider_name == "stub":
        return StubPresentationProvider()
    raise RuntimeError(
        f"Generation provider {provider_name!r} is not configured. "
        "Keep SLIDEGEN_GENERATION_PROVIDER=stub until the gateway adapter is available."
    )


def main() -> None:
    worker = GenerationWorker(SessionLocal, build_provider())
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
