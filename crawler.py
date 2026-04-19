import feedparser
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "news.db")

RSS_FEEDS = [
    # 경제
    {"url": "https://www.hankyung.com/feed/economy",       "source": "한국경제", "category": "경제"},
    {"url": "https://feeds.feedburner.com/khan/rss/business", "source": "경향신문", "category": "경제"},
    # 주식
    {"url": "https://www.hankyung.com/feed/stock",         "source": "한국경제", "category": "주식"},
    # 부동산
    {"url": "https://www.hankyung.com/feed/realestate",    "source": "한국경제", "category": "부동산"},
    {"url": "https://land.naver.com/news/newsRss.naver",   "source": "네이버부동산", "category": "부동산"},
]

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

def crawl():
    init_db()
    print(f"크롤링 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    total = 0
    for feed_info in RSS_FEEDS:
        print(f"[{feed_info['source']}] 수집 중...")
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries[:20]:
            title = entry.get("title", "제목없음")
            link  = entry.get("link", "#")
            date  = entry.get("published", datetime.now().strftime("%Y-%m-%d"))[:10]
            c.execute("SELECT id FROM articles WHERE link = ?", (link,))
            if c.fetchone() is None:
                c.execute(
                    "INSERT INTO articles (title, link, source, category, date) VALUES (?,?,?,?,?)",
                    (title, link, feed_info["source"], feed_info["category"], date)
                )
                total += 1
    conn.commit()
    conn.close()
    print(f"크롤링 완료 - 새 기사 {total}개 추가")

if __name__ == "__main__":
    crawl()