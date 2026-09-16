# Google Sheets Dashboard

Ung dung Streamlit de doc du lieu tu Google Sheets (nhieu tab) va hien thi dashboard tong quan.

## Chay local

```powershell
cd D:\Work\Sunhouse\Dashboard
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run Home.py
```

Lan dau bam nut Ket noi va tai du lieu, trinh duyet se mo de dang nhap Google OAuth (neu dung che do oauth).

## Cac che do xac thuc

App ho tro 2 che do:

1. `oauth` (mac dinh): dung `credentials.json` + `token.json`, phu hop local.
2. `service_account`: phu hop deploy cloud, khong can login tren browser.

### Bien moi truong

Xem mau day du trong `.env.example`:

- `GOOGLE_AUTH_MODE=oauth|service_account`
- `GOOGLE_CLIENT_SECRET_FILE`
- `GOOGLE_TOKEN_FILE`
- `GOOGLE_SERVICE_ACCOUNT_FILE`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SPREADSHEET`
- `CACHE_TTL_SECONDS`

## Deploy len Streamlit Community Cloud (khuyen nghi)

1. Push code len GitHub repo nay.
2. Tao Service Account trong Google Cloud Console.
3. Bat Google Sheets API cho project.
4. Share file Google Sheet cho email cua Service Account voi quyen Viewer.
5. Vao Streamlit Community Cloud va chon New app.
6. Chon repo `CuongGiap/Sunhouse-Dashboard`, branch `main`, main file path `Home.py`.
7. Mo Advanced settings > Secrets, dan noi dung theo mau trong `.streamlit/secrets.example.toml`.
8. Sua lai 2 gia tri bat buoc trong Secrets:
   - `GOOGLE_SPREADSHEET`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
9. Bam Deploy app.

Goi y: neu nhap JSON tren cloud, giu nguyen toan bo chuoi JSON (gom private_key).
App da duoc cap nhat de doc ca environment variables va Streamlit secrets.

## Deploy len Render

Repo da co san file `render.yaml`.

1. Tao Web Service tren Render tu GitHub repo.
2. Render tu doc `render.yaml` va start command.
3. Them environment variables tren Render:
   - `GOOGLE_AUTH_MODE=service_account`
   - `GOOGLE_SPREADSHEET=<url-hoac-id-sheet>`
   - `GOOGLE_SERVICE_ACCOUNT_JSON=<json-service-account-day-du>`
4. Redeploy.

## Bao mat

Cac file nhay cam da duoc ignore:

- `.env`
- `credentials.json`
- `token.json`
- `client_secret_*.json`
- `*.apps.googleusercontent.com.json`

Khong commit service account JSON vao repo.
