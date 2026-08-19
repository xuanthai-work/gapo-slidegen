import logging

from .database import SessionLocal
from .generation.factory import build_generation_worker


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    worker = build_generation_worker(SessionLocal)
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
