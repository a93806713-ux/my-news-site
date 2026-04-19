from flask import Flask, render_template
import sqlite3
import os
import threading
import schedule
import time

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
    conn.commit()
    conn.close()

def get_articles():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, title, link, source, category, date FROM articles ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    articles = []
    for row in rows:
        articles.append({
            "id":       row[0],
            "title":    row[1],
            "link":     row[2],
            "source":   row[3],
            "category": row[4],
            "date":     row[5],
        })
    return articles

def run_crawler():
    """크롤러 자동 실행"""
    print("자동 크롤링 시작...")
    import feedparser
    from datetime import datetime

    RSS_FEEDS = [
        {"url": "https://www.hankyung.com/feed/economy", "source": "한국경제", "category": "경제"},
        {"url": "https://www.hankyung.com/feed/stock",   "source": "한국경제", "category": "주식"},
    ]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    count = 0
    for feed_info in RSS_FEEDS:
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries[:10]:
            title = entry.get("title", "제목없음")
            link  = entry.get("link", "#")
            date  = entry.get("published", datetime.now().strftime("%Y-%m-%d"))[:10]
            c.execute("SELECT id FROM articles WHERE link = ?", (link,))
            if c.fetchone() is None:
                c.execute(
                    "INSERT INTO articles (title, link, source, category, date) VALUES (?,?,?,?,?)",
                    (title, link, feed_info["source"], feed_info["category"], date)
                )
                count += 1
    conn.commit()
    conn.close()
    print(f"자동 크롤링 완료 - 새 기사 {count}개 추가")

def start_scheduler():
    """백그라운드 스케줄러 실행"""
    schedule.every(30).minutes.do(run_crawler)  # 30분마다 실행
    while True:
        schedule.run_pending()
        time.sleep(60)

@app.route("/")
def index():
    articles = get_articles()
    return render_template("index.html", articles=articles)

if __name__ == "__main__":
    init_db()

    # 서버 시작할 때 크롤러 1회 즉시 실행
    run_crawler()

    # 백그라운드에서 스케줄러 실행
    t = threading.Thread(target=start_scheduler, daemon=True)
    t.start()

    app.run(debug=False)  # 스케줄러 때문에 debug=False