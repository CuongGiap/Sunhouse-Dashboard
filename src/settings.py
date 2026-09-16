from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_path(path_value: str) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str((BASE_DIR / path).resolve())


@dataclass(frozen=True)
class AppSettings:
    client_secret_file: str = _resolve_path(
        os.getenv("GOOGLE_CLIENT_SECRET_FILE", "credentials.json")
    )
    token_file: str = _resolve_path(os.getenv("GOOGLE_TOKEN_FILE", "token.json"))
    spreadsheet_default: str = os.getenv("GOOGLE_SPREADSHEET", "")
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))


SETTINGS = AppSettings()
