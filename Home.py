from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import unicodedata

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
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False


def _require_app_access() -> None:
    expected_token = (SETTINGS.app_access_token or "").strip()
    if not expected_token:
        st.session_state.auth_ok = True
        return

    if st.session_state.auth_ok:
        return

    st.warning("Ứng dụng yêu cầu mã truy cập.")
    with st.form("app-access-form", clear_on_submit=True):
        input_token = st.text_input("Mã truy cập", type="password")
        submitted = st.form_submit_button("Đăng nhập")

    if submitted:
        if input_token == expected_token:
            st.session_state.auth_ok = True
            st.rerun()
        else:
            st.error("Mã truy cập không đúng.")

    st.stop()


_require_app_access()

with st.sidebar:
    st.header("Cấu hình")
    if SETTINGS.app_access_token.strip():
        if st.button("Đăng xuất", type="secondary"):
            st.session_state.auth_ok = False
            st.session_state.tabs_data = None
            st.session_state.spreadsheet_id = None
            st.session_state.loaded_at = None
            st.rerun()

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

if SETTINGS.google_auth_mode == "service_account":
    has_inline_secret = bool(SETTINGS.service_account_json.strip())
    has_secret_file = Path(SETTINGS.service_account_file).exists()
    if not has_inline_secret and not has_secret_file:
        st.warning(
            "Chưa có thông tin Service Account. "
            "Hãy cấu hình GOOGLE_SERVICE_ACCOUNT_JSON trong Secrets trên Streamlit Cloud."
        )


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


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def _find_reason_column(df: pd.DataFrame) -> str | None:
    normalized_map = {col: _normalize_text(col) for col in df.columns}

    for col, normalized in normalized_map.items():
        if "ly do" in normalized:
            return col

    for col, normalized in normalized_map.items():
        if "loi" in normalized and "do" in normalized:
            return col

    return None


def _extract_month_label(series: pd.Series) -> pd.Series:
    raw = series.fillna("").astype(str).str.strip()

    yymmdd_prefix = raw.str.extract(r"^(\d{6})", expand=False)
    month_from_code = pd.to_datetime(yymmdd_prefix, format="%y%m%d", errors="coerce")

    yyyymmdd_prefix = raw.str.extract(r"^(\d{8})", expand=False)
    month_from_yyyymmdd = pd.to_datetime(
        yyyymmdd_prefix, format="%Y%m%d", errors="coerce"
    )

    ddmm = raw.str.extract(r"^(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?")
    if not ddmm.empty:
        day = ddmm[0].str.zfill(2)
        month = ddmm[1].str.zfill(2)
        year = ddmm[2].fillna(str(datetime.now().year))
        year = year.map(lambda y: f"20{y}" if len(y) == 2 else y)
        parsed_ddmm = pd.to_datetime(
            day + "/" + month + "/" + year,
            format="%d/%m/%Y",
            errors="coerce",
        )
    else:
        parsed_ddmm = pd.Series(pd.NaT, index=raw.index)

    yyyymmdd_with_sep = raw.str.extract(
        r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})", expand=True
    )
    if not yyyymmdd_with_sep.empty:
        parsed_yyyymmdd_sep = pd.to_datetime(
            yyyymmdd_with_sep[0]
            + "-"
            + yyyymmdd_with_sep[1].str.zfill(2)
            + "-"
            + yyyymmdd_with_sep[2].str.zfill(2),
            format="%Y-%m-%d",
            errors="coerce",
        )
    else:
        parsed_yyyymmdd_sep = pd.Series(pd.NaT, index=raw.index)

    generic_parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)

    month_value = month_from_code
    month_value = month_value.fillna(month_from_yyyymmdd)
    month_value = month_value.fillna(parsed_ddmm)
    month_value = month_value.fillna(parsed_yyyymmdd_sep)
    month_value = month_value.fillna(generic_parsed)
    return month_value.dt.strftime("%m/%Y")


