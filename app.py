import sqlite3
from flask import Flask, redirect, render_template, request, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'secret_key'


def init_db():
    """初始化資料庫，建立 members 表並插入初始資料"""
    with sqlite3.connect("membership.db") as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS members (
                        iid INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        email TEXT NOT NULL,
                        password TEXT NOT NULL
                    )""")
        c.execute(
            "INSERT OR IGNORE INTO members (username, email, password) VALUES (?, ?, ?)",
            ("admin", "admin@gmail.com", "123"),
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
        
        # 創建訂單記錄表格
        c.execute("""CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        ticket_type TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price REAL NOT NULL,
                        total_amount REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES members (iid)
                    )""")
        
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
    """首頁"""
    return render_template("index.html")


@app.route("/about")
def about():
    """關於我們"""
    return render_template("about.html")


@app.route("/tickets")
def tickets():
    """線上購票"""
    return render_template("tickets.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """處理註冊請求"""
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        

        # 檢查必填欄位
        if not (username and email and password):
            return render_template("error.html", message="請輸入用戶名、電子郵件和密碼")

        # 檢查用戶名是否已存在
        conn = sqlite3.connect("membership.db")
        c = conn.cursor()
        c.execute("SELECT username FROM members WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return render_template("error.html", message="用戶名已存在")

        # 儲存資料
        c.execute(
            "INSERT INTO members (username, email, password) "
            "VALUES (?, ?, ?)",
            (username, email, password),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """處理登入請求"""
    if request.method == "POST":
        account = request.form.get("account")
        password = request.form.get("password")

        # 檢查必填欄位
        if not (account and password):
            return render_template("error.html", message="請輸入帳號和密碼")

        # 驗證帳號和密碼
        conn = sqlite3.connect("membership.db")
        c = conn.cursor()
        c.execute(
            "SELECT username, iid FROM members WHERE (username = ? OR email = ?) AND password = ?",
            (account,account, password),
        )
        result = c.fetchone()
        conn.close()

        if result:
            username, iid = result
            session['user_id'] = iid
            session['username'] = username
            return render_template("index.html", username=username, iid=iid)
        return render_template("error.html", message="帳號或密碼錯誤")

    return render_template("login.html")

@app.route("/emptyshopping")
def emptyshopping():
    """空購物車"""
    return render_template("emptyshopping.html")


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    """添加商品到購物車"""
    if 'user_id' not in session:
        return jsonify({"error": "請先登入"}), 401
    
    ticket_type = request.form.get("ticket_type")
    quantity = int(request.form.get("quantity", 1))
    price = float(request.form.get("price", 0))
    
    if not all([ticket_type, quantity, price]):
        return jsonify({"error": "缺少必要資訊"}), 400
    
    conn = sqlite3.connect("membership.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO cart (user_id, ticket_type, quantity, price) VALUES (?, ?, ?, ?)",
        (session['user_id'], ticket_type, quantity, price)
    )
    conn.commit()
    conn.close()
    
    return jsonify({"redirect": url_for("readyshopping")})

@app.route("/readyshopping")
def readyshopping():
    """查看購物車內容"""
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("membership.db")
    c = conn.cursor()
    c.execute("""
        SELECT id, ticket_type, quantity, price, quantity * price as total
        FROM cart
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session['user_id'],))
    cart_items = c.fetchall()
    
    # 計算總金額
    total_amount = sum(item[4] for item in cart_items)
    
    conn.close()
    return render_template("readyshopping.html", cart_items=cart_items, total_amount=total_amount)

@app.route("/update_cart", methods=["POST"])
def update_cart():
    """更新購物車商品數量"""
    if 'user_id' not in session:
        return render_template("error.html", message="請先登入")
    
    cart_id = request.form.get("cart_id")
    quantity = int(request.form.get("quantity", 1))
    
    conn = sqlite3.connect("membership.db")
    c = conn.cursor()
    c.execute(
        "UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?",
        (quantity, cart_id, session['user_id'])
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for("readyshopping"))

@app.route("/remove_from_cart/<int:cart_id>")
def remove_from_cart(cart_id):
    """從購物車中刪除商品"""
    if 'user_id' not in session:
        return render_template("error.html", message="請先登入")
    
    conn = sqlite3.connect("membership.db")
    c = conn.cursor()
    c.execute(
        "DELETE FROM cart WHERE id = ? AND user_id = ?",
        (cart_id, session['user_id'])
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for("readyshopping"))

@app.route("/logout")
def logout():
    """登出功能"""
    session.clear()
    return redirect(url_for("index"))

@app.route("/checkout", methods=["POST"])
def checkout():
    """處理結帳請求"""
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("membership.db")
    c = conn.cursor()
    
    # 獲取購物車內容
    c.execute("""
        SELECT ticket_type, quantity, price
        FROM cart
        WHERE user_id = ?
    """, (session['user_id'],))
    cart_items = c.fetchall()
    
    if cart_items:
        # 將購物車內容複製到訂單記錄
        for item in cart_items:
            ticket_type, quantity, price = item
            total = quantity * price
            c.execute("""
                INSERT INTO orders (user_id, ticket_type, quantity, price, total_amount)
                VALUES (?, ?, ?, ?, ?)
            """, (session['user_id'], ticket_type, quantity, price, total))
        
        # 清空購物車
        c.execute("DELETE FROM cart WHERE user_id = ?", (session['user_id'],))
        conn.commit()
    
    conn.close()
    return redirect(url_for("index"))

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = sqlite3.connect("membership.db")
    c = conn.cursor()
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        # 檢查必填
        if not (username and email):
            conn.close()
            return render_template("error.html", message="請輸入用戶名和電子郵件")
        # 檢查用戶名是否重複（排除自己）
        c.execute("SELECT iid FROM members WHERE username = ? AND iid != ?", (username, user_id))
        if c.fetchone():
            conn.close()
            return render_template("error.html", message="用戶名已存在")
        # 更新資料
        if password:
            c.execute("UPDATE members SET username=?, email=?, password=? WHERE iid=?", (username, email, password, user_id))
        else:
            c.execute("UPDATE members SET username=?, email=? WHERE iid=?", (username, email, user_id))
        conn.commit()
        session['username'] = username
        conn.close()
        return redirect(url_for('edit_profile'))
    # GET: 查詢會員資料
    c.execute("SELECT username, email FROM members WHERE iid=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return render_template("edit_profile.html", username=user[0], email=user[1])

@app.route("/admin/orders")
def admin_orders():
    """僅限admin查看所有用戶購買紀錄"""
    if 'user_id' not in session or session.get('username') != 'admin':
        return render_template("error.html", message="無權限存取")
    conn = sqlite3.connect("membership.db")
    c = conn.cursor()
    c.execute("""
        SELECT o.id, m.username, m.email, o.ticket_type, o.quantity, o.price, o.total_amount, o.created_at
        FROM orders o
        JOIN members m ON o.user_id = m.iid
        ORDER BY o.created_at DESC
    """)
    orders = c.fetchall()
    conn.close()
    return render_template("admin_orders.html", orders=orders)





