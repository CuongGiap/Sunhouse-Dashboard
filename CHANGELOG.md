# CHANGELOG — Sunhouse Dashboard

Tài liệu này ghi lại toàn bộ quá trình xây dựng, sự cố đã gặp và cách xử lý cho ứng dụng
Google Sheets Dashboard (Streamlit), phục vụ mục đích traceback khi cần tra lại lịch sử.

Repo: https://github.com/CuongGiap/Sunhouse-Dashboard
App production: https://sunhouse-dashboard.streamlit.app/

## Kiến trúc tổng quan

- `Home.py`: Toàn bộ UI + logic dashboard (Streamlit, single-page app).
- `src/settings.py`: Đọc cấu hình từ biến môi trường hoặc `st.secrets` (Streamlit Cloud).
- `src/google_sheets.py`: Xác thực Google (OAuth desktop hoặc Service Account) và đọc dữ liệu
  nhiều tab từ Google Sheets, chuẩn hoá thành `pandas.DataFrame`.
- `.streamlit/secrets.example.toml`: Mẫu secrets cho Streamlit Cloud.
- `render.yaml`: Cấu hình deploy thay thế trên Render (tuỳ chọn, ngoài Streamlit Cloud).

## Lịch sử commit (từ khởi tạo đến hiện tại)

1. `27b4e02` Initial Streamlit Google Sheets dashboard
   - Khởi tạo app đọc nhiều tab Google Sheets, hiển thị thống kê cơ bản và bảng dữ liệu.
2. `6b5b02e` Add cloud deploy auth mode and deployment configs
   - Thêm chế độ xác thực `service_account` để chạy được trên cloud (ngoài `oauth` cho local).
3. `0899d7c` Prepare Streamlit Cloud deployment with secrets support
   - Đọc cấu hình từ `st.secrets` khi deploy lên Streamlit Community Cloud.
4. `aa323d4` Add Streamlit Cloud deploy checks and runtime warnings
   - Cảnh báo khi thiếu Service Account credentials trên cloud.
5. `5c01c9f` Accept object-form Streamlit secrets for service account
6. `3693cd3` Handle Streamlit secrets mapping values
7. `e874ea1` Fix parsing of service account JSON secrets
   - 3 commit trên xử lý việc `st.secrets` có thể trả về secret dạng string JSON hoặc dạng
     mapping/table TOML; sửa lỗi parse JSON và newline trong private key.
8. `72a53b3` Add optional app access token gate
   - Thêm lớp bảo mật thứ 2: `APP_ACCESS_TOKEN` yêu cầu nhập mã truy cập trước khi vào app.
9. `51e0db3` Add monthly reason filter for Đổi Shopee tab
10. `96898f2` Add Đổi Shopee reason search with month filter
11. `d09ee94` Improve Đổi Shopee month parsing and count stats
    - 3 commit trên: thêm phân tích tab ĐỔI SHOPEE theo `Lý do (Lỗi, linh kiện, bù)`, tách
      tháng từ dữ liệu, đếm số lượng + tỷ lệ % theo tháng.
12. `fa12e6d` Add all-sheets time and quantity summary
13. `f2505d3` Make time summary follow selected sheet and filters
14. `5122b3a` Add scope toggle for time summary
    - Thêm bảng tổng hợp "Thời gian/Số lượng", cho phép chọn phạm vi: Sheet đang chọn hay
      Tất cả sheet.
15. `a5ec9d5` Use MSP column for month-year extraction
    - Đổi nguồn tách tháng sang cột MSP (6 ký tự đầu dạng `yymmdd`).
16. `a434230` Make time summary robust to renamed columns
    - Sau khi cột trong Google Sheet bị đổi tên/thứ tự, bổ sung cơ chế tự dò cột thời gian
      (`_guess_time_column`) và cho phép chọn thủ công cột dùng để tách Thời gian/Số lượng.
17. `0878d66` Improve time summary fallback and date parsing
    - Mở rộng định dạng nhận diện ngày (yyyymmdd, dd/mm/yyyy, yyyy-mm-dd...), thêm fallback
      tự động sang cột khác khi cột đang chọn không tách được ngày.
18. `f067dfc` Handle more date formats and isolate time column per sheet
    - Thêm nhận diện số serial Excel, tách riêng state lựa chọn cột thời gian theo từng sheet
      (tránh việc đổi tab bị giữ lựa chọn cột cũ).
19. `fa86b24` Guard Excel serial date parsing against overflow
    - **Sự cố production**: `OverflowError` khi convert giá trị số bất kỳ (rất lớn) thành ngày
      theo serial Excel → app crash toàn bộ, không hiển thị được phần tổng hợp thời gian.
    - Fix: giới hạn khoảng giá trị hợp lệ (1–100000) trước khi convert.
