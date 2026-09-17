from __future__ import annotations

from collections.abc import Mapping
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _read_streamlit_secret(key: str) -> str:
    try:
        import streamlit as st

        value = st.secrets.get(key)
        if value is None:
            return ""

        if isinstance(value, Mapping):
            return json.dumps(value)

        if isinstance(value, list):
            return json.dumps(value)

        return str(value)
    except Exception:
        return ""


def _read_setting(key: str, default: str) -> str:
    env_value = os.getenv(key)
    if env_value is not None and env_value != "":
        return env_value

    secret_value = _read_streamlit_secret(key)
    if secret_value != "":
        return secret_value

    return default


def _resolve_path(path_value: str) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str((BASE_DIR / path).resolve())


@dataclass(frozen=True)
class AppSettings:
    app_access_token: str = _read_setting("APP_ACCESS_TOKEN", "")
    google_auth_mode: str = _read_setting("GOOGLE_AUTH_MODE", "oauth").strip().lower()
    client_secret_file: str = _resolve_path(
        _read_setting("GOOGLE_CLIENT_SECRET_FILE", "credentials.json")
    )
    token_file: str = _resolve_path(_read_setting("GOOGLE_TOKEN_FILE", "token.json"))
    service_account_file: str = _resolve_path(
        _read_setting("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")
    )
    service_account_json: str = _read_setting("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    spreadsheet_default: str = _read_setting("GOOGLE_SPREADSHEET", "")
    cache_ttl_seconds: int = int(_read_setting("CACHE_TTL_SECONDS", "300"))


SETTINGS = AppSettings()
