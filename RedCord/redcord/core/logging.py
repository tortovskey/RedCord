from pathlib import Path

from loguru import logger

from redcord.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(settings.log_dir / "redcord.log", rotation="5 MB", retention=10, level="INFO")
    logger.add(lambda msg: print(msg, end=""), level="INFO")
