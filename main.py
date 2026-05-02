import feedparser
import requests
from datetime import datetime

BOT_TOKEN = "8676689810:AAHqnbC2_fpsGwhfRqHAlKbv61G3XhYricw"
CHAT_ID = "511177080"

FEEDS = [
    # Федеральные
    ("Лента.ру", "https://lenta.ru/rss"),
    ("РИА Новости", "https://ria.ru/export/rss2/index.xml"),
    ("Газета.ру", "https://www.gazeta.ru/export/rss/first.xml"),
    ("ТАСС", "https://tass.com/rss/v2.xml"),
    ("Коммерсант", "https://www.kommersant.ru/RSS/main.xml"),
    ("МК", "https://www.mk.ru/rss/index.xml"),
    ("Российская газета", "https://rg.ru/xml/index.xml"),
    ("Meduza", "https://meduza.io/rss/all"),
    # Курьёзы и необычное
    ("Лента — Россия", "https://lenta.ru/rss/news/russia"),
    ("Лента — Наука", "https://lenta.ru/rss/news/science"),
    ("Лента — Общество", "https://lenta.ru/rss/news/society"),
    ("РИА — Общество", "https://ria.ru/export/rss2/society/index.xml"),
    ("РИА — Наука", "https://ria.ru/export/rss2/science/index.xml"),
    ("РИА — Регионы", "https://ria.ru/export/rss2/region_other/index.xml"),
    ("ТАСС — Общество", "https://tass.com/rss/v2.xml"),
    ("Naked Science", "https://naked-science.ru/feed"),
    ("Хайтек", "https://hightech.fm/feed"),
    # Тверь и Кашин
    ("Кашин — новости", "https://news.google.com/rss/search?q=Кашин+Тверская+область&hl=ru&gl=RU&ceid=RU:ru"),
    ("Тверь — новости", "https://news.google.com/rss/search?q=Тверь+новости&hl=ru&gl=RU&ceid=RU:ru"),
    ("Кашин — события", "https://news.google.com/rss/search?q=Кашин+город+событие&hl=ru&gl=RU&ceid=RU:ru"),
    # Необычное по России
    ("Курьёзы России", "https://news.google.com/rss/search?q=необычное+Россия+курьёз&hl=ru&gl=RU&ceid=RU:ru"),
    ("Странные законы", "https://news.google.com/rss/search?q=Госдума+предложила+запретить&hl=ru&gl=RU&ceid=RU:ru"),
    ("Провинция России", "https://news.google.com/rss/search?q=малый+город+Россия+событие&hl=ru&gl=RU&ceid=RU:ru"),
]

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

def get_news():
    lines = []
    lines.append(f"☕ <b>Дайджест Митрича</b> — {datetime.now().strftime('%d.%m.%Y')}\n")
    for name, url in FEEDS:
        feed = feedparser.parse(url)
        entries = feed.entries[:3]
        if entries:
            lines.append(f"\n<b>{name}:</b>")
            for e in entries:
                lines.append(f"• {e.title}")
    return "\n".join(lines)

if __name__ == "__main__":
    news = get_news()
    send_message(news)
