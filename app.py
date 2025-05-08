from flask import Flask,render_template

app = Flask(__name__)

@app.route("/")
def show_login_page():
    """顯示登入畫面"""
    return render_template("login.html")

if __name__ == "__main__":
    show_login_page()

