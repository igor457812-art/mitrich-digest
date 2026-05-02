import feedparser
import requests
from datetime import datetime

BOT_TOKEN = "8676689810:AAHqnbC2_fpsGwhfRqHAlKbv61G3XhYricw"
CHAT_ID = "511177080"

FEEDS = [
    ("Афанасий — Кашин", "https://www.afanasy.biz/rss/novosti-kashina"),
    ("ТИА Тверь", "https://tvernews.ru/rss/"),
    ("Твериград", "https://tvergrad.ru/feed/"),
    ("Кашин — официальный", "https://www.kashin.info/rss/"),
]

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

def get_news():
    lines = []
    lines.append(f"☕ <b>Дайджест Митрича</b> — {datetime.now().strftime('%d.%m.%Y')}\n")
    for name, url in FEEDS:
        feed = feedparser.parse(url)
        count = len(feed.entries)
        lines.append(f"\n<b>{name}:</b> найдено {count} новостей")
        for e in feed.entries[:3]:
            lines.append(f"• {e.title}")
    return "\n".join(lines)

if __name__ == "__main__":
    news = get_news()
    send_message(news)
