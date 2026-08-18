import logging

from .database import SessionLocal
from .generation.factory import build_story_provider
from .generation.worker import GenerationWorker


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    worker = GenerationWorker(SessionLocal, build_story_provider())
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