20. `79e6660` Avoid datetime fillna overflow in month extraction
    - **Sự cố production tiếp theo**: dù đã chặn overflow ở bước convert, việc `fillna` giữa
      nhiều `Series` kiểu `datetime64` với các đơn vị thời gian khác nhau vẫn có thể overflow.
    - Fix triệt để: đổi toàn bộ pipeline tách tháng sang làm việc trên chuỗi `"MM/YYYY"`
      (kiểu `object`) thay vì gộp trực tiếp nhiều `Series` datetime, tránh lỗi overflow của
      pandas khi `fillna` giữa các datetime64 khác đơn vị.
21. `5deecf8` Add dual keyword comparison tables and trend chart
    - Bản đầu tiên của tính năng so sánh 2 từ khóa: 2 ô tìm kiếm toàn bảng, ra 2 bảng riêng
      + biểu đồ xu hướng. (Sau đó được yêu cầu làm lại cho đúng nghiệp vụ hơn.)
22. `047f203` Rework comparison to single 4-column table (STT, Date, value1, value2)
    - Làm lại theo đúng yêu cầu: chọn 1 cột để so sánh (`Cột muốn so sánh`), nhập 2 từ khóa
      tìm **trong chính cột đó**, xuất ra **1 bảng duy nhất 4 cột**:
      - `STT`: số thứ tự
      - `Date`: tháng/năm tách theo "Cột dùng để tách Thời gian/Số lượng"
      - Cột 3: số lượng dòng khớp từ khóa 1 theo từng Date
      - Cột 4: số lượng dòng khớp từ khóa 2 theo từng Date
    - Kèm biểu đồ line so sánh xu hướng số lượng theo 2 từ khóa theo Date.

23. (chưa commit) Sửa lỗi bảng so sánh không ra giá trị
    - **Nguyên nhân 1**: so khớp từ khóa không bỏ dấu tiếng Việt → gõ `loi` không khớp `Lỗi`
      (phần ĐỔI SHOPEE đã chuẩn hoá bằng `_normalize_text`, phần so sánh thì chưa).
    - **Nguyên nhân 2**: `str.contains` mặc định coi từ khóa là regex → từ khóa chứa `(`, `)`,
      `+`... gây lỗi `Invalid regular expression` và không ra bảng.
    - **Nguyên nhân 3**: dòng khớp từ khóa nhưng cột thời gian không tách được ngày thì bị
      loại âm thầm, không có fallback sang cột thời gian khác, không báo rõ lý do.
    - Cách fix:
      - `_keyword_match_mask`: chuẩn hoá bỏ dấu + `re.escape`, thêm tuỳ chọn khớp chính xác cả ô.
      - `_count_keyword_matches_by_date`: trả thêm (tổng dòng khớp, số dòng thiếu ngày) để hiển
        thị chẩn đoán thay vì im lặng.
      - Tự động fallback sang cột thời gian đoán được khi cột đang chọn không tách được ngày.
      - Tách `_extract_date_label(series, date_format)` dùng chung; `_extract_month_label` trở
        thành wrapper `%m/%Y` (giữ nguyên toàn bộ guard chống `OverflowError`).
      - Thêm chọn đơn vị cột Date: theo tháng (MM/YYYY) hoặc theo ngày (DD/MM/YYYY).
      - Thêm expander "Gợi ý giá trị đang có trong cột" (top 15) để nhập đúng từ khóa.
      - Bảng vẫn đúng 4 cột STT | Date | SL 'giá trị 1' | SL 'giá trị 2', kèm dòng Tổng và
        biểu đồ xu hướng.

24. (chưa commit) Tinh chỉnh giao diện bảng so sánh và sidebar
    - Bảng so sánh: cột `STT` rộng 70px, cột `Date` rộng 110px, toàn bộ ô căn giữa bằng
      `st.column_config` (`width=<px>`, `alignment="center"`). Áp dụng cho cả dòng Tổng.
    - Sidebar: bỏ các dòng thông tin kỹ thuật (OAuth secret, OAuth token, Auth mode,
      Service account file, Cache TTL), chỉ còn ô `Spreadsheet URL / ID`.
    - Nút `Đăng xuất` chuyển xuống cuối sidebar, có `st.divider()` phân tách, rộng full sidebar.
    - `requirements.txt`: nâng sàn `streamlit>=1.37` → `>=1.64` vì `alignment` và `width` dạng
      pixel của `column_config` chỉ có ở bản mới; bản cũ sẽ lỗi `TypeError`.
    - Biểu đồ so sánh: cố định màu đường kẻ - giá trị 1 đỏ `#e34948`, giá trị 2 xanh dương
      `#2a78d6` (`color_discrete_map`), độ dày nét 2px, marker 8px. Cặp màu này đã kiểm tra
      đạt dải sáng, chroma, tương phản >= 3:1 và tách màu cho người mù màu (ΔE 21.6 protan)
      trên cả nền sáng lẫn nền tối, nên dùng chung một cặp cho mọi theme.

