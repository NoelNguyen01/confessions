# CONFESSION (Python) — Google Form → Ping Server → Server đọc Google Sheet → MongoDB → Facebook Page

Dự án này chạy theo đúng luồng sau:

**(1) Người dùng bấm gửi Google Form**  
→ **(2) Form lưu câu trả lời vào Google Sheet**  
→ **(3) Apps Script Trigger chạy `onFormSubmit(e)` chỉ để “bắn 1 request” về server** (KHÔNG gửi nội dung confession)  
→ **(4) Server nhận ping**  
→ **(5) Server dùng Google Sheets API đọc dữ liệu mới nhất từ Google Sheet**  
→ **(6) Server lưu vào MongoDB**  
→ **(7) (Tuỳ chọn) Server đăng lên Facebook Page bằng Graph API**

---

# 🪟 BẢN WINDOWS 10 (hướng dẫn nhanh)

> Repo này đã được chỉnh để chạy được trên Windows 10:
> - Đã bỏ `gunicorn`, `pexpect`, `ptyprocess` (chỉ chạy được trên Linux).
> - Có sẵn `setup.bat`, `run.bat`, `ngrok.bat`, `.env.example`.

## Bước nhanh trên Windows

1. **Cài Python 3.8+** tại https://python.org — khi cài **tick chọn "Add Python to PATH"**.
2. Tải repo về và giải nén (hoặc `git clone`).
3. Copy file **`credentials.json`** (tạo ở mục 6 bên dưới) vào **đúng thư mục gốc** của project (cùng chỗ với `run.py`).
4. **Bấm đúp `setup.bat`** → tự tạo `.venv`, cài dependencies, tạo file `.env` từ `.env.example`.
5. **Mở file `.env`** bằng Notepad và điền: `MONGO_URI`, `YOUR_KEY`, `SHEET_NAME`, `GOOGLE_AI_API_KEY`, (tuỳ chọn) `ACCESS_TOKEN`/`PAGE_ID`.
6. **Bấm đúp `run.bat`** để chạy server → URL là `http://localhost:3000`.
7. Muốn nhận ping từ Google Form → **bấm đúp `ngrok.bat`** để có URL công khai `https://xxxx.ngrok-free.dev`, rồi dán URL đó vào Apps Script (`https://xxxx.ngrok-free.dev/submit`).

> ⚠️ Lưu ý: server chỉ nhận ping được từ Google Form khi có **URL công khai** (ngrok/VPS). `localhost` không truy cập được từ internet.

---

## 0) Checklist nhanh (ông làm theo thứ tự này)

- [ ] Tạo Google Form và liên kết với Google Sheet
- [ ] Tạo Apps Script + Trigger “On form submit” để ping server
- [ ] Tạo Google Cloud Project
- [ ] Bật **Google Sheets API** và **Google Drive API**
- [ ] Tạo **Service Account** và tải **credentials.json**
- [ ] Share Google Sheet cho email của Service Account
- [ ] Setup `.env` cho server (MongoDB, Facebook, Sheet info)
- [ ] Chạy server + public URL (ngrok/VPS)
- [ ] Test: submit form → server log nhận ping → server đọc sheet → lưu DB → đăng FB

---

## 1) Yêu cầu hệ thống

- Windows 10 (bản này) **hoặc** Ubuntu/Linux
- Python >= 3.8 (trên Windows: tick **"Add Python to PATH"** khi cài)
- pip
- (Tuỳ chọn) MongoDB Atlas / MongoDB local
- (Tuỳ chọn) Facebook Page + quyền quản lý Page để lấy token

---

## 2) Cài đặt server

### 2.0 Trên Windows 10 (khuyên dùng)

Không cần gõ lệnh tay, chỉ cần:

```bat
setup.bat   :: tạo .venv + cài dependencies + tạo .env
run.bat     :: chạy server (http://localhost:3000)
ngrok.bat   :: mở tunnel công khai cho Apps Script
```

Các bước chi tiết nằm ở phần **BẢN WINDOWS 10** ở đầu README.

### 2.1 Trên Ubuntu/Linux: Clone repo
```bash
git clone https://github.com/laivansam11920/CONFESSION.git
cd CONFESSION
```

