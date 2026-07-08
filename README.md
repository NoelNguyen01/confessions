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

- Ubuntu (Khuyên dùng)
- Python >= 3.8
- pip
- (Tuỳ chọn) MongoDB Atlas / MongoDB local
- (Tuỳ chọn) Facebook Page + quyền quản lý Page để lấy token

---

## 2) Cài đặt server (Ubuntu)

### 2.1 Clone repo
```bash
git clone https://github.com/laivansam11920/CONFESSION.git
cd CONFESSION
```

### 2.2 Tạo môi trường ảo
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2.3 Cài dependencies
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

Tạo file `.env` trong thư mục server (thư mục chạy app):

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

# Format message (tuỳ code)
TOTAL_MES=DANH SÁCH CONFESSION MỚI NHẤT\n\n

# Đường dẫn credentials.json trên Ubuntu
GOOGLE_APPLICATION_CREDENTIALS=/confession_app/credentials.json
```

### Giải thích các biến “quan trọng thật”
- `SHEET_NAME`: tên tab sheet chứa câu trả lời (ví dụ `Confession_app`)
- `GOOGLE_APPLICATION_CREDENTIALS`: đường dẫn file credentials.json (service account key)
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
    var url = "https://inundatory-unpigmented-patsy.ngrok-free.dev/submit";

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

Mục tiêu: có file key JSON đặt tại:
`/home/laivansam/confession_app/credentials.json`

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

### 6.5 Đưa file về đúng path trên Ubuntu
Giả sử file tải về nằm trong `~/Downloads/`:

```bash
mkdir -p /home/laivansam/confession_app
mv ~/Downloads/*.json /home/laivansam/confession_app/credentials.json
chmod 600 /confession_app/credentials.json
```

Kiểm tra:
```bash
ls -l /confession_app/credentials.json
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
Chạy server local (ví dụ port 5000) rồi:
```bash
ngrok http 5000
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
- Sai `SPREADSHEET_ID` / sai `SHEET_NAME`
- Sai đường dẫn `GOOGLE_APPLICATION_CREDENTIALS`

### 9.3 File credentials.json bị lộ
- Không commit lên GitHub
- `chmod 600`
- Đừng gửi file lên chat/public

---

## 10) Gợi ý endpoint /submit nên làm gì (để đúng luồng)
- Xác thực `your_key`
- Gọi Sheets API đọc dòng mới nhất trong `SHEET_NAME`
- Parse confession/email theo `CONFESSION_QUESTION` và `EMAIL_QUESTION`
- Lưu MongoDB
- Đăng Facebook (nếu bật)

---
