import sqlite3
from flask import Flask, redirect, render_template, request, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import uuid
import os
from datetime import datetime
from config import DevelopmentConfig, ProductionConfig

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# 確保 Flask 內部的 secret_key 屬性也被設置
app.secret_key = app.config['SECRET_KEY']


def connect_db():
    """
    取得資料庫連線並設定 row factory。
    回傳一個可用 with 管理的 sqlite3 連線物件。
    """
    conn = sqlite3.connect("membership.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    初始化資料庫，建立 members、cart、orders 表並插入初始資料。
    若 orders 表不存在 qrcode_code 欄位則自動新增。
    """
    from werkzeug.security import generate_password_hash
    with sqlite3.connect("membership.db") as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS members (
                        iid INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        email TEXT NOT NULL,
                        password TEXT NOT NULL
                    )""")
        # 使用雜湊儲存 admin 密碼
        admin_hash = generate_password_hash("123")
        c.execute(
            "INSERT OR IGNORE INTO members (username, email, password) VALUES (?, ?, ?)",
            ("admin", "admin@gmail.com", admin_hash),
        )

        # 創建購物車表格
        c.execute("""CREATE TABLE IF NOT EXISTS cart (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        ticket_type TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES members (iid)
                    )""")

        # 創建訂單記錄表格，新增 qrcode_code 欄位
        c.execute("""CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        ticket_type TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price REAL NOT NULL,
                        total_amount REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        qrcode_code TEXT,
                        FOREIGN KEY (user_id) REFERENCES members (iid)
                    )""")

        # 若已存在 orders 表但沒有 qrcode_code 欄位則自動新增
        c.execute("PRAGMA table_info(orders)")
        columns = [row[1] for row in c.fetchall()]
        if 'qrcode_code' not in columns:
            c.execute("ALTER TABLE orders ADD COLUMN qrcode_code TEXT")
        conn.commit()

# 在程式啟動時初始化資料庫（只在第一次執行時）
with sqlite3.connect("membership.db") as conn:
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='members'"
    ).fetchone()

if not table_exists:
    init_db()


@app.route("/")
def index():
    """
    首頁：顯示首頁畫面。
    """
    return render_template("index.html")


@app.route("/about")
def about():
    """
    關於我們：顯示關於我們頁面。
    """
    return render_template("about.html")


@app.route("/tickets")
def tickets():
    """
    線上購票：顯示購票頁面。
    """
    return render_template("tickets.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    處理註冊請求：顯示註冊頁面與處理註冊表單。
    """
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        # 檢查必填欄位
        if not (username and email and password):
            return render_template("error.html", message="請輸入用戶名、電子郵件和密碼"), 400

        try:
            with connect_db() as conn:
                c = conn.cursor()
                # 檢查用戶名是否已存在
                c.execute("SELECT username FROM members WHERE username = ?", (username,))
                if c.fetchone():
                    return render_template("error.html", message="用戶名已存在"), 409

                # 密碼雜湊後儲存
                password_hash = generate_password_hash(password)
                c.execute(
                    "INSERT INTO members (username, email, password) VALUES (?, ?, ?)",
                    (username, email, password_hash)
                )
                conn.commit()
                return redirect(url_for("login")), 302
        except Exception as e:
            return render_template("error.html", message="註冊失敗，請稍後再試"), 500

    return render_template("register.html"), 200


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    處理登入請求：顯示登入頁面與處理登入表單。
    """
    if request.method == "POST":
        account = request.form.get("account")
        password = request.form.get("password")

        # 檢查必填欄位
        if not (account and password):
            return render_template("error.html", message="請輸入帳號和密碼"), 400

        with connect_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT username, iid, password FROM members WHERE username = ? OR email = ?",
                (account, account)
            )
            result = c.fetchone()

        if result and (
            (result[0] == 'admin' and check_password_hash(result[2], password)) or
            (result[0] != 'admin' and check_password_hash(result[2], password))
        ):
            session['user_id'] = result[1]
            session['username'] = result[0]
            return render_template("index.html", username=result[0], iid=result[1]), 200
        return render_template("error.html", message="帳號或密碼錯誤"), 401
    return render_template("login.html"), 200


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    """
    忘記密碼頁面：顯示與處理忘記密碼表單。
    """
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        new_password = request.form.get("new_password")

        if not (username and email and new_password):
            return render_template("forgot_password.html", error="請填寫所有欄位"), 400

        with connect_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM members WHERE username=? AND email=?", (username, email))
            user = c.fetchone()
            if user:
                # 所有帳號都用雜湊儲存密碼
                hashed_password = generate_password_hash(new_password)
                c.execute("UPDATE members SET password=? WHERE username=? AND email=?", (hashed_password, username, email))
                conn.commit()
                return render_template("forgot_password.html", message="密碼已成功更新"), 200
            else:
                return render_template("forgot_password.html", error="帳號或Email錯誤"), 404
    return render_template("forgot_password.html"), 200