def _find_msp_column(df: pd.DataFrame) -> str | None:
    normalized_map = {col: _normalize_text(col) for col in df.columns}

    for col, normalized in normalized_map.items():
        if normalized == "msp" or normalized.startswith("msp"):
            return col

    for col, normalized in normalized_map.items():
        if "msp" in normalized:
            return col

    return None


def _time_parse_success_rate(series: pd.Series) -> float:
    labels = _extract_month_label(series)
    if len(labels) == 0:
        return 0.0
    return float(labels.notna().mean())


def _guess_time_column(df: pd.DataFrame) -> str | None:
    if df.empty or len(df.columns) == 0:
        return None

    scored: list[tuple[str, float]] = []
    for col in df.columns:
        score = _time_parse_success_rate(df[col])
        normalized = _normalize_text(col)
        if "ngay" in normalized or "date" in normalized or "thang" in normalized:
            score += 0.02
        elif "msp" in normalized:
            score += 0.01
        scored.append((col, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    best_col, best_score = scored[0]
    if best_score <= 0.01:
        return None

    return best_col


def _render_time_summary_for_sheet(
    source_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    sheet_name: str,
    time_col: str,
) -> None:
    st.subheader("Tổng hợp theo thời gian - sheet đang chọn")

    if source_df.empty or len(source_df.columns) == 0:
        st.info("Sheet đang chọn không có dữ liệu.")
        return

    if filtered_df.empty:
        st.info("Không có dữ liệu sau khi filter để tổng hợp theo thời gian.")
        return

    if time_col not in source_df.columns:
        st.warning("Không tìm thấy cột thời gian trong sheet đang chọn.")
        return

    selected_rows = source_df.loc[filtered_df.index].copy()
    time_label = _extract_month_label(selected_rows[time_col])

    if time_label.notna().sum() == 0:
        fallback_col = _guess_time_column(selected_rows)
        if fallback_col and fallback_col != time_col:
            fallback_label = _extract_month_label(selected_rows[fallback_col])
            if fallback_label.notna().sum() > 0:
                st.info(
                    f"Không tách được thời gian từ cột '{time_col}'. "
                    f"Đang dùng tự động cột '{fallback_col}'."
                )
                time_col = fallback_col
                time_label = fallback_label

    summary = (
        pd.DataFrame({"Thời gian": time_label})
        .dropna(subset=["Thời gian"])
        .groupby("Thời gian", as_index=False)
        .size()
        .rename(columns={"size": "Số lượng"})
    )

    if summary.empty:
        st.info(
            "Không tách được thời gian từ cột đã chọn của sheet. "
            "Định dạng hỗ trợ: yymmdd... hoặc dd/mm."
        )
        return

    summary["_sort_date"] = pd.to_datetime(
        "01/" + summary["Thời gian"], format="%d/%m/%Y", errors="coerce"
    )
    summary = summary.sort_values("_sort_date").drop(columns=["_sort_date"])

    st.caption(f"Sheet: {sheet_name} | Cột thời gian: {time_col}")
    st.markdown("**Bảng 2 cột: Thời gian và Số lượng**")
    st.dataframe(summary, width="stretch")

    chart = px.line(
        summary,
        x="Thời gian",
        y="Số lượng",
        markers=True,
        title="Xu hướng số lượng theo thời gian (toàn bộ sheet)",
    )
    st.plotly_chart(chart, width="stretch")


def _render_time_summary_for_all_sheets(
    tabs_data: dict[str, pd.DataFrame],
    preferred_time_col: str,
) -> None:
    if not tabs_data:
        st.info("Chưa có dữ liệu để tổng hợp.")
        return

    parts: list[pd.DataFrame] = []
    for sheet_name, df in tabs_data.items():
        if df.empty or len(df.columns) == 0:
            continue

        col_for_time = None
        if preferred_time_col in df.columns and _time_parse_success_rate(df[preferred_time_col]) > 0:
            col_for_time = preferred_time_col
        else:
            col_for_time = _guess_time_column(df)
        if col_for_time is None:
            continue

        part = pd.DataFrame({"Thời gian": _extract_month_label(df[col_for_time])})
        part = part.dropna(subset=["Thời gian"]).copy()
        if not part.empty:
            parts.append(part)

    if not parts:
        st.info(
            "Không tách được thời gian từ các cột dữ liệu ở các sheet. "
            "Định dạng hỗ trợ: yymmdd... hoặc dd/mm."
        )
        return

    summary = (
        pd.concat(parts, ignore_index=True)
        .groupby("Thời gian", as_index=False)
        .size()
        .rename(columns={"size": "Số lượng"})
    )
    summary["_sort_date"] = pd.to_datetime(
        "01/" + summary["Thời gian"], format="%d/%m/%Y", errors="coerce"
    )
    summary = summary.sort_values("_sort_date").drop(columns=["_sort_date"])

    st.caption("Phạm vi: Tất cả sheet")
    st.markdown("**Bảng 2 cột: Thời gian và Số lượng**")
    st.dataframe(summary, width="stretch")

    chart = px.line(
        summary,
        x="Thời gian",
        y="Số lượng",
        markers=True,
        title="Xu hướng số lượng theo thời gian (tất cả sheet)",
    )
    st.plotly_chart(chart, width="stretch")


def _render_doi_shopee_summary(
    df: pd.DataFrame,
    selected_sheet: str,
    time_col: str,
) -> None:
    if "doi shopee" not in _normalize_text(selected_sheet):
        return

    st.subheader("Phân tích lỗi theo tháng - ĐỔI SHOPEE")

    if df.empty:
        st.info("Tab ĐỔI SHOPEE đang trống dữ liệu.")
        return

    reason_col = _find_reason_column(df)
    if reason_col is None:
        st.warning("Không tìm thấy cột Lý do trong tab ĐỔI SHOPEE.")
        return

    if time_col not in df.columns:
        st.warning("Không tìm thấy cột thời gian trong tab ĐỔI SHOPEE.")
        return

    effective_time_col = time_col
    if _time_parse_success_rate(df[effective_time_col]) == 0:
        fallback_col = _guess_time_column(df)
        if fallback_col and fallback_col != effective_time_col:
            effective_time_col = fallback_col
            st.info(
                f"Không tách được thời gian từ cột '{time_col}'. "
                f"Đang dùng tự động cột '{effective_time_col}' cho phần ĐỔI SHOPEE."
            )

    working = df.copy()
    working["_reason_raw"] = working[reason_col].fillna("").astype(str)

    keyword_map = {
        "Lỗi": ["loi"],
        "Linh kiện": ["linh kien"],
        "Bù": ["bu"],
    }

    selected_groups = st.multiselect(
        "Lọc theo nhóm Lý do",
        options=list(keyword_map.keys()),
        default=list(keyword_map.keys()),
        key="doi_shopee_reason_groups",
    )

    if not selected_groups:
        st.info("Hãy chọn ít nhất một nhóm Lý do để phân tích.")
        return

    reason_search = st.text_input(
        "Tìm trong cột Lý do (ví dụ: lỗi, linh kiện, bù)",
        value="",
        key="doi_shopee_reason_search",
    ).strip()

    def map_reason_group(text: str) -> str | None:
        normalized = _normalize_text(text)
        for group_name in selected_groups:
            keywords = keyword_map[group_name]
            if any(keyword in normalized for keyword in keywords):
                return group_name
        return None

    working["_reason_group"] = working["_reason_raw"].map(map_reason_group)
    working = working[working["_reason_group"].notna()].copy()

    if reason_search:
        normalized_search = _normalize_text(reason_search)
        working = working[
            working["_reason_raw"]
            .astype(str)
            .map(_normalize_text)
            .str.contains(re.escape(normalized_search), na=False)
        ].copy()

    if working.empty:
        st.info("Không có dữ liệu khớp với các nhóm Lý do đã chọn.")
        return

    working["Tháng"] = _extract_month_label(working[effective_time_col])
    working = working[working["Tháng"].notna()].copy()

    if working.empty:
        st.warning(
            "Không tách được tháng từ cột đã chọn. "
            "Hỗ trợ định dạng 6 số đầu kiểu yymmdd (260901...) hoặc ngày dd/mm."
        )
        return

    month_options = sorted(working["Tháng"].dropna().unique().tolist())
    selected_months = st.multiselect(
        "Lọc theo tháng (tách từ cột A)",
        options=month_options,
        default=month_options,
        key="doi_shopee_month_filter",
    )

    if not selected_months:
        st.info("Hãy chọn ít nhất một tháng để xem tổng hợp.")
        return

    working = working[working["Tháng"].isin(selected_months)].copy()

    if working.empty:
        st.info("Không có dữ liệu sau khi lọc theo tháng.")
        return

    monthly = (
        working.groupby(["Tháng", "_reason_group"], as_index=False)
        .size()
        .rename(columns={"_reason_group": "Nhóm lý do", "size": "Số lượng"})
        .sort_values(["Tháng", "Nhóm lý do"])
    )

    monthly["Tỷ lệ (%)"] = (
        monthly["Số lượng"]
        / monthly.groupby("Tháng")["Số lượng"].transform("sum")
        * 100
    ).round(2)

    c1, c2 = st.columns(2)
    c1.metric("Số bản ghi khớp", len(working))
    c2.metric("Số tháng", monthly["Tháng"].nunique())

    chart = px.bar(
        monthly,
        x="Tháng",
        y="Số lượng",
        color="Nhóm lý do",
        barmode="group",
        title="Tổng hợp Lý do theo tháng (ĐỔI SHOPEE)",
    )
    st.plotly_chart(chart, width="stretch")
    st.dataframe(monthly, width="stretch")

    st.markdown("**Tổng hợp theo tháng (đủ số lượng và tỷ lệ)**")
    pivot_counts = (
        monthly.pivot(index="Tháng", columns="Nhóm lý do", values="Số lượng")
        .fillna(0)
        .astype(int)
    )
    pivot_counts["Tổng"] = pivot_counts.sum(axis=1)
    st.dataframe(pivot_counts, width="stretch")


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
        st.plotly_chart(chart, width="stretch")
        st.dataframe(stats, width="stretch")
    else:
        st.info("Google Sheet không có dữ liệu để hiển thị.")

    st.subheader("Xem dữ liệu chi tiết")
    selected_sheet = st.selectbox("Chọn tab", list(tabs_data.keys()))
    selected_df = tabs_data[selected_sheet]

    guessed_time_col = _guess_time_column(selected_df)
    time_col_options = list(selected_df.columns)
    default_idx = 0
    if guessed_time_col in time_col_options:
        default_idx = time_col_options.index(guessed_time_col)

    selected_time_col = st.selectbox(
        "Cột dùng để tách Thời gian/Số lượng",
        options=time_col_options,
        index=default_idx,
        help="Sẽ lấy 6 ký tự đầu (yymmdd...) hoặc dạng dd/mm để quy đổi ra tháng.",
    )

    filtered_df = _filter_dataframe(selected_df)

    c4, c5 = st.columns(2)
    c4.metric("Số dòng", len(filtered_df))
    c5.metric("Số cột", len(filtered_df.columns))

    st.dataframe(filtered_df, width="stretch", height=500)

    summary_scope = st.radio(
        "Phạm vi tổng hợp Thời gian/Số lượng",
        options=["Sheet đang chọn", "Tất cả sheet"],
        horizontal=True,
        key="time_summary_scope",
    )

    if summary_scope == "Tất cả sheet":
        _render_time_summary_for_all_sheets(tabs_data, selected_time_col)
    else:
        _render_time_summary_for_sheet(
            selected_df,
            filtered_df,
            selected_sheet,
            selected_time_col,
        )

    _render_doi_shopee_summary(selected_df, selected_sheet, selected_time_col)


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
