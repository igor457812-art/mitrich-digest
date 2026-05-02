import feedparser
import requests
from datetime import datetime

BOT_TOKEN = "8676689810:AAHqnbC2_fpsGwhfRqHAlKbv61G3XhYricw"
CHAT_ID = "511177080"

FEEDS = [
    ("Лента.ру", "https://lenta.ru/rss"),
    ("РИА Новости", "https://ria.ru/export/rss2/index.xml"),
    ("Газета.ру", "https://www.gazeta.ru/export/rss/first.xml"),
    ("Meduza", "https://meduza.io/rss/all"),
]

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

def get_news():
    lines = []
    lines.append(f"☕ <b>Дайджест Митрича</b> — {datetime.now().strftime('%d.%m.%Y')}\n")
    for name, url in FEEDS:
        feed = feedparser.parse(url)
        entries = feed.entries[:2]
        if entries:
            lines.append(f"\n<b>{name}:</b>")
            for e in entries:
                lines.append(f"• {e.title}")
    return "\n".join(lines)

if __name__ == "__main__":
    news = get_news()
    send_message(news)
