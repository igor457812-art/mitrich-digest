import os
import html
import time
import random
from datetime import datetime, timedelta

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
    "наркот", "алкогол", "пьяный", "избил", "розыск",
]


SEASON_BAD_MONTHS = {
    1: [],
    2: [],
    3: ["ёлка", "елка", "дед мороз", "новый год"],
    4: ["ёлка", "елка", "дед мороз", "новый год"],
    5: ["ёлка", "елка", "дед мороз", "новый год"],
    6: ["ёлка", "елка", "дед мороз", "новый год"],
    7: ["ёлка", "елка", "дед мороз", "новый год"],
    8: ["ёлка", "елка", "дед мороз", "новый год"],
    9: ["ёлка", "елка", "дед мороз", "новый год"],
    10: [],
    11: [],
    12: [],
}


GOOD_WORDS = [
    "каш", "каляз", "твер", "город", "музей", "выставка", "фестиваль",
    "праздник", "история", "археолог", "нашли", "обнаружили", "раскоп",
    "монет", "наука", "учёные", "ученые", "космос", "планет", "животн",
    "необыч", "редк", "курьёз", "курьез", "интересн",
    "дети", "школ", "учитель", "культура", "театр", "книга",
    "добровол", "помог", "открыли", "создали", "изобрели",
    "площад", "дорог", "ремонт", "золотое кольцо",
    "туризм", "турист", "благоустр", "конкурс", "природ", "река",
]


INTRO_VARIANTS = [
    "Покопался тут немного — вот что интересного вылезло.",
    "Посмотрел, что там в новостях. Отобрал без истерики.",
    "Пошуршал по интернету. Есть пара любопытных вещей.",
    "Новости сегодня разные, но кое-что нормальное нашлось.",
    "Собрал для вас то, что можно читать без валерьянки.",
    "Митрич полистал ленты и отмёл лишний шум.",
    "Вот что сегодня попалось из более-менее человеческого.",
]


ENDING_VARIANTS = [
    "Вот такой сегодня улов.",
    "Остальное — шум, его в печку.",
    "Если коротко — день без сенсаций, но посмотреть есть на что.",
    "На этом пока всё. Митрич пошёл дальше копаться.",
    "Такие дела. Не всё же нам тревогу читать.",
]


def clean_title(title):
    return " ".join(title.replace("\n", " ").replace("\r", " ").split())


def is_bad(title):
    text = title.lower()

    if any(word in text for word in BAD_WORDS):
        return True

    current_month = datetime.now().month
    seasonal_bad_words = SEASON_BAD_MONTHS.get(current_month, [])

    if any(word in text for word in seasonal_bad_words):
        return True

    return False


def is_recent_entry(entry, max_days=21):
    published = getattr(entry, "published_parsed", None)
    updated = getattr(entry, "updated_parsed", None)
    date_struct = published or updated

    if not date_struct:
        return True

    entry_date = datetime(*date_struct[:6])
    min_date = datetime.utcnow() - timedelta(days=max_days)

    return entry_date >= min_date


def score_news(title, source):
    text = f"{title} {source}".lower()
    score = 0

    for word in GOOD_WORDS:
        if word in text:
            score += 2

    if "каш" in text:
        score += 10

    if "каляз" in text:
        score += 5

    if "твер" in text:
        score += 3

    if "монет" in text or "археолог" in text or "история" in text:
        score += 5

    if "золотое кольцо" in text or "туризм" in text:
        score += 5

    if "наука" in source.lower() or "naked science" in source.lower() or "хайтек" in source.lower():
        score += 2

    return score


def make_mitrich_line(title):
    text = clean_title(title)

    replacements = [
        ("В Тверской области ", "В Тверской области "),
        ("стало известно", "пишут"),
        ("сообщили", "пишут"),
        ("рассказали", "рассказывают"),
        ("назвали", "назвали"),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    starters = [
        "Тут пишут: ",
        "Попалось такое: ",
        "Есть вот такая новость: ",
        "А вот это занятно: ",
        "Вот ещё интересное: ",
        "Гляньте, что нашлось: ",
    ]

    comments = [
        "Нормальная тема, без лишней паники.",
        "Такое уже можно спокойно читать.",
        "Не сенсация века, но любопытно.",
        "Для маленьких городов такие вещи важны.",
        "Вот это ближе к жизни.",
        "Записал в хорошие находки.",
    ]

    starter = random.choice(starters)

    if random.random() < 0.45:
        return f"{starter}{text}. {random.choice(comments)}"

    return f"{starter}{text}."


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
            messages = soup.select(".tgme_widget_message")

            for message in messages[-12:]:
                text_block = message.select_one(".tgme_widget_message_text")
                link_block = message.select_one(".tgme_widget_message_date")

                if not text_block:
                    continue

                text = text_block.get_text(" ", strip=True)
                text = clean_title(text)

                if not text or len(text) < 40:
                    continue

                link = url
                if link_block and link_block.get("href"):
                    link = link_block.get("href")

                items.append({
                    "source": source_name,
                    "title": text[:280],
                    "link": link,
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
                if not is_recent_entry(entry):
                    continue

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
    return items[:5]


def build_message(items):
    today = datetime.now().strftime("%d.%m.%Y")

    if not items:
        return (
            f"☕ <b>Дайджест Митрича — {today}</b>\n\n"
            "Покопался я тут по лентам, но сегодня ничего приличного не нашёл.\n"
            "То шум, то тревога, то вообще майская ёлка из прошлого года.\n\n"
            "Подождём нормальных новостей."
        )

    lines = [
        f"☕ <b>Дайджест Митрича — {today}</b>",
        "",
        random.choice(INTRO_VARIANTS),
        "",
    ]

    links = ["", "<b>Источники, чтобы всё было по-честному:</b>"]

    for i, item in enumerate(items, 1):
        title = html.escape(make_mitrich_line(item["title"]))
        link = html.escape(item["link"])
        source = html.escape(item["source"])

        lines.append(f"{i}. {title}")
        lines.append("")

        links.append(f"{i}. <a href=\"{link}\">{source}</a>")

    lines.append(random.choice(ENDING_VARIANTS))

    return "\n".join(lines + links)


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
