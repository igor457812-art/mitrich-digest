import os
import html
import time
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


def clean_text(text):
    if not text:
        return ""

    text = BeautifulSoup(str(text), "html.parser").get_text(" ", strip=True)
    text = html.unescape(text)
    return " ".join(text.replace("\n", " ").replace("\r", " ").split())


def short_text(text, limit=360):
    text = clean_text(text)

    if len(text) <= limit:
        return text

    cut = text[:limit]
    last_dot = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))

    if last_dot > 140:
        return cut[:last_dot + 1]

    return cut.rstrip() + "…"


def is_local(title):
    text = title.lower()
    return "каш" in text or "каляз" in text or "твер" in text


def is_bad(text):
    text = text.lower()

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


def score_news(title, summary, source):
    text = f"{title} {summary} {source}".lower()
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


def verdict_for_item(item):
    title = item["title"].lower()
    summary = item.get("summary", "").lower()
    text = f"{title} {summary}"

    if item["local"]:
        return "🟢 Да. Местная тема, хорошо подходит Митричу."

    if any(word in text for word in ["история", "археолог", "монет", "музей", "ретро", "золотое кольцо"]):
        return "🟢 Да. Можно красиво подать через историю и любопытство."

    if any(word in text for word in ["наука", "учёные", "ученые", "животн", "космос", "необыч"]):
        return "🟡 Можно. Хорошо как лёгкая разбавка."

    return "🟡 Спорно. Можно брать, если не найдётся темы сильнее."


def explain_item(item):
    title = item["title"]
    summary = item.get("summary", "")

    if summary:
        return short_text(summary, 360)

    return short_text(title, 260)


def get_entry_summary(entry):
    summary = getattr(entry, "summary", "")
    if not summary:
        summary = getattr(entry, "description", "")

    return short_text(summary, 360)


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

                full_text = clean_text(text_block.get_text(" ", strip=True))

                if not full_text or len(full_text) < 40:
                    continue

                if len(full_text) > 650:
                    continue

                if is_bad(full_text):
                    continue

                title = short_text(full_text, 120)
                summary = short_text(full_text, 360)

                link = url
                if link_block and link_block.get("href"):
                    link = link_block.get("href")

                items.append({
                    "source": source_name,
                    "title": title,
                    "summary": summary,
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

                title = clean_text(getattr(entry, "title", ""))
                link = getattr(entry, "link", "")
                summary = get_entry_summary(entry)

                if not title or not link:
                    continue

                check_text = f"{title} {summary}"

                if is_bad(check_text):
                    continue

                title_key = title.lower()

                if title_key in seen_titles:
                    continue

                seen_titles.add(title_key)

                score = score_news(title, summary, source_name)

                if score <= 0:
                    continue

                items.append({
                    "source": source_name,
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "score": score,
                    "local": is_local(title),
                })

            time.sleep(0.5)

        except Exception as error:
            print(f"Ошибка источника {source_name}: {error}")

    for item in get_telegram_news():
        title = item["title"]
        summary = item["summary"]
        title_key = title.lower()

        if title_key in seen_titles:
            continue

        seen_titles.add(title_key)

        check_text = f"{title} {summary}"

        if is_bad(check_text):
            continue

        score = score_news(title, summary, item["source"])

        if score <= 0:
            continue

        items.append({
            "source": item["source"],
            "title": title,
            "summary": summary,
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
            f"☕ <b>Редакторский дайджест Митрича — {today}</b>\n\n"
            "Сегодня нормальных тем почти не попалось.\n"
            "Лучше пропустить, чем делать выпуск из мусора."
        )

    lines = [
        f"☕ <b>Редакторский дайджест Митрича — {today}</b>",
        "",
        "Пошуршал по лентам. Ниже — темы, из которых можно лепить выпуск.",
        "",
    ]

    counter = 1

    local_items = [item for item in items if item["local"]]
    other_items = [item for item in items if not item["local"]]

    if local_items:
        lines.append("<b>Из наших краёв</b>")
        lines.append("")

        for item in local_items:
            title = html.escape(item["title"])
            summary = html.escape(explain_item(item))
            verdict = html.escape(verdict_for_item(item))
            link = html.escape(item["link"])
            source = html.escape(item["source"])

            lines.append(f"🟢 <b>{counter}. Что нашёл:</b> {title}")
            lines.append(f"<b>Суть:</b> {summary}")
            lines.append(f"<b>Можно брать:</b> {verdict}")
            lines.append(f"<b>Источник:</b> <a href=\"{link}\">{source}</a>")
            lines.append("")
            counter += 1

    if other_items:
        lines.append("<b>Для разбавки</b>")
        lines.append("")

        for item in other_items:
            title = html.escape(item["title"])
            summary = html.escape(explain_item(item))
            verdict = html.escape(verdict_for_item(item))
            link = html.escape(item["link"])
            source = html.escape(item["source"])

            lines.append(f"🟡 <b>{counter}. Что нашёл:</b> {title}")
            lines.append(f"<b>Суть:</b> {summary}")
            lines.append(f"<b>Можно брать:</b> {verdict}")
            lines.append(f"<b>Источник:</b> <a href=\"{link}\">{source}</a>")
            lines.append("")
            counter += 1

    lines.append("Выбирай 1–2 темы — из них уже можно делать голос Митрича.")

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
