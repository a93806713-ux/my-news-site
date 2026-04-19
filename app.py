from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import yfinance as yf

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "news.db")

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title    TEXT NOT NULL,
            link     TEXT,
            source   TEXT,
            category TEXT,
            date     TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedbacks (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT,
            email     TEXT,
            message   TEXT NOT NULL,
            date      TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_articles(category=None):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if category:
        c.execute("SELECT id, title, link, source, category, date FROM articles WHERE category=? ORDER BY date DESC LIMIT 20", (category,))
    else:
        c.execute("SELECT id, title, link, source, category, date FROM articles ORDER BY date DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "link": r[2], "source": r[3], "category": r[4], "date": r[5]} for r in rows]

@app.route("/")
def index():
    articles = get_articles()
    return render_template("index.html", articles=articles)

@app.route("/news/<category>")
def news_category(category):
    articles = get_articles(category)
    return render_template("news.html", articles=articles, category=category)

@app.route("/stock")
def stock():
    return render_template("stock.html")

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        name    = request.form.get("name", "익명")
        email   = request.form.get("email", "")
        message = request.form.get("message", "")
        if message:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            from datetime import datetime
            c.execute("INSERT INTO feedbacks (name, email, message, date) VALUES (?,?,?,?)",
                      (name, email, message, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()
        return render_template("feedback.html", success=True)
    return render_template("feedback.html", success=False)

@app.route("/api/market")
def market_data():
    tickers = {
        "코스피": "^KS11",
        "코스닥": "^KQ11",
        "나스닥": "^IXIC",
        "S&P500": "^GSPC",
        "비트코인": "BTC-USD",
        "환율(원/달러)": "KRW=X",
        "금": "GC=F",
        "유가(WTI)": "CL=F",
    }
    result = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                current = hist["Close"].iloc[-1]
                previous = hist["Close"].iloc[-2]
                change = current - previous
                change_pct = (change / previous) * 100
                result[name] = {
                    "price": round(current, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                }
        except:
            result[name] = {"price": 0, "change": 0, "change_pct": 0}
    return jsonify(result)

@app.route("/api/stock/<ticker>")
def stock_data(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        info = t.info
        prices = [round(p, 2) for p in hist["Close"].tolist()]
        dates  = [str(d.date()) for d in hist.index]
        return jsonify({
            "name": info.get("longName", ticker),
            "price": round(hist["Close"].iloc[-1], 2),
            "currency": info.get("currency", "USD"),
            "prices": prices,
            "dates": dates,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)