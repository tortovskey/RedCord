from pathlib import Path

from redcord.core.config import get_settings


def ensure_runtime_dirs() -> None:
    s = get_settings()
    Path(s.app_data_dir).mkdir(parents=True, exist_ok=True)
    Path(s.backup_dir).mkdir(parents=True, exist_ok=True)
    Path(s.log_dir).mkdir(parents=True, exist_ok=True)
