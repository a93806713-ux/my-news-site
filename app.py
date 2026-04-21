from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import yfinance as yf
import anthropic
import threading
import schedule
import time
from datetime import datetime, timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "news.db")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 보안 - Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["300 per day", "60 per hour"]
)

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
    c.execute('''
        CREATE TABLE IF NOT EXISTS summaries (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            type     TEXT,
            content  TEXT,
            date     TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_articles(category=None):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if category:
        c.execute("""
            SELECT id, title, link, source, category, date
            FROM articles WHERE category=?
            ORDER BY date DESC LIMIT 20
        """, (category,))
    else:
        c.execute("""
            SELECT id, title, link, source, category, date FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY date DESC) rn
                FROM articles WHERE category IN ('경제','주식','부동산')
            ) WHERE rn <= 20
            ORDER BY date DESC
        """)
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "link": r[2], "source": r[3], "category": r[4], "date": r[5]} for r in rows]

def get_summary(summary_type):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT content, date FROM summaries WHERE type=? ORDER BY id DESC LIMIT 1", (summary_type,))
    row = c.fetchone()
    conn.close()
    return row if row else None

def generate_summary(summary_type):
    if not ANTHROPIC_API_KEY:
        return "API 키가 설정되지 않았습니다."

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    if summary_type == "today":
        c.execute("SELECT title FROM articles ORDER BY id DESC LIMIT 30")
        period = "오늘"
    else:
        c.execute("SELECT title FROM articles ORDER BY id DESC LIMIT 80")
        period = "저번주"

    titles = [row[0] for row in c.fetchall()]
    conn.close()

    if summary_type == "week":
        titles = titles[30:]

    if not titles:
        return f"{period} 기사가 없습니다."

    titles_text = "\n".join([f"- {t}" for t in titles])

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""다음은 {period} 주요 경제/주식/부동산 기사 제목들입니다.
이 기사들을 바탕으로 {period}의 주요 경제 동향을 3~5줄로 간결하게 요약해주세요.
핵심 키워드와 트렌드 위주로 작성해주세요.

기사 목록:
{titles_text}"""
        }]
    )
    summary = message.content[0].text

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO summaries (type, content, date) VALUES (?,?,?)",
              (summary_type, summary, today))
    conn.commit()
    conn.close()

    return summary

# 자동 크롤링 스케줄러
def run_crawler():
    try:
        from crawler import crawl
        print(f"자동 크롤링 실행 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        crawl()
    except Exception as e:
        print(f"크롤링 오류: {e}")

def start_scheduler():
    from crawler import crawl
    schedule.every(30).minutes.do(crawl)
    schedule.every().day.at("09:00").do(auto_post_instagram)
    while True:
        schedule.run_pending()
        time.sleep(60)

def auto_post_instagram():
    """매일 오전 9시 인스타 자동 포스팅"""
    try:
        from instagram_poster import post_to_instagram, generate_caption, create_post_image, upload_to_imgbb
        import yfinance as yf

        # 시세 데이터 수집
        tickers = {
            "코스피":   "^KS11",
            "나스닥":   "^IXIC",
            "비트코인": "BTC-USD",
            "환율":     "KRW=X",
        }
        market = {}
        for name, ticker in tickers.items():
            try:
                t    = yf.Ticker(ticker)
                hist = t.history(period="2d")
                if len(hist) >= 2:
                    current    = hist["Close"].iloc[-1]
                    previous   = hist["Close"].iloc[-2]
                    change     = current - previous
                    change_pct = round((change / previous) * 100, 2)
                    market[name] = {
                        "price":      round(current, 2),
                        "change":     change,
                        "change_pct": change_pct
                    }
            except:
                pass

        # AI 요약 생성
        summary = generate_summary("today")

        # 이미지 생성 및 업로드
        img       = create_post_image(summary, market)
        image_url = upload_to_imgbb(img)

        if not image_url:
            print("이미지 업로드 실패로 포스팅 중단")
            return

        # 캡션 생성 및 포스팅
        caption = generate_caption(summary, market)
        post_to_instagram(image_url, caption)
        print("인스타 자동 포스팅 완료!")

    except Exception as e:
        print(f"인스타 포스팅 오류: {e}")

@app.route("/")
def index():
    articles      = get_articles()
    today_summary = get_summary("today")
    week_summary  = get_summary("week")
    return render_template("index.html",
        articles=articles,
        today_summary=today_summary[0] if today_summary else None,
        week_summary=week_summary[0] if week_summary else None,
    )

@app.route("/api/summary/<summary_type>")
@limiter.limit("10 per hour")
def api_summary(summary_type):
    summary = generate_summary(summary_type)
    return jsonify({"summary": summary})

@app.route("/news/<category>")
def news_category(category):
    articles = get_articles(category)
    return render_template("news.html", articles=articles, category=category)

@app.route("/stock")
def stock():
    return render_template("stock.html")

@app.route("/realestate")
def realestate():
    articles = get_articles("부동산")
    return render_template("realestate.html", articles=articles)

@app.route("/feedback", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def feedback():
    if request.method == "POST":
        name    = request.form.get("name", "익명")
        email   = request.form.get("email", "")
        message = request.form.get("message", "")
        if message:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("INSERT INTO feedbacks (name, email, message, date) VALUES (?,?,?,?)",
                      (name, email, message, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()
        return render_template("feedback.html", success=True)
    return render_template("feedback.html", success=False)

@app.route("/api/market")
@limiter.limit("30 per hour")
def market_data():
    tickers = {
        "코스피":      "^KS11",
        "코스닥":      "^KQ11",
        "나스닥":      "^IXIC",
        "S&P500":      "^GSPC",
        "비트코인":    "BTC-USD",
        "환율(원/달러)": "KRW=X",
        "금":          "GC=F",
        "유가(WTI)":   "CL=F",
    }
    result = {}
    for name, ticker in tickers.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d")  # 2d → 5d 로 변경 (주말/공휴일 대비)
            hist = hist.dropna()            # NaN 제거
            if len(hist) >= 2:
                current    = hist["Close"].iloc[-1]
                previous   = hist["Close"].iloc[-2]
                change     = current - previous
                change_pct = (change / previous) * 100
                result[name] = {
                    "price":      round(current, 2),
                    "change":     round(change, 2),
                    "change_pct": round(change_pct, 2),
                }
            elif len(hist) == 1:
                current = hist["Close"].iloc[-1]
                result[name] = {
                    "price":      round(current, 2),
                    "change":     0,
                    "change_pct": 0,
                }
        except Exception as e:
            print(f"시세 오류 {name}: {e}")
            result[name] = {"price": 0, "change": 0, "change_pct": 0}
    return jsonify(result)

@app.route("/api/stock/<ticker>")
@limiter.limit("30 per hour")
def stock_data(ticker):
    try:
        period = request.args.get("period", "1mo")
        candle = request.args.get("candle", "daily")
        t      = yf.Ticker(ticker)
        info   = t.info

        # 봉 타입에 따라 interval 설정
        if candle == "weekly":
            interval = "1wk"
        elif candle == "monthly":
            interval = "1mo"
        else:
            interval = "1d"

        hist   = t.history(period=period, interval=interval)
        prices = [round(p, 2) for p in hist["Close"].tolist()]
        dates  = [str(d.date()) for d in hist.index]

        # OHLC 데이터 (봉 그래프용)
        ohlc = []
        for i, row in hist.iterrows():
            ohlc.append({
                "date":  str(i.date()),
                "open":  round(row["Open"], 2),
                "high":  round(row["High"], 2),
                "low":   round(row["Low"],  2),
                "close": round(row["Close"],2),
            })

        return jsonify({
            "name":     info.get("longName", ticker),
            "price":    round(hist["Close"].iloc[-1], 2),
            "currency": info.get("currency", "USD"),
            "prices":   prices,
            "dates":    dates,
            "ohlc":     ohlc,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 서버 시작 시 초기화
init_db()
run_crawler()

# 백그라운드 스케줄러 시작
scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()

# 관리자 페이지
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            feedbacks = c.execute("SELECT id, name, email, message, date FROM feedbacks ORDER BY date DESC").fetchall()
            feedbacks = [{"id": r[0], "name": r[1], "email": r[2], "message": r[3], "date": r[4]} for r in feedbacks]
            conn.close()
            return render_template("admin.html", feedbacks=feedbacks, logged_in=True)
        else:
            return render_template("admin.html", feedbacks=[], logged_in=False, error="비밀번호가 틀렸어요!")
    return render_template("admin.html", feedbacks=[], logged_in=False, error=None)

@app.route("/api/test_instagram")
def test_instagram():
    auto_post_instagram()
    return jsonify({"status": "포스팅 시도 완료! 터미널 확인하세요."})

@app.route("/api/search_ticker")
@limiter.limit("30 per hour")
def search_ticker():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    try:
        from deep_translator import GoogleTranslator

        # 한글 포함 여부 확인 후 영어로 번역
        def is_korean(text):
            return any('\uac00' <= c <= '\ud7a3' for c in text)

        search_query = query
        if is_korean(query):
            search_query = GoogleTranslator(source='ko', target='en').translate(query)
            print(f"번역: {query} → {search_query}")

        results = yf.Search(search_query, max_results=8)
        data    = []
        for q in results.quotes[:8]:
            symbol = q.get("symbol", "")
            name   = q.get("longname") or q.get("shortname", "")
            if symbol and name:
                data.append({
                    "symbol":   symbol,
                    "name":     name,
                    "exchange": q.get("exchDisp", q.get("exchange", "")),
                })
        return jsonify(data)
    except Exception as e:
        print(f"검색 오류: {e}")
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)