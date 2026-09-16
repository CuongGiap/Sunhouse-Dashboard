# Google Sheets Dashboard

Ung dung Streamlit de doc du lieu tu mot Google Sheet (nhieu tabs) va hien thi dashboard tong quan.

## 1. Cai dat

```powershell
cd D:\Work\Sunhouse\Dashboard
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Tao OAuth credentials (1 lan)

1. Mo Google Cloud Console.
2. Tao project moi (hoac dung project san co).
3. Bat Google Sheets API.
4. Vao APIs & Services > Credentials > Create Credentials > OAuth client ID.
5. Chon Application type: Desktop app.
6. Tai file JSON ve va dat ten `credentials.json` trong thu muc goc Dashboard.

## 3. Cau hinh bien moi truong

```powershell
Copy-Item .env.example .env
```

Co the sua lai `GOOGLE_SPREADSHEET` trong `.env` thanh URL hoac ID cua file can doc.

## 4. Chay app

```powershell
streamlit run Home.py
```

Lan dau nhan nut **Ket noi va tai du lieu**, trinh duyet se mo trang dang nhap Google:
- Dang nhap bang tai khoan da co quyen voi Google Sheet.
- Chap nhan quyen truy cap read-only.
- Sau khi xong, file `token.json` duoc tao local de tai su dung.

## 5. Bao mat

- `credentials.json` va `token.json` da duoc bo qua trong `.gitignore`.
- Khong commit 2 file nay len git.
- Neu doi tai khoan hoac thu hoi quyen, xoa `token.json` va login lai.

## 6. Ghi chu

- App hien tai doc toan bo tabs trong file va cho phep preview tung tab.
- Dung cache theo `CACHE_TTL_SECONDS` (mac dinh 300 giay).
- Neu tab co dong header khong nam o dong 1, can bo sung buoc mapping rieng o phien ban tiep theo.
