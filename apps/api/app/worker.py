from .database import SessionLocal
from .generation.factory import build_provider
from .generation.worker import GenerationWorker


def main() -> None:
    worker = GenerationWorker(SessionLocal, build_provider())
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
