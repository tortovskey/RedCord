from __future__ import annotations

from pathlib import Path

from redcord.app.config import get_settings


def app_dir() -> Path:
    return get_settings().app_dir


def data_dir() -> Path:
    path = get_settings().data_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def commits_dir() -> Path:
    path = get_settings().commit_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def assets_dir() -> Path:
    return get_settings().assets_dir