@app.route("/emptyshopping")
def emptyshopping():
    """
    空購物車：顯示購物車為空的頁面。
    """
    return render_template("emptyshopping.html")


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    """
    添加商品到購物車：將票券加入購物車。
    """
    if 'user_id' not in session:
        return jsonify({"error": "請先登入"}), 401

    ticket_type = request.form.get("ticket_type")
    quantity = int(request.form.get("quantity", 1))
    price = float(request.form.get("price", 0))

    if not all([ticket_type, quantity, price]):
        return jsonify({"error": "缺少必要資訊"}), 400

    with connect_db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO cart (user_id, ticket_type, quantity, price) VALUES (?, ?, ?, ?)",
            (session['user_id'], ticket_type, quantity, price)
        )
        conn.commit()

    return jsonify({"redirect": url_for("readyshopping")})

@app.route("/readyshopping")
def readyshopping():
    """
    查看購物車內容：顯示目前購物車所有商品。
    """
    if 'user_id' not in session:
        return redirect(url_for("login")), 302

    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, ticket_type, quantity, price, quantity * price as total
            FROM cart
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (session['user_id'],))
        cart_items = cur.fetchall()
        
        # 使用欄位名稱存取計算總金額
        total_amount = sum(item['total'] for item in cart_items)

    return render_template("readyshopping.html", cart_items=cart_items, total_amount=total_amount)

@app.route("/update_cart", methods=["POST"])
def update_cart():
    """
    更新購物車商品數量。
    """
    if 'user_id' not in session:
        return render_template("error.html", message="請先登入"), 401

    cart_id = request.form.get("cart_id")
    quantity = int(request.form.get("quantity", 1))

    with connect_db() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?",
            (quantity, cart_id, session['user_id'])
        )
        conn.commit()

    return redirect(url_for("readyshopping"))

@app.route("/remove_from_cart/<int:cart_id>")
def remove_from_cart(cart_id):
    """
    從購物車中刪除商品。
    """
    if 'user_id' not in session:
        return render_template("error.html", message="請先登入"), 401

    with connect_db() as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM cart WHERE id = ? AND user_id = ?",
            (cart_id, session['user_id'])
        )
        conn.commit()

    return redirect(url_for("readyshopping"))

@app.route("/logout")
def logout():
    """
    登出功能：清除 session 並回首頁。
    """
    session.clear()
    return redirect(url_for("index"))