### 2.2 Tạo môi trường ảo (Ubuntu/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2.3 Cài dependencies (Ubuntu/Linux)
Nếu có `requirements.txt`:
```bash
pip install -r requirements.txt
```

Nếu chưa có, tối thiểu thường cần:
```bash
pip install flask requests python-dotenv pymongo google-api-python-client google-auth google-auth-oauthlib
```

---

## 3) Biến môi trường (.env)

Trong repo đã có sẵn file mẫu **`.env.example`**.
Copy nó thành `.env` (trên Windows: `copy .env.example .env`) rồi điền giá trị thật:

```env
# Database
MONGO_URI=

# Facebook (nếu muốn auto đăng)
ACCESS_TOKEN=
PAGE_ID=

# Xác thực ping từ Apps Script (khuyên dùng)
YOUR_KEY=

# Google Sheet
SHEET_NAME=Confession_app

# Tên câu hỏi trong Google Form (PHẢI KHỚP 100% ký tự)
CONFESSION_QUESTION=Confession của bạn là gì?
EMAIL_QUESTION=Gmail liên hệ của bạn là gì?

# Google AI
GOOGLE_AI_API_KEY=
PORT=3000
```

### Giải thích các biến “quan trọng thật”
- `SHEET_NAME`: tên tab sheet chứa câu trả lời (ví dụ `Confession_app`)
- `credentials.json`: file key của Service Account — đặt **cùng thư mục gốc project** (cùng chỗ `run.py`). Code đọc theo đường dẫn tương đối `credentials.json`, nên **không** cần biến `GOOGLE_APPLICATION_CREDENTIALS`.
- `YOUR_KEY`: khoá để server từ chối ping giả mạo

---

## 4) Google Form + Google Sheet

### 4.1 Tạo Google Form
Tạo đúng câu hỏi (để server bóc dữ liệu theo tên câu hỏi):
- `Confession của bạn là gì?`
- `Gmail liên hệ của bạn là gì?`

### 4.2 Liên kết Form với Sheet
Google Form → tab **Câu trả lời** → “Liên kết với Trang tính” → tạo Sheet.

---

## 5) Apps Script: chỉ ping server khi có submit

### 5.1 Mở Apps Script
Mở Google Sheet → **Extensions (Tiện ích mở rộng)** → **Apps Script**

### 5.2 Code `onFormSubmit(e)` (chỉ ping)
> Lưu ý: ở luồng này, ông không cần gửi `e.namedValues` (vì server tự đọc Sheet).  
> Nhưng giữ lại cũng được để debug. README này viết đúng theo yêu cầu “chỉ ping”.

```javascript
function onFormSubmit(e) {
  try {
    // URL server Render (hoặc ngrok). KHÔNG còn là "localhost".
    // Key có thể nằm trong path: /submit/<YOUR_KEY> HOẶC trong body your_key (server hỗ trợ cả 2).
    var url = "https://THAY_DOMAIN_RENDER_CUA_BAN.onrender.com/submit";

    if (!e) {
      console.log("e bị rỗng, hàm này cần được chạy bởi Trigger!");
      return;
    }

    var payload = {
      "event": "form_submit",
      "your_key": "GIÁ_TRỊ_TRÙNG_VỚI_YOUR_KEY_TRONG_.env",
      "ts": new Date().toISOString()
      // Không gửi confession ở đây. Server sẽ tự đọc Sheet.
    };

    var options = {
      "method": "post",
      "contentType": "application/json",
      "payload": JSON.stringify(payload),
      "muteHttpExceptions": true
    };

    var res = UrlFetchApp.fetch(url, options);
    console.log("Ping server xong! Status: " + res.getResponseCode());
    console.log(res.getContentText());

  } catch (err) {
    console.log("Lỗi xảy ra: " + err.toString());
  }
}
```

### 5.3 Tạo Trigger
Apps Script → **Triggers (Kích hoạt)** → Add Trigger:
- Function: `onFormSubmit`
- Event source: From spreadsheet
- Event type: On form submit
- Save và cấp quyền.

---

## 6) Lấy `credentials.json` trong Google Cloud Console (Sheets API + Drive API)

Mục tiêu: có file key JSON đặt tại **thư mục gốc project** (cùng chỗ `run.py`, cạnh file `.env`).

