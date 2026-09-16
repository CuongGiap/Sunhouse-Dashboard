from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class GoogleSheetError(Exception):
    pass


def parse_spreadsheet_id(sheet_input: str) -> str:
    text = (sheet_input or "").strip()
    if not text:
        raise GoogleSheetError("Spreadsheet ID hoặc URL đang trống.")

    url_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", text)
    if url_match:
        return url_match.group(1)

    id_match = re.fullmatch(r"[a-zA-Z0-9-_]{20,}", text)
    if id_match:
        return text

    raise GoogleSheetError("Không parse được Spreadsheet ID từ input đã nhập.")


def load_oauth_credentials(client_secret_file: str, token_file: str) -> Credentials:
    client_secret_path = Path(client_secret_file)
    token_path = Path(token_file)

    if not client_secret_path.exists():
        raise GoogleSheetError(
            f"Không tìm thấy file OAuth client secret: {client_secret_path}"
        )

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def load_service_account_credentials(
    service_account_file: str,
    service_account_json: str,
) -> ServiceAccountCredentials:
    raw_json = (service_account_json or "").strip()
    if raw_json:
        try:
            service_info = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise GoogleSheetError(
                "GOOGLE_SERVICE_ACCOUNT_JSON không phải JSON hợp lệ."
            ) from exc

        private_key = service_info.get("private_key")
        if isinstance(private_key, str):
            service_info["private_key"] = private_key.replace("\\n", "\n")

        return ServiceAccountCredentials.from_service_account_info(
            service_info,
            scopes=SCOPES,
        )

    service_account_path = Path(service_account_file)
    if not service_account_path.exists():
        raise GoogleSheetError(
            "Không tìm thấy service account credentials. "
            "Hãy cấu hình GOOGLE_SERVICE_ACCOUNT_FILE hoặc GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    return ServiceAccountCredentials.from_service_account_file(
        str(service_account_path),
        scopes=SCOPES,
    )


def _values_to_dataframe(values: list[list[Any]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()

    headers = [str(c).strip() if c is not None else "" for c in values[0]]
    if not any(headers):
        headers = [f"col_{i+1}" for i in range(len(values[0]))]

    rows = values[1:] if len(values) > 1 else []
    max_row_len = max((len(row) for row in rows), default=0)
    target_len = max(len(headers), max_row_len)

    # Some tabs have merged headers or sparse header rows. Expand header names
    # so every row can be normalized to the same width.
    if len(headers) < target_len:
        headers = headers + [f"col_{i+1}" for i in range(len(headers), target_len)]

    normalized_rows: list[list[Any]] = []
    for row in rows:
        row_values = list(row)
        if len(row_values) < target_len:
            row_values = row_values + [None] * (target_len - len(row_values))
        elif len(row_values) > target_len:
            row_values = row_values[:target_len]
        normalized_rows.append(row_values)

    return pd.DataFrame(normalized_rows, columns=headers)


def fetch_spreadsheet_data(
    sheet_input: str,
    client_secret_file: str,
    token_file: str,
    auth_mode: str = "oauth",
    service_account_file: str = "",
    service_account_json: str = "",
) -> tuple[dict[str, pd.DataFrame], str]:
    spreadsheet_id = parse_spreadsheet_id(sheet_input)
    normalized_mode = (auth_mode or "oauth").strip().lower()

    if normalized_mode == "service_account":
        creds = load_service_account_credentials(
            service_account_file=service_account_file,
            service_account_json=service_account_json,
        )
    else:
        creds = load_oauth_credentials(client_secret_file, token_file)

    service = build("sheets", "v4", credentials=creds)
    metadata = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id)
        .execute()
    )

    sheets = metadata.get("sheets", [])
    title_by_sheet = [s.get("properties", {}).get("title", "Unnamed") for s in sheets]

    data: dict[str, pd.DataFrame] = {}
    for title in title_by_sheet:
        resp = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"'{title}'")
            .execute()
        )
        values = resp.get("values", [])
        data[title] = _values_to_dataframe(values)

    return data, spreadsheet_id