25. (chưa commit) Rà soát bảo mật và xử lý các phát hiện ưu tiên
    - **Xác thực fail-open (nghiêm trọng)**: khi `APP_ACCESS_TOKEN` trống/thiếu, code cũ gán
      `auth_ok = True` → app mở công khai toàn bộ dữ liệu Sheet cho bất kỳ ai có URL. Đổi sang
      fail-closed: thiếu cấu hình thì hiện lỗi, ghi log và `st.stop()`.
    - **`.gitignore` không chặn private key (nghiêm trọng)**: dòng `!.streamlit/` vô hiệu hoá
      ignore của cả thư mục nên `.streamlit/secrets.toml` sẽ bị commit; `service-account.json`
      (đường dẫn mặc định trong `settings.py`) không hề có trong danh sách. Sửa thành
      `.streamlit/*` + `!.streamlit/secrets.example.toml`, bổ sung `service-account.json`.
      Đã kiểm chứng lại bằng `git check-ignore`. Lịch sử git sạch, chưa từng lộ credential.
    - **Lộ traceback**: `st.exception(exc)` in nguyên stack trace kèm đường dẫn server cho
      người dùng cuối → đổi thành `logger.exception` + thông báo lỗi chung.
    - **So sánh mã truy cập**: `==` → `hmac.compare_digest` (constant-time), encode utf-8 để
      mã có ký tự ngoài ASCII không ném `TypeError`.
    - **Ô "Tìm nhanh trong bảng"**: từ khóa vẫn bị hiểu là regex, gõ `(` làm app crash →
      thêm `regex=False`. (Đã test: không phải lỗ hổng ReDoS vì pandas dùng engine Arrow/RE2
      không có backtracking, chỉ là crash.)
    - **Chặn đọc sheet ngoài phạm vi**: bỏ ô nhập Spreadsheet URL/ID tự do ở sidebar (người
      dùng có thể dán ID bất kỳ và app đọc bằng credential hệ thống). Thay bằng allowlist
      phía server `REPORT_SOURCES`, người dùng chỉ chọn theo tên báo cáo:
      "Báo Cáo Lỗi Đổi Hàng" (`GOOGLE_SPREADSHEET`) và "Báo Cáo Chỉ Số Vận Hành"
      (`GOOGLE_SPREADSHEET_OPERATION`). Báo cáo chưa cấu hình sẽ tự ẩn khỏi danh sách.
      Đổi báo cáo thì xoá dữ liệu đã tải để không hiển thị nhầm số của báo cáo trước.
    - URL của báo cáo thứ 2 đặt trong cấu hình chứ không hardcode: repo này là public, ID
      Google Sheet nội bộ không nên nằm trong source.
    - Kiểm thử bằng `streamlit.testing.v1.AppTest`: thiếu token → app khoá, 0 ô nhập liệu;
      nhập sai → bị từ chối; nhập đúng → vào được; sidebar không còn ô URL tự do.
    - Còn tồn (chưa làm, theo thống nhất): rate limit/log truy cập, phân quyền theo người
      dùng thật thay cho 1 mã dùng chung, pin version dependency.

26. (chưa commit) Fix `AttributeError` khi mở báo cáo có cột trùng tên
    - **Sự cố production**: mở "Báo Cáo Chỉ Số Vận Hành" là app crash
      `AttributeError: 'DataFrame' object has no attribute 'str'` tại `_extract_date_label`.
    - **Nguyên nhân**: sheet có 2 cột cùng tên (và/hoặc ô header trống). `_values_to_dataframe`
      chỉ đổi tên khi *toàn bộ* header rỗng, nên tên cột bị trùng. Với nhãn trùng,
      `df[col]` trả về **DataFrame** thay vì Series → `.str` không tồn tại.
    - Fix tận gốc: thêm `_make_unique_headers` trong `src/google_sheets.py`, chuẩn hoá ngay
      khi đọc dữ liệu - header rỗng thành `col_N`, header trùng thành `Tên (2)`, `Tên (3)`.
      Sheet có header hợp lệ giữ nguyên tên như cũ.
    - Thêm lưới an toàn trong `_extract_date_label`: nếu vẫn nhận DataFrame thì lấy cột đầu,
      để một sheet lạ không làm chết cả app.
    - Bọc `render_dashboard` trong try/except + `logger.exception`, thống nhất với mục 4 của
      đợt rà soát bảo mật: lỗi hiển thị cũng không đổ traceback ra cho người dùng.

## Các sự cố production đã xử lý (tổng hợp riêng để tra nhanh)

