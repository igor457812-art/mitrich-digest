import os
import html
import time
from datetime import datetime

import feedparser
import requests


BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


FEEDS = [
    ("Лента.ру", "https://lenta.ru/rss"),
    ("РИА Новости", "https://ria.ru/export/rss2/index.xml"),
    ("Газета.ру", "https://www.gazeta.ru/export/rss/first.xml"),
    ("Коммерсант", "https://www.kommersant.ru/RSS/main.xml"),
    ("Российская газета", "https://rg.ru/xml/index.xml"),
    ("РБК", "https://rss.rbk.ru/v1/get/all"),

    ("Лента — Наука", "https://lenta.ru/rss/news/science"),
    ("РИА — Наука", "https://ria.ru/export/rss2/science/index.xml"),
    ("Naked Science", "https://naked-science.ru/feed"),
    ("Хайтек", "https://hightech.fm/feed"),

    ("Кашин — новости", "https://news.google.com/rss/search?q=Кашин+Тверская+область&hl=ru&gl=RU&ceid=RU:ru"),
    ("Тверь — новости", "https://news.google.com/rss/search?q=Тверь+новости&hl=ru&gl=RU&ceid=RU:ru"),
    ("Малые города", "https://news.google.com/rss/search?q=малый+город+Россия+событие&hl=ru&gl=RU&ceid=RU:ru"),
    ("Курьёзы России", "https://news.google.com/rss/search?q=необычное+Россия+курьёз&hl=ru&gl=RU&ceid=RU:ru"),
]


BAD_WORDS = [
    "убил", "убийство", "убийца", "погиб", "погибли", "смерть", "умер",
    "труп", "насилие", "изнасил", "напал", "нападение", "драка",
    "авария", "дтп", "сбил", "пожар", "взрыв", "теракт",
    "война", "ракета", "обстрел", "бпла", "дрон", "фронт",
    "суд", "приговор", "арест", "задержан", "уголовн",
    "коррупц", "мошенник", "штраф",
    "грязная вода", "плохая вода", "канализация", "отключение воды",
    "навальный", "санкции", "трамп", "иран", "украин",
]


GOOD_WORDS = [
    "каш", "твер", "город", "музей", "выставка", "фестиваль", "праздник",
    "история", "археолог", "нашли", "обнаружили", "раскоп", "монет",
    "наука", "учёные", "ученые", "космос", "планет", "животн",
    "необыч", "редк", "курьёз", "курьез", "интересн",
    "дети", "школ", "учитель", "культура", "театр", "книга",
    "добровол", "помог", "открыли", "создали", "изобрели",
]


def is_bad(title):
    text = title.lower()
    return any(word in text for word in BAD_WORDS)


def score_news(title, source):
    text = f"{title} {source}".lower()
    score = 0

    for word in GOOD_WORDS:
        if word in text:
            score += 2

    if "каш" in text:
        score += 6

    if "твер" in text:
        score += 3

    if "монет" in text or "археолог" in text or "история" in text:
        score += 4

    if "наука" in source.lower() or "naked science" in source.lower() or "хайтек" in source.lower():
        score += 2

    return score


def clean_title(title):
    return " ".join(title.replace("\n", " ").split())


def collect_news():
    items = []
    seen_titles = set()

    for source_name, feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:8]:
                title = clean_title(getattr(entry, "title", ""))
                link = getattr(entry, "link", "")

                if not title or not link:
                    continue

                title_key = title.lower()

                if title_key in seen_titles:
                    continue

                seen_titles.add(title_key)

                if is_bad(title):
                    continue

                score = score_news(title, source_name)

                if score <= 0:
                    continue

                items.append({
                    "source": source_name,
                    "title": title,
                    "link": link,
                    "score": score,
                })

            time.sleep(0.5)

        except Exception as error:
            print(f"Ошибка источника {source_name}: {error}")

    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:7]


def build_message(items):
    today = datetime.now().strftime("%d.%m.%Y")

    if not items:
        return (
            f"☕ <b>Дайджест Митрича — {today}</b>\n\n"
            "Сегодня Митрич ничего приличного для чтения не нашёл. "
            "В лентах шумно, а нам такое в избу не надо."
        )

    lines = [
        f"☕ <b>Дайджест Митрича — {today}</b>",
        "",
        "Новости без грязи и лишней тревоги:",
        "",
    ]

    for item in items:
        title = html.escape(item["title"])
        link = html.escape(item["link"])
        source = html.escape(item["source"])
        lines.append(f"• <a href=\"{link}\">{title}</a>")
        lines.append(f"  <i>{source}</i>")
        lines.append("")

    return "\n".join(lines)


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    response.raise_for_status()


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("Не задан BOT_TOKEN")

    if not CHAT_ID:
        raise ValueError("Не задан CHAT_ID")

    news_items = collect_news()
    message = build_message(news_items)
    send_message(message)
