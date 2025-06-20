# 遊樂園購票系統 (Amusement Park Ticketing System)

本專案是一個以 Flask 為基礎的遊樂園線上購票與會員管理系統，支援會員註冊、登入、購票、購物車、訂單查詢、QR Code 票券、會員資料編輯，以及管理員後台功能。

## 目錄
- [功能介紹](#功能介紹)
- [安裝與執行](#安裝與執行)
- [專案結構](#專案結構)
- [主要技術](#主要技術)
- [資料庫說明](#資料庫說明)
- [管理員功能](#管理員功能)
- [授權](#授權)

## 功能介紹

- 會員註冊、登入、登出、忘記密碼
- 線上購票（成人票、學生票）
- 購物車功能（加入、修改數量、刪除、結帳）
- 訂單查詢與 QR Code 票券下載
- 會員資料編輯
- 管理員後台（會員管理、訂單總覽、會員新增/刪除）

## 安裝與執行

1. **安裝 Python 3.8+ 與 pip**
2. **安裝相依套件**
   ```sh
   pip install -r requirements.txt
   ```
3. **啟動伺服器**
   ```sh
   python app.py
   ```
   預設會在 `localhost:5000` 執行。

4. **預設管理員帳號**
   - 帳號：admin
   - 密碼：123

## 專案結構

```
amusement_park_ticketing/
│
├── app.py                # 主程式
├── config.py             # 設定檔
├── requirements.txt      # 相依套件
├── membership.db         # SQLite 資料庫（啟動時自動建立）
├── static/               # 靜態資源（CSS/JS/圖片/QR Code）
│   ├── css/
│   ├── js/
│   └── images/
├── templates/            # 前端模板（HTML）
│   ├── index.html
│   ├── tickets.html
│   ├── readyshopping.html
│   ├── my_orders.html
│   ├── edit_profile.html
│   ├── admin_orders.html
│   ├── admin_users.html
│   ├── login.html
│   ├── forgot_password.html
│   ├── error.html
│   └── ...
└── README.md
```

## 主要技術

- Python 3
- Flask 3
- SQLite
- Jinja2
- qrcode
- HTML/CSS/JavaScript

## 資料庫說明

- **members**：會員資料（含管理員）
- **cart**：購物車內容
- **orders**：訂單與 QR Code 資訊

啟動時會自動建立資料表與預設管理員帳號。

## 管理員功能

- 進入 `/admin/users` 可管理會員（新增、刪除，admin 不可刪除）
- 進入 `/admin/orders` 可瀏覽所有會員訂單

## 授權

本專案採用 MIT License，詳見 [`LICENSE`](LICENSE )。

---

如有問題歡迎提出 issue 或聯絡作者。
