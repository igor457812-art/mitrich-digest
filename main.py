import os
import html
import time
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup


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
    ("Калязин и Кашин", "https://news.google.com/rss/search?q=Калязин+Кашин+новости&hl=ru&gl=RU&ceid=RU:ru"),
]


TELEGRAM_CHANNELS = [
    ("Калязин & Кашин: News", "https://t.me/s/pvk_69"),
]


BAD_WORDS = [
    "убил", "убийство", "убийца", "погиб", "погибли", "смерть", "умер",
    "труп", "насилие", "изнасил", "напал", "нападение", "драка",
    "авария", "дтп", "сбил", "пожар", "взрыв", "теракт",
    "война", "ракета", "обстрел", "бпла", "дрон", "фронт",
    "суд", "приговор", "арест", "задержан", "уголовн",
    "коррупц", "мошенник", "штраф", "воровств", "украл", "краж",
    "грязная вода", "плохая вода", "канализация", "отключение воды",
    "навальный", "санкции", "трамп", "иран", "украин",
]


GOOD_WORDS = [
    "каш", "каляз", "твер", "город", "музей", "выставка", "фестиваль",
    "праздник", "история", "археолог", "нашли", "обнаружили", "раскоп",
    "монет", "наука", "учёные", "ученые", "космос", "планет", "животн",
    "необыч", "редк", "курьёз", "курьез", "интересн",
    "дети", "школ", "учитель", "культура", "театр", "книга",
    "добровол", "помог", "открыли", "создали", "изобрели",
    "елк", "ёлк", "площад", "дорог", "ремонт", "золотое кольцо",
    "туризм", "турист", "благоустр", "конкурс",
]


def clean_title(title):
    return " ".join(title.replace("\n", " ").split())


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
        score += 8

    if "каляз" in text:
        score += 4

    if "твер" in text:
        score += 3

    if "монет" in text or "археолог" in text or "история" in text:
        score += 4

    if "золотое кольцо" in text or "туризм" in text:
        score += 4

    if "наука" in source.lower() or "naked science" in source.lower() or "хайтек" in source.lower():
        score += 2

    return score


def get_telegram_news():
    items = []

    for source_name, url in TELEGRAM_CHANNELS:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            messages = soup.select(".tgme_widget_message_text")

            for msg in messages[-12:]:
                text = msg.get_text(" ", strip=True)
                text = clean_title(text)

                if not text or len(text) < 40:
                    continue

                items.append({
                    "source": source_name,
                    "title": text[:250],
                    "link": url,
                })

        except Exception as error:
            print(f"Ошибка Telegram-канала {source_name}: {error}")

    return items


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

    tg_items = get_telegram_news()

    for item in tg_items:
        title = item["title"]
        title_key = title.lower()

        if title_key in seen_titles:
            continue

        seen_titles.add(title_key)

        if is_bad(title):
            continue

        score = score_news(title, item["source"])

        if score <= 0:
            continue

        items.append({
            "source": item["source"],
            "title": title,
            "link": item["link"],
            "score": score,
        })

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