### 6.1 Tạo Google Cloud Project
1. Vào Google Cloud Console
2. Chọn **Select a project** → **New Project**
3. Đặt tên, tạo project.

### 6.2 Bật API cần thiết
Vào **APIs & Services** → **Library**:
- Tìm và bật **Google Sheets API**
- Tìm và bật **Google Drive API**

> Vì sao cần Drive API?  
> - Nhiều trường hợp ông cần Drive API để truy cập file theo quyền, tìm file, đọc metadata, hoặc thao tác liên quan file sheet.  
> - Nếu ông chỉ đọc values, đôi khi Sheets API là đủ, nhưng bật Drive API giúp khỏi “đụng tường” khi mở rộng.

### 6.3 Tạo Service Account
1. Vào **IAM & Admin** → **Service Accounts**
2. **Create Service Account**
3. Đặt tên, Create & Continue
4. Role: (đơn giản) có thể để trống, vì quyền truy cập sheet chủ yếu đến từ việc share file.  
   (Nếu bạn biết rõ, có thể cấp thêm role tối thiểu. Nhưng share file vẫn là bước bắt buộc.)

### 6.4 Tạo Key JSON và tải về (đây chính là credentials.json)
1. Chọn service account vừa tạo
2. Tab **Keys**
3. **Add Key** → **Create new key**
4. Chọn **JSON** → Create → Tải file về máy

File tải về có dạng: `xxxxx-xxxxx.json`  
=> Đó chính là `credentials.json` (service account key).

### 6.5 Đưa file về đúng thư mục

**Trên Windows:** copy file `xxxxx-xxxxx.json` tải về vào thư mục gốc project và **đổi tên thành `credentials.json`** (hoặc bấm đúp `setup.bat` — nó sẽ nhắc bạn nếu chưa có file này).

**Trên Ubuntu/Linux:** (giả sử file nằm trong `~/Downloads/`)
```bash
mkdir -p /home/laivansam/confession_app
mv ~/Downloads/*.json /home/laivansam/confession_app/credentials.json
chmod 600 /confession_app/credentials.json
```

### 6.6 Share Google Sheet cho Service Account (BẮT BUỘC)
1. Mở file Google Sheet (nơi chứa responses)
2. Bấm **Share**
3. Copy email của Service Account (dạng: `xxx@xxx.iam.gserviceaccount.com`)
4. Add email đó vào share với quyền:
   - **Viewer** (chỉ đọc) là đủ nếu server chỉ đọc
   - **Editor** nếu server cần ghi/chỉnh

Nếu không share, server sẽ báo kiểu “The caller does not have permission”.

## 7) Public URL cho server (ngrok/VPS)

### 7.1 Ngrok (nhanh để test)

**Trên Windows:** bấm đúp `ngrok.bat` (nhập port mặc định là `3000`), hoặc tự chạy:
```bat
ngrok http 3000
```

**Trên Ubuntu/Linux:**
```bash
ngrok http 3000
```

Copy domain `https://xxxxx.ngrok-free.dev`  
Dán vào Apps Script:
`https://xxxxx.ngrok-free.dev/submit`

> Nhưng! Ngrok free thường đổi domain khi restart → ông phải update lại URL.

### 7.2 Deploy server (dùng lâu dài)
Deploy lên VPS/Render/Railway/Fly.io để có domain cố định.

---

## 8) Facebook Graph API (tuỳ chọn)

### 8.1 ACCESS_TOKEN
- Token dùng để đăng bài lên Page.
- Token có thể hết hạn → nên dùng loại token dài hạn nếu chạy lâu.

### 8.2 PAGE_ID
ID của page ông muốn đăng.

---

## 9) Troubleshooting

### 9.1 `e bị rỗng`
Bạn chạy script bằng nút Run trong Apps Script editor.  
`onFormSubmit(e)` chỉ có `e` khi chạy từ Trigger (form submit).

### 9.2 Server nhận ping nhưng không đọc được sheet
- Quên share sheet cho service account
- Sai `SHEET_NAME` (phải khớp tên tab sheet)
- Không có file `credentials.json` đúng chỗ (phải nằm ở thư mục gốc project, cùng chỗ `run.py`)
- `credentials.json` không phải file key JSON của Service Account đúng project

