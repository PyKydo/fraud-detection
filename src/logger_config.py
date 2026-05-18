import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "pipeline.log"

_FORMAT = "%(asctime)s [%(levelname)s] %(funcName)s: %(message)s"

_configured = False


def setup_logging(name: str | None = None) -> logging.Logger:
    global _configured

    if not _configured:
        logging.basicConfig(
            level=logging.INFO,
            format=_FORMAT,
            handlers=[
                logging.FileHandler(LOG_FILE, encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )
        _configured = True

    return logging.getLogger(name)
