from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.google_sheets import GoogleSheetError, fetch_spreadsheet_data
from src.settings import SETTINGS

st.set_page_config(page_title="Google Sheets Dashboard", layout="wide")

st.title("Google Sheets Dashboard")
st.caption("Đọc dữ liệu đa tab và hiển thị tổng quan theo thời gian thực")

if "tabs_data" not in st.session_state:
    st.session_state.tabs_data = None
if "spreadsheet_id" not in st.session_state:
    st.session_state.spreadsheet_id = None
if "loaded_at" not in st.session_state:
    st.session_state.loaded_at = None

with st.sidebar:
    st.header("Cấu hình")
    sheet_input = st.text_input(
        "Spreadsheet URL / ID",
        value=SETTINGS.spreadsheet_default,
        help="Dán URL đầy đủ hoặc chỉ ID của Google Sheet",
    )
    st.write(f"OAuth secret: {SETTINGS.client_secret_file}")
    st.write(f"OAuth token: {SETTINGS.token_file}")
    st.write(f"Auth mode: {SETTINGS.google_auth_mode}")
    if SETTINGS.google_auth_mode == "service_account":
        st.write(f"Service account file: {SETTINGS.service_account_file}")
    st.write(f"Cache TTL: {SETTINGS.cache_ttl_seconds}s")


@st.cache_data(ttl=SETTINGS.cache_ttl_seconds)
def load_data(sheet_source: str) -> tuple[dict[str, pd.DataFrame], str]:
    return fetch_spreadsheet_data(
        sheet_input=sheet_source,
        client_secret_file=SETTINGS.client_secret_file,
        token_file=SETTINGS.token_file,
        auth_mode=SETTINGS.google_auth_mode,
        service_account_file=SETTINGS.service_account_file,
        service_account_json=SETTINGS.service_account_json,
    )


def _filter_dataframe(source_df: pd.DataFrame) -> pd.DataFrame:
    if source_df.empty:
        return source_df

    all_columns = list(source_df.columns)
    default_columns = all_columns[: min(8, len(all_columns))]
    selected_columns = st.multiselect(
        "Chọn cột cần xem",
        options=all_columns,
        default=default_columns,
        help="Để trống để hiển thị tất cả cột.",
    )

    displayed_df = source_df if not selected_columns else source_df[selected_columns]

    search_keyword = st.text_input(
        "Tìm nhanh trong bảng",
        value="",
        placeholder="Nhập từ khóa để lọc theo toàn bộ cột đang hiển thị",
    ).strip()

    if search_keyword:
        mask = displayed_df.astype(str).apply(
            lambda col: col.str.contains(search_keyword, case=False, na=False)
        )
        displayed_df = displayed_df[mask.any(axis=1)]

    return displayed_df


def render_dashboard(tabs_data: dict[str, pd.DataFrame], spreadsheet_id: str) -> None:
    total_tabs = len(tabs_data)
    total_rows = sum(len(df) for df in tabs_data.values())
    total_columns = sum(len(df.columns) for df in tabs_data.values())

    c1, c2, c3 = st.columns(3)
    c1.metric("Số tab", total_tabs)
    c2.metric("Tổng số dòng", f"{total_rows:,}")
    c3.metric("Tổng số cột", f"{total_columns:,}")

    if st.session_state.loaded_at:
        st.caption(
            f"Lần tải gần nhất: {st.session_state.loaded_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    st.markdown(
        f"**Spreadsheet ID:** `{spreadsheet_id}`  \\\n"
        "Nếu đã đăng nhập OAuth thành công, token sẽ được lưu local để tái sử dụng."
    )

    stats = pd.DataFrame(
        [
            {
                "Tab": name,
                "Số dòng": len(df),
                "Số cột": len(df.columns),
                "Ô trống": int(df.isna().sum().sum()) if not df.empty else 0,
            }
            for name, df in tabs_data.items()
        ]
    )

    st.subheader("Thống kê theo tab")
    if not stats.empty:
        chart = px.bar(
            stats,
            x="Tab",
            y="Số dòng",
            color="Số cột",
            title="Số dòng dữ liệu theo từng tab",
        )
        st.plotly_chart(chart, use_container_width=True)
        st.dataframe(stats, use_container_width=True)
    else:
        st.info("Google Sheet không có dữ liệu để hiển thị.")

    st.subheader("Xem dữ liệu chi tiết")
    selected_sheet = st.selectbox("Chọn tab", list(tabs_data.keys()))
    selected_df = tabs_data[selected_sheet]

    filtered_df = _filter_dataframe(selected_df)

    c4, c5 = st.columns(2)
    c4.metric("Số dòng", len(filtered_df))
    c5.metric("Số cột", len(filtered_df.columns))

    st.dataframe(filtered_df, use_container_width=True, height=500)


col_load, col_refresh = st.columns([2, 1])
load_button = col_load.button("Kết nối và tải dữ liệu", type="primary")
refresh_button = col_refresh.button("Tải lại (bỏ cache)")


if load_button or refresh_button:
    try:
        if refresh_button:
            load_data.clear()

        with st.spinner("Đang kết nối Google Sheets và tải dữ liệu..."):
            data, spreadsheet_id = load_data(sheet_input)

        if not data:
            st.warning("Không tìm thấy tab nào trong file Google Sheet.")
        else:
            st.session_state.tabs_data = data
            st.session_state.spreadsheet_id = spreadsheet_id
            st.session_state.loaded_at = datetime.now()
            st.success("Tải dữ liệu thành công.")

    except GoogleSheetError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.exception(exc)

if st.session_state.tabs_data and st.session_state.spreadsheet_id:
    render_dashboard(st.session_state.tabs_data, st.session_state.spreadsheet_id)
else:
    st.info(
        "Nhấn **Kết nối và tải dữ liệu** để bắt đầu. "
        "Lần đầu sẽ mở trình duyệt để bạn đăng nhập Google OAuth."
    )