### 9.3 File credentials.json bị lộ
- Không commit lên GitHub (đã nằm trong `.gitignore`)
- Đừng gửi file lên chat/public

### 9.4 Windows: “python không phải là lệnh”
- Khi cài Python trên Windows, **tick "Add Python to PATH"**.
- Nếu đã cài rồi, gỡ cài lại hoặc chạy `py` thay cho `python` (Windows Launcher).
- `setup.bat` dùng lệnh `python`; nếu máy chỉ có `py`, mở `setup.bat` sửa `python` → `py -3`.

### 9.5 Render Free bị "ngủ" sau 15 phút → Log không nhảy khi submit Form
- Render Free **tự Sleep sau 15 phút không có request** và chỉ "thức dậy" khi có request mới (mất vài chục giây).
- Cần 1 trình **giữ ấm (keep-alive)** bấm vào server mỗi ~10 phút để không bao giờ ngủ:
  1. Vào https://cron-job.org (hoặc https://uptimerobot.com) tạo **monitor/cron** dạng **HTTP GET**.
  2. URL bấm vào: `https://THAY_DOMAIN_RENDER_CUA_BAN.onrender.com/health`
     - Endpoint `/health` không cần key, trả `{"success": true}` ngay khi server còn sống.
  3. Đặt chu kỳ **mỗi 10 phút** → Render không bao giờ Sleep → log tự nhảy ngay khi có Form.
- Kiểm tra nhanh server còn sống bằng cách mở `https://THAY_DOMAIN_RENDER_CUA_BAN.onrender.com/health` trên trình duyệt.

### 9.6 Apps Script "ping" nhưng server trả 404 / không nhảy log
- URL trong Apps Script **phải là URL Render công khai**, KHÔNG phải `localhost`.
- Endpoint đúng là `/submit` kèm `your_key` trong body **hoặc** `/submit/<YOUR_KEY>` (server hỗ trợ cả 2 từ bản mới).
- Sau khi sửa code trong Apps Script, nhớ **lưu (Save)** và tạo/kiểm tra lại **Trigger: Event type = On form submit**.

### 9.7 Pipedream nhận bài nhưng không đăng lên Facebook → lỗi 283
- Lỗi `OAuthException Code 283: Requires pages_read_engagement permission` nghĩa là **App Facebook thiếu quyền Page**, không phải lỗi server.
- Cách sửa:
  1. Vào https://developers.facebook.com → chọn App đang dùng.
  2. Mục **App Review → Permissions and Features**: thêm **`pages_read_engagement`** và **`pages_manage_posts`**.
  3. Với App đang ở chế độ Development, gán tài khoản **Quynh Tien** làm Admin/Test và **đăng nhập lại** vào App để nhận quyền.
  4. Trong Pipedream: **Disconnect rồi Connect lại** tài khoản Facebook của Quynh Tien, chọn lại Page, đảm bảo token có 2 quyền trên.
  5. Test lại bằng cách bấm "Send Test Event" trong Pipedream.

### 9.8 Dữ liệu cũ bị kẹt trong MongoDB (active=True) không được duyệt/đăng
- Hệ thống chỉ xử lý bài có `active: false`. Bài test cũ `active: true` sẽ bị bỏ qua mãi.
- Dùng tool đi kèm để liệt kê / reset / xoá:
  ```bat
  .venv\Scripts\python.exe script\reset_db.py --list        :: xem bài kẹt
  .venv\Scripts\python.exe script\reset_db.py --reprocess   :: set active=False để duyệt+đăng lại
  .venv\Scripts\python.exe script\reset_db.py --delete      :: xoá vĩnh viễn bài kẹt
  ```
- Nếu đổi **mật khẩu MongoDB Atlas**: cập nhật lại `MONGO_URI` trong `.env` (và biến môi trường trên Render) với password mới, rồi restart server.

---

## 10) Gợi ý endpoint /submit nên làm gì (để đúng luồng)
- Xác thực `your_key`
- Gọi Sheets API đọc dòng mới nhất trong `SHEET_NAME`
- Parse confession/email theo `CONFESSION_QUESTION` và `EMAIL_QUESTION`
- Lưu MongoDB
- Đăng Facebook (nếu bật)

---
