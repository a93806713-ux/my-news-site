from flask import Flask, render_template
import sqlite3
import os

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

init_db()

@app.route("/")
def index():
    articles = get_articles()
    return render_template("index.html", articles=articles)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)