| Sự cố | Nguyên nhân | Cách fix | Commit |
| --- | --- | --- | --- |
| App không load được trên Streamlit Cloud | Thiếu Service Account credentials / secrets sai định dạng | Chuẩn hoá đọc `st.secrets` (string JSON hoặc mapping), fix parse private key | `5c01c9f`, `3693cd3`, `e874ea1` |
| Bảng "Phạm vi tổng hợp Thời gian/Số lượng" biến mất | Tên cột trong Google Sheet đổi (không còn khớp "MSP" hardcode) | Thêm `_guess_time_column` tự dò cột thời gian tốt nhất + cho chọn thủ công | `a434230` |
| Vẫn báo "Không tách được thời gian..." dù đã chọn đúng cột | Parser chỉ hỗ trợ 2 định dạng ngày | Mở rộng parser: yyyymmdd, dd/mm/yyyy, yyyy-mm-dd, Excel serial, generic parse | `0878d66`, `f067dfc` |
| App crash `OverflowError` khi vào tab có cột số lớn | Convert số bất kỳ thành ngày kiểu Excel serial không giới hạn khoảng | Giới hạn giá trị hợp lệ trước khi convert | `fa86b24` |
| App vẫn lỗi khi `fillna` giữa nhiều cột datetime64 | Các `Series` datetime khác đơn vị thời gian (unit) gây overflow khi gộp | Đổi pipeline sang gộp chuỗi `"MM/YYYY"` thay vì gộp datetime | `79e6660` |
| Tính năng so sánh 2 từ khóa chưa đúng yêu cầu | Version đầu tìm toàn bảng, ra 2 bảng riêng thay vì 1 bảng 4 cột theo đúng 1 cột chỉ định | Viết lại `_render_dual_keyword_compare` theo đúng đặc tả STT/Date/giá trị 1/giá trị 2 | `047f203` |
| Mở báo cáo mới là crash `AttributeError: 'DataFrame' object has no attribute 'str'` | Sheet có cột trùng tên → `df[col]` trả về DataFrame thay vì Series | `_make_unique_headers` chuẩn hoá tên cột ngay khi đọc dữ liệu | (chưa commit) |
| Xác thực fail-open: thiếu `APP_ACCESS_TOKEN` là app mở công khai | Code cũ gán `auth_ok = True` khi không có token cấu hình | Fail-closed: hiện lỗi, ghi log, `st.stop()` | (chưa commit) |
| `.gitignore` không chặn `.streamlit/secrets.toml` và `service-account.json` | Dòng `!.streamlit/` vô hiệu hoá ignore cả thư mục; thiếu hẳn `service-account.json` | Đổi sang `.streamlit/*` + negation file mẫu, bổ sung `service-account.json` | (chưa commit) |
| Bảng so sánh không hiển thị giá trị nào | Không bỏ dấu tiếng Việt khi so khớp; từ khóa bị hiểu là regex; dòng khớp bị loại vì không tách được ngày | Chuẩn hoá `_normalize_text` + `re.escape`, fallback cột thời gian, hiển thị số dòng khớp và số dòng thiếu ngày | (chưa commit) |

## Bảo mật

- `.env`, `credentials.json`, `token.json`, `client_secret_*.json` đã được thêm vào
  `.gitignore`, không commit lên repo.
- `APP_ACCESS_TOKEN` dùng làm lớp xác thực thứ 2 ở tầng ứng dụng (ngoài xác thực của
  Streamlit Cloud/GitHub).
- Lưu ý: nếu token/secret từng bị dán vào chat hoặc file mẫu, nên rotate (đổi) lại giá trị
  thật trên Google Cloud Console / Streamlit Secrets.

## Trạng thái hiện tại

- App chạy ổn định trên Streamlit Cloud, không còn lỗi `OverflowError`.
- Có đầy đủ: thống kê theo tab, xem dữ liệu chi tiết có filter, tổng hợp Thời gian/Số lượng
  (theo sheet đang chọn hoặc tất cả sheet), phân tích riêng cho tab ĐỔI SHOPEE, và bảng so
  sánh 2 từ khóa theo 1 cột chỉ định (STT/Date/giá trị 1/giá trị 2) kèm biểu đồ xu hướng.
- Bảng so sánh tìm kiếm không phân biệt hoa thường và dấu tiếng Việt, an toàn với ký tự đặc
  biệt, và báo rõ khi không khớp từ khóa hoặc không tách được ngày.
- Sidebar gọn còn bộ chọn báo cáo theo tên và nút Đăng xuất ở cuối; bảng so sánh căn giữa,
  cột STT và Date thu hẹp.
- Đã xử lý các phát hiện bảo mật ưu tiên (fail-closed auth, gitignore, ẩn traceback,
  constant-time compare, chặn regex ở ô tìm nhanh, allowlist nguồn dữ liệu).
