import feedparser
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "news.db")

RSS_FEEDS = [
    # 국내 - 경제
    {"url": "https://www.yonhapnewstv.co.kr/category/news/economy/feed/",     "source": "연합뉴스", "category": "경제"},
    {"url": "https://www.hankyung.com/feed/economy",                           "source": "한국경제", "category": "경제"},
    {"url": "https://www.mk.co.kr/rss/30100041/",                             "source": "매일경제", "category": "경제"},
    {"url": "https://www.moneytoday.co.kr/rss/S1N1A1/",                       "source": "머니투데이", "category": "경제"},
    {"url": "https://www.edaily.co.kr/rss/01400000.xml",                       "source": "이데일리", "category": "경제"},
    # 국내 - 주식
    {"url": "https://www.hankyung.com/feed/finance",                           "source": "한국경제", "category": "주식"},
    {"url": "https://www.mk.co.kr/rss/30200030/",                             "source": "매일경제", "category": "주식"},
    {"url": "https://www.moneytoday.co.kr/rss/S1N2A1/",                       "source": "머니투데이", "category": "주식"},
    {"url": "https://www.edaily.co.kr/rss/01600000.xml",                       "source": "이데일리", "category": "주식"},
    # 국내 - 부동산
    {"url": "https://www.hankyung.com/feed/realestate",                        "source": "한국경제", "category": "부동산"},
    {"url": "https://www.mk.co.kr/rss/30400011/",                             "source": "매일경제", "category": "부동산"},
    # 해외 - 경제/주식
    {"url": "https://feeds.reuters.com/reuters/businessNews",                  "source": "Reuters",  "category": "해외경제"},
    {"url": "https://feeds.bloomberg.com/markets/news.rss",                    "source": "Bloomberg","category": "해외경제"},
    {"url": "https://www.ft.com/rss/home/us",                                  "source": "FT",       "category": "해외경제"},
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