@app.route("/checkout", methods=["POST"])
def checkout():
    """
    處理結帳請求，產生 QR Code 並建立訂單。
    """
    if 'user_id' not in session:
        return redirect(url_for("login")), 302

    with connect_db() as conn:
        c = conn.cursor()
        # 獲取購物車內容
        c.execute("""
            SELECT ticket_type, quantity, price
            FROM cart
            WHERE user_id = ?
        """, (session['user_id'],))
        cart_items = c.fetchall()

        qrcodes_info = []
        if cart_items:
            for item in cart_items:
                ticket_type, quantity, price = item
                total = quantity * price
                # 產生唯一專屬代碼，檢查是否存在
                while True:
                    qrcode_code = str(uuid.uuid4())
                    c.execute("SELECT 1 FROM orders WHERE qrcode_code = ?", (qrcode_code,))
                    if not c.fetchone():
                        break
                # 產生時間戳記
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # QR Code 內容
                qr_content = f"type:{ticket_type};qty:{quantity};price:{price};total:{total};time:{timestamp};code:{qrcode_code}"
                # 建立 qrcodes 資料夾
                qrcode_dir = os.path.join('static', 'images', 'qrcodes')
                if not os.path.exists(qrcode_dir):
                    os.makedirs(qrcode_dir)
                # QR Code 檔名
                qr_filename = f"{qrcode_code}.png"
                qr_path = os.path.join(qrcode_dir, qr_filename)
                # 產生 QR Code 圖片
                qr_img = qrcode.make(qr_content)
                qr_img.save(qr_path)
                # 存入訂單
                c.execute("""
                    INSERT INTO orders (user_id, ticket_type, quantity, price, total_amount, qrcode_code)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session['user_id'], ticket_type, quantity, price, total, qrcode_code))
                qrcodes_info.append({
                    'ticket_type': ticket_type,
                    'quantity': quantity,
                    'price': price,
                    'total': total,
                    'timestamp': timestamp,
                    'qrcode_code': qrcode_code,
                    'qr_filename': qr_filename
                })
            # 清空購物車
            c.execute("DELETE FROM cart WHERE user_id = ?", (session['user_id'],))
            conn.commit()
    # 導向 tickets.html 並顯示 QR Code
    return render_template("tickets.html", qrcodes_info=qrcodes_info)

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    """
    會員個人資料編輯：顯示與處理個人資料修改。
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    with connect_db() as conn:
        c = conn.cursor()
        if request.method == "POST":
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")
            
            # 檢查必填
            if not (username and email):
                return render_template("error.html", message="請輸入用戶名和電子郵件")
                
            # 檢查用戶名是否重複（排除自己）
            c.execute("SELECT iid FROM members WHERE username = ? AND iid != ?", (username, user_id))
            if c.fetchone():
                return render_template("error.html", message="用戶名已存在")
                
            # 更新資料
            if password:
                # 所有帳號都用雜湊儲存密碼
                hashed_password = generate_password_hash(password)
                c.execute("UPDATE members SET username=?, email=?, password=? WHERE iid=?", 
                         (username, email, hashed_password, user_id))
            else:
                c.execute("UPDATE members SET username=?, email=? WHERE iid=?", 
                         (username, email, user_id))
            
            conn.commit()
            session['username'] = username
            flash('個人資料更新成功', 'success')
        c.execute("SELECT username, email FROM members WHERE iid=?", (user_id,))
        user = c.fetchone()
    return render_template("edit_profile.html", username=user[0], email=user[1])

@app.route("/admin/orders")
def admin_orders():
    """
    僅限 admin 查看所有用戶購買紀錄。
    """
    if 'user_id' not in session or session.get('username') != 'admin':
        return render_template("error.html", message="無權限存取"), 403
    with connect_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT o.id, m.username, m.email, o.ticket_type, o.quantity, o.price, o.total_amount, o.created_at
            FROM orders o
            JOIN members m ON o.user_id = m.iid
            ORDER BY o.created_at DESC
        """)
        orders = c.fetchall()
    return render_template("admin_orders.html", orders=orders)

@app.route('/admin/users')
def admin_users():
    """
    僅限 admin 查看所有會員清單。
    """
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('error', message='無權限訪問此頁面')), 302
    
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM members')
        users = cursor.fetchall()
    return render_template('admin_users.html', users=users)

@app.route('/admin/delete_user/<username>')
def admin_delete_user(username):
    """
    僅限 admin 刪除指定會員（不可刪除 admin 本身）。
    """
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('error', message='無權限執行此操作')), 302
    
    if username == 'admin':
        flash('不能刪除管理員帳號', 'error')
        return redirect(url_for('admin_users')), 302
    
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cart WHERE user_id IN (SELECT iid FROM members WHERE username = ?)', (username,))
            cursor.execute('DELETE FROM orders WHERE user_id IN (SELECT iid FROM members WHERE username = ?)', (username,))
            cursor.execute('DELETE FROM members WHERE username = ?', (username,))
            conn.commit()
            flash('使用者已成功刪除', 'success')
    except Exception as e:
        flash('刪除使用者時發生錯誤', 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/add_user', methods=['POST'])
def admin_add_user():
    """
    僅限 admin 新增會員。
    """
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('error', message='無權限執行此操作')), 302
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM members WHERE username = ?', (username,))
            if cursor.fetchone():
                flash('使用者名稱已存在', 'error')
                return redirect(url_for('admin_users'))
            hashed_password = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO members (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password)
            )
            conn.commit()
            flash('使用者新增成功', 'success')
    except Exception as e:
        flash('新增使用者時發生錯誤', 'error')
    return redirect(url_for('admin_users'))


@app.route("/my_orders")
def my_orders():
    """
    會員查詢自己的訂單與 QR Code。
    """
    if 'user_id' not in session:
        return redirect(url_for('login')), 302
    user_id = session['user_id']
    with connect_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT ticket_type, quantity, price, total_amount, created_at, qrcode_code
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        )
        orders = c.fetchall()
    orders_info = []
    for order in orders:
        qr_filename = f"{order['qrcode_code']}.png" if order['qrcode_code'] else None
        orders_info.append({
            'ticket_type': order['ticket_type'],
            'quantity': order['quantity'],
            'price': order['price'],
            'total': order['total_amount'],
            'timestamp': order['created_at'],
            'qrcode_code': order['qrcode_code'],
            'qr_filename': qr_filename
        })
    return render_template("my_orders.html", orders_info=orders_info), 200

# 全域錯誤處理
@app.errorhandler(404)
def page_not_found(e):
    """
    404 錯誤處理：找不到頁面時顯示自訂錯誤訊息。
    """
    return render_template('error.html', message="找不到頁面 (404)"), 404

@app.errorhandler(500)
def internal_error(e):
    """
    500 錯誤處理：伺服器發生未預期錯誤時顯示自訂錯誤訊息。
    """
    return render_template('error.html', message="伺服器發生錯誤 (500)"), 500





