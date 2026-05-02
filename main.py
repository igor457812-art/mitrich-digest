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
    ("Лента — Наука", "https://lenta.ru/rss/news/science"),
    ("РИА — Наука", "https://ria.ru/export/rss2/science/index.xml"),
    ("Naked Science", "https://naked-science.ru/feed"),
    ("Хайтек", "https://hightech.fm/feed"),

    ("Кашин — новости", "https://news.google.com/rss/search?q=Кашин+Тверская+область&hl=ru&gl=RU&ceid=RU:ru"),
    ("Калязин и Кашин", "https://news.google.com/rss/search?q=Калязин+Кашин+новости&hl=ru&gl=RU&ceid=RU:ru"),
    ("Тверь — интересное", "https://news.google.com/rss/search?q=Тверская+область+интересное+культура+туризм+музей&hl=ru&gl=RU&ceid=RU:ru"),
    ("Россия — интересное", "https://news.google.com/rss/search?q=Россия+необычное+наука+история+археология+животные&hl=ru&gl=RU&ceid=RU:ru"),
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

    "подписк", "забрать", "промокод", "скидк", "акция", "реклама",
    "наш чат", "мы в max", "прислать новость", "ссылка ниже",
    "обход", "глушил", "мобильного интернета", "vpn", "заработок",

    "продается", "продаётся", "продам", "куплю", "аренда", "сдается",
    "сдаётся", "квартира", "однокомнатная", "двухкомнатная",
    "трехкомнатная", "трёхкомнатная", "комнат", "цена", "ипотека",
    "дом кирпичный", "санузел", "балкон",

    "обсудили", "заявил", "заявила", "заявили", "пригрозил",
    "правительство", "министр", "депутат", "госдума", "совещание",
    "санкц", "переговор", "конфликт",
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
    "площад", "благоустр", "золотое кольцо",
    "туризм", "турист", "конкурс", "природ", "река",
    "ретро", "гараж", "парк", "мастер", "ремесл",
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


def is_local(title):
    text = title.lower()
    return "каш" in text or "каляз" in text or "твер" in text


def is_bad(title):
    text = title.lower()

    if any(word in text for word in BAD_WORDS):
        return True

    current_month = datetime.now().month
    seasonal_bad_words = SEASON_BAD_MONTHS.get(current_month, [])

    if any(word in text for word in seasonal_bad_words):
        return True

    return False


def is_too_long_for_telegram_source(text):
    return len(text) > 220


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
        score += 12

    if "каляз" in text:
        score += 7

    if "твер" in text:
        score += 4

    if "монет" in text or "археолог" in text or "история" in text:
        score += 6

    if "золотое кольцо" in text or "туризм" in text:
        score += 5

    if "ретро" in text or "музей" in text or "выставка" in text:
        score += 5

    if "наука" in source.lower() or "naked science" in source.lower() or "хайтек" in source.lower():
        score += 3

    return score


def make_mitrich_line(title, local=False):
    text = clean_title(title)

    if local:
        starters = [
            "Из наших краёв: ",
            "По Кашину и рядом попалось: ",
            "Местное нашлось такое: ",
            "Вот из ближнего: ",
        ]
        comments = [
            "Такое Митрич отдельно записал.",
            "Это уже ближе к дому.",
            "За такими новостями и следим.",
            "Вот это в нашу копилку.",
        ]
    else:
        starters = [
            "А из большого интернета вот что: ",
            "Для разбавки — интересная штука: ",
            "Ещё попалось занятное: ",
            "Из не местного, но любопытного: ",
        ]
        comments = [
            "Не сенсация века, но любопытно.",
            "Такое уже можно спокойно читать.",
            "Хоть какая-то польза от интернета.",
            "Записал в хорошие находки.",
        ]

    if random.random() < 0.45:
        return f"{random.choice(starters)}{text}. {random.choice(comments)}"

    return f"{random.choice(starters)}{text}."


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

            for message in messages[-15:]:
                text_block = message.select_one(".tgme_widget_message_text")
                link_block = message.select_one(".tgme_widget_message_date")

                if not text_block:
                    continue

                text = clean_title(text_block.get_text(" ", strip=True))

                if not text or len(text) < 40:
                    continue

                if is_too_long_for_telegram_source(text):
                    continue

                if is_bad(text):
                    continue

                link = url
                if link_block and link_block.get("href"):
                    link = link_block.get("href")

                items.append({
                    "source": source_name,
                    "title": text,
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

            for entry in feed.entries[:10]:
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
                    "local": is_local(title),
                })

            time.sleep(0.5)

        except Exception as error:
            print(f"Ошибка источника {source_name}: {error}")

    for item in get_telegram_news():
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
            "local": is_local(title),
        })

    local_items = [item for item in items if item["local"]]
    other_items = [item for item in items if not item["local"]]

    local_items.sort(key=lambda x: x["score"], reverse=True)
    other_items.sort(key=lambda x: x["score"], reverse=True)

    result = []

    result.extend(local_items[:2])

    for item in other_items:
        if len(result) >= 5:
            break
        result.append(item)

    if len(result) < 5:
        for item in local_items[2:]:
            if len(result) >= 5:
                break
            result.append(item)

    return result[:5]


def build_message(items):
    today = datetime.now().strftime("%d.%m.%Y")

    if not items:
        return (
            f"☕ <b>Дайджест Митрича — {today}</b>\n\n"
            "Покопался я тут по лентам, но сегодня ничего приличного не нашёл.\n"
            "То шум, то тревога, то вообще майская ёлка из прошлого года.\n\n"
            "Подождём нормальных новостей."
        )

    local_items = [item for item in items if item["local"]]
    other_items = [item for item in items if not item["local"]]

    lines = [
        f"☕ <b>Дайджест Митрича — {today}</b>",
        "",
        random.choice(INTRO_VARIANTS),
        "",
    ]

    links = ["", "<b>Источники, чтобы всё было по-честному:</b>"]
    counter = 1

    if local_items:
        lines.append("<b>Из наших краёв:</b>")
        lines.append("")

        for item in local_items:
            title = html.escape(make_mitrich_line(item["title"], local=True))
            lines.append(f"{counter}. {title}")
            lines.append("")

            link = html.escape(item["link"])
            source = html.escape(item["source"])
            links.append(f"{counter}. <a href=\"{link}\">{source}</a>")
            counter += 1

    if other_items:
        lines.append("<b>Для разбавки:</b>")
        lines.append("")

        for item in other_items:
            title = html.escape(make_mitrich_line(item["title"], local=False))
            lines.append(f"{counter}. {title}")
            lines.append("")

            link = html.escape(item["link"])
            source = html.escape(item["source"])
            links.append(f"{counter}. <a href=\"{link}\">{source}</a>")
            counter += 1

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
