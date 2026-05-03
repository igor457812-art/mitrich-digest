import os
import re
import json
import html
import time
import hashlib
from datetime import datetime, timedelta

import feedparser
import requests
from bs4 import BeautifulSoup


BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

MEMORY_FILE = "sent_news.json"
MEMORY_DAYS = 14
MAX_HOURS = 48
TELEGRAM_MESSAGE_LIMIT = 3800


LOCAL_FEEDS = [
    ("Кашин — БезФормата", "https://kashin.bezformata.com/rsstop.xml"),
    ("Google News — Кашин", "https://news.google.com/rss/search?q=Кашин+Тверская+область&hl=ru&gl=RU&ceid=RU:ru"),
    ("Google News — Калязин", "https://news.google.com/rss/search?q=Калязин&hl=ru&gl=RU&ceid=RU:ru"),
    ("Google News — Кесова Гора", "https://news.google.com/rss/search?q=Кесова+Гора&hl=ru&gl=RU&ceid=RU:ru"),
    ("Google News — Кашинский округ", "https://news.google.com/rss/search?q=Кашинский+округ&hl=ru&gl=RU&ceid=RU:ru"),
]


REGIONAL_FEEDS = [
    ("Афанасий Бизнес", "https://www.afanasy.biz/rss"),
    ("Google News — Тверская область", "https://news.google.com/rss/search?q=Тверская+область+новости&hl=ru&gl=RU&ceid=RU:ru"),
]


WORLD_FEEDS = [
    ("Good News Network", "https://www.goodnewsnetwork.org/feed/"),
    ("Indicator", "https://indicator.ru/rss/all.xml"),
    ("Элементы", "https://elementy.ru/rss/news"),
    ("Наука и жизнь", "https://nkj.ru/rss/"),
]


TELEGRAM_CHANNELS = [
    ("Калязин & Кашин: News", "https://t.me/s/pvk_69"),
    ("Администрация Кашина", "https://t.me/s/kashinadm"),
    ("Кашин Кайф", "https://t.me/s/kashinkaif"),
]


HARD_BAD_WORDS = [
    "убил", "убийство", "убийца", "погиб", "погибли", "смерть", "умер",
    "труп", "насилие", "изнасил", "напал", "нападение", "драка",
    "авария с пострадав", "дтп с пострадав", "пострадал", "пострадали",
    "пожар", "взрыв", "теракт", "война", "ракета", "обстрел", "бпла",
    "дрон", "фронт", "сво", "суд", "приговор", "арест", "задержан",
    "уголовн", "коррупц", "мошенник", "воровств", "украл", "краж",
    "наркот", "алкогол", "пьяный", "избил", "розыск", "санкции",
    "украин", "навальный", "трагедия", "трагедии",
]


SOFT_BAD_WORDS = [
    "штраф", "грязная вода", "плохая вода", "канализация", "отключение воды",
    "обсудили", "заявил", "заявила", "заявили", "правительство", "министр",
    "депутат", "госдума", "совещание", "переговор", "конфликт",
    "подписк", "забрать", "промокод", "скидк", "акция", "реклама",
    "наш чат", "мы в max", "прислать новость", "ссылка ниже",
    "обход", "глушил", "мобильного интернета", "vpn", "заработок",
    "продается", "продаётся", "продам", "куплю", "аренда", "сдается",
    "сдаётся", "квартира", "однокомнатная", "двухкомнатная",
    "трехкомнатная", "трёхкомнатная", "комнат", "цена", "ипотека",
    "дом кирпичный", "санузел", "балкон",
]


BUREAUCRACY_WORDS = [
    "провел совещание", "провёл совещание", "провела совещание",
    "обсудили вопросы", "обсудили ход", "реализация мероприятий",
    "в рамках реализации", "состоялось заседание", "рабочая встреча",
    "принял участие", "приняла участие", "поручил", "поручила",
    "доложил", "доложила", "отчитались", "контроль исполнения",
    "межведомственное взаимодействие", "плановое мероприятие",
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
    "каш", "каляз", "кесова", "твер", "город", "музей", "выставка",
    "фестиваль", "праздник", "история", "археолог", "нашли",
    "обнаружили", "раскоп", "монет", "наука", "учёные", "ученые",
    "космос", "планет", "животн", "необыч", "редк", "курьёз",
    "курьез", "интересн", "дети", "школ", "учитель", "культура",
    "театр", "книга", "добровол", "помог", "открыли", "создали",
    "изобрели", "площад", "благоустр", "золотое кольцо", "туризм",
    "турист", "конкурс", "природ", "река", "ретро", "гараж", "парк",
    "мастер", "ремесл", "сохранили", "восстановили", "память",
    "ярмарка", "ремонт", "дорога", "двор", "улица", "местные",
    "жители", "открытие", "встреча", "концерт", "спорт",
]


KASHIN_WORDS = [
    "кашин", "кашинский", "кашинского", "кашинском", "калязин",
    "калязинский", "кесова гора", "кесовогорский",
]


TVER_WORDS = [
    "тверь", "тверская область", "тверской области", "тверском",
    "тверской", "кимры", "бежецк", "торжок", "ржев", "осташков",
    "старица", "лихославль", "вышний волочек", "удомля",
]


def clean_text(text):
    if not text:
        return ""

    text = BeautifulSoup(str(text), "html.parser").get_text(" ", strip=True)
    text = html.unescape(text)
    return " ".join(text.replace("\n", " ").replace("\r", " ").split())


def normalize_text(text):
    text = clean_text(text).lower()
    text = text.replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def contains_any(text, words):
    normalized = normalize_text(text)
    return any(word.replace("ё", "е") in normalized for word in words)


def short_text(text, limit=360):
    text = clean_text(text)

    if len(text) <= limit:
        return text

    cut = text[:limit]
    last_dot = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))

    if last_dot > 140:
        return cut[:last_dot + 1]

    return cut.rstrip() + "…"


def split_message(text, limit=TELEGRAM_MESSAGE_LIMIT):
    parts = []
    current = ""

    for line in text.split("\n"):
        candidate = line if not current else current + "\n" + line

        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            parts.append(current)
            current = ""

        if len(line) <= limit:
            current = line
        else:
            while len(line) > limit:
                cut = line[:limit]
                last_space = cut.rfind(" ")

                if last_space > 500:
                    parts.append(line[:last_space])
                    line = line[last_space:].strip()
                else:
                    parts.append(cut)
                    line = line[limit:].strip()

            current = line

    if current:
        parts.append(current)

    return parts


def make_memory_key(title, link):
    normalized_title = normalize_text(title)
    normalized_link = clean_text(link).strip().lower()
    raw = f"{normalized_title}|{normalized_link}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

        return {}

    except Exception as error:
        print(f"Не смог прочитать память дублей: {error}")
        return {}


def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as file:
            json.dump(memory, file, ensure_ascii=False, indent=2)
    except Exception as error:
        print(f"Не смог сохранить память дублей: {error}")


def cleanup_memory(memory):
    cleaned = {}
    min_date = datetime.utcnow() - timedelta(days=MEMORY_DAYS)

    for key, value in memory.items():
        sent_at = value.get("sent_at")

        if not sent_at:
            continue

        try:
            sent_date = datetime.fromisoformat(sent_at)
        except Exception:
            continue

        if sent_date >= min_date:
            cleaned[key] = value

    return cleaned


def is_seen(title, link, memory):
    key = make_memory_key(title, link)

    if key in memory:
        return True

    normalized_title = normalize_text(title)

    for value in memory.values():
        old_title = normalize_text(value.get("title", ""))

        if normalized_title and old_title and normalized_title == old_title:
            return True

    return False


def remember_items(items, memory):
    now = datetime.utcnow().isoformat(timespec="seconds")

    for item in items:
        key = make_memory_key(item["title"], item["link"])
        memory[key] = {
            "title": item["title"],
            "link": item["link"],
            "source": item["source"],
            "category": item["category"],
            "sent_at": now,
        }

    save_memory(memory)


def has_hard_bad(text):
    return contains_any(text, HARD_BAD_WORDS)


def has_soft_bad(text):
    return contains_any(text, SOFT_BAD_WORDS) or contains_any(text, BUREAUCRACY_WORDS)


def has_season_bad(text):
    current_month = datetime.now().month
    seasonal_bad_words = SEASON_BAD_MONTHS.get(current_month, [])
    return contains_any(text, seasonal_bad_words)


def should_reject(text, category):
    if has_hard_bad(text):
        return True

    if has_season_bad(text):
        return True

    return False


def soft_penalty(text, category):
    if not has_soft_bad(text):
        return 0

    if category == "kashin":
        return 0

    if category == "tver":
        return 4

    return 6


def classify_item(title, summary, source, feed_group):
    text = f"{title} {summary} {source}"

    if feed_group == "local":
        return "kashin"

    if feed_group == "regional":
        return "tver"

    if contains_any(text, KASHIN_WORDS):
        return "kashin"

    if contains_any(text, TVER_WORDS):
        return "tver"

    return "world"


def is_recent_entry(entry, max_hours=MAX_HOURS):
    published = getattr(entry, "published_parsed", None)
    updated = getattr(entry, "updated_parsed", None)
    date_struct = published or updated

    if not date_struct:
        return False

    entry_date = datetime(*date_struct[:6])
    min_date = datetime.utcnow() - timedelta(hours=max_hours)

    return entry_date >= min_date


def score_news(title, summary, source, category):
    text = f"{title} {summary} {source}".lower()
    score = 0

    for word in GOOD_WORDS:
        if word in text:
            score += 2

    if category == "kashin":
        score += 20

    if category == "tver":
        score += 9

    if "каш" in text:
        score += 12

    if "каляз" in text:
        score += 8

    if "кесова" in text:
        score += 6

    if "твер" in text:
        score += 5

    if "монет" in text or "археолог" in text or "история" in text:
        score += 6

    if "золотое кольцо" in text or "туризм" in text:
        score += 5

    if "ретро" in text or "музей" in text or "выставка" in text:
        score += 5

    if "животн" in text or "природ" in text:
        score += 4

    if (
        "наука" in source.lower()
        or "naked science" in source.lower()
        or "хайтек" in source.lower()
        or "indicator" in source.lower()
        or "элементы" in source.lower()
        or "наука и жизнь" in source.lower()
    ):
        score += 3

    if "good news network" in source.lower():
        score += 5

    score -= soft_penalty(text, category)

    return score


def verdict_for_item(item):
    title = item["title"].lower()
    summary = item.get("summary", "").lower()
    text = f"{title} {summary}"

    if item["category"] == "kashin":
        if has_soft_bad(text):
            return "🟡 Живая местная тема. Не радостная, но без жести — можно смотреть редактору."
        return "🟢 Местная тема. Для кашинского блока подходит."

    if item["category"] == "tver":
        if has_soft_bad(text):
            return "🟡 Областная тема, но спорная по тону. Нужна ручная проверка."
        return "🟢 Нормальная областная тема для выпуска."

    if has_soft_bad(text):
        return "🟡 Спорно. Для России/мира брать только если смысл действительно человеческий."

    if any(word in text for word in ["история", "археолог", "монет", "музей", "ретро", "золотое кольцо"]):
        return "🟢 Хорошая. Можно подать через любопытство и историю."

    if any(word in text for word in ["наука", "учёные", "ученые", "животн", "космос", "необыч"]):
        return "🟢 Подойдёт как лёгкая новость Россия/мир."

    return "🟡 Нейтральная тема. Брать, если редактору есть за что зацепиться."


def explain_item(item):
    summary = item.get("summary", "")

    if summary:
        return short_text(summary, 360)

    return short_text(item["title"], 260)


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

                if len(full_text) > 1200:
                    print(
                        f"Пропущен Telegram-пост: слишком длинный текст — "
                        f"{len(full_text)} символов, источник: {source_name}"
                    )
                    continue

                title = short_text(full_text, 120)
                summary = short_text(full_text, 360)
                category = classify_item(title, summary, source_name, "local")

                if should_reject(full_text, category):
                    print(
                        f"Пропущен Telegram-пост: жёсткий негатив или сезонный фильтр, "
                        f"источник: {source_name}, текст: {short_text(full_text, 120)}"
                    )
                    continue

                link = url
                if link_block and link_block.get("href"):
                    link = link_block.get("href")

                items.append({
                    "source": source_name,
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "feed_group": "local",
                })

        except Exception as error:
            print(f"Ошибка Telegram-канала {source_name}: {error}")

    return items


def add_item(items, seen_titles, memory, source, title, summary, link, feed_group):
    if not title or not link:
        return

    category = classify_item(title, summary, source, feed_group)
    check_text = f"{title} {summary}"

    if should_reject(check_text, category):
        return

    title_key = normalize_text(title)

    if title_key in seen_titles:
        return

    if is_seen(title, link, memory):
        return

    score = score_news(title, summary, source, category)

    if category == "kashin":
        min_score = 1
    elif category == "tver":
        min_score = 3
    else:
        min_score = 4

    if score < min_score:
        return

    seen_titles.add(title_key)

    items.append({
        "source": source,
        "title": title,
        "summary": summary,
        "link": link,
        "score": score,
        "category": category,
    })


def get_all_feeds():
    feeds = []

    for source_name, feed_url in LOCAL_FEEDS:
        feeds.append(("local", source_name, feed_url))

    for source_name, feed_url in REGIONAL_FEEDS:
        feeds.append(("regional", source_name, feed_url))

    for source_name, feed_url in WORLD_FEEDS:
        feeds.append(("world", source_name, feed_url))

    return feeds


def collect_news():
    memory = cleanup_memory(load_memory())
    save_memory(memory)

    items = []
    seen_titles = set()

    for feed_group, source_name, feed_url in get_all_feeds():
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:15]:
                if not is_recent_entry(entry):
                    continue

                title = clean_text(getattr(entry, "title", ""))
                link = getattr(entry, "link", "")
                summary = get_entry_summary(entry)

                add_item(
                    items=items,
                    seen_titles=seen_titles,
                    memory=memory,
                    source=source_name,
                    title=title,
                    summary=summary,
                    link=link,
                    feed_group=feed_group,
                )

            time.sleep(0.5)

        except Exception as error:
            print(f"Ошибка источника {source_name}: {error}")

    for item in get_telegram_news():
        add_item(
            items=items,
            seen_titles=seen_titles,
            memory=memory,
            source=item["source"],
            title=item["title"],
            summary=item["summary"],
            link=item["link"],
            feed_group=item["feed_group"],
        )

    kashin_items = [item for item in items if item["category"] == "kashin"]
    tver_items = [item for item in items if item["category"] == "tver"]
    world_items = [item for item in items if item["category"] == "world"]

    kashin_items.sort(key=lambda x: x["score"], reverse=True)
    tver_items.sort(key=lambda x: x["score"], reverse=True)
    world_items.sort(key=lambda x: x["score"], reverse=True)

    return {
        "kashin": kashin_items[:4],
        "tver": tver_items[:3],
        "world": world_items[:3],
        "memory": memory,
    }


def category_title(category):
    if category == "kashin":
        return "1. Кашин / рядом"

    if category == "tver":
        return "2. Тверская область"

    return "3. Россия / мир"


def emoji_for_category(category):
    if category == "kashin":
        return "🟢"

    if category == "tver":
        return "🟢"

    return "🟡"


def build_item_lines(item, number):
    title = html.escape(item["title"])
    summary = html.escape(explain_item(item))
    verdict = html.escape(verdict_for_item(item))
    link = html.escape(item["link"])
    source = html.escape(item["source"])
    emoji = emoji_for_category(item["category"])

    return [
        f"{emoji} <b>{number}. Что нашёл:</b> {title}",
        f"<b>Суть:</b> {summary}",
        f"<b>Оценка:</b> {verdict}",
        f"<b>Источник:</b> <a href=\"{link}\">{source}</a>",
        "",
    ]


def build_message(collected):
    today = datetime.now().strftime("%d.%m.%Y")

    kashin_items = collected["kashin"]
    tver_items = collected["tver"]
    world_items = collected["world"]

    total_items = len(kashin_items) + len(tver_items) + len(world_items)

    if total_items == 0:
        return (
            f"☕ <b>Редакторский дайджест Митрича — {today}</b>\n\n"
            "Сегодня свежих нормальных тем не попалось.\n"
            "Лучше пропустить, чем делать выпуск из старья, дублей или жести."
        )

    lines = [
        f"☕ <b>Редакторский дайджест Митрича — {today}</b>",
        "",
        f"Проверил RSS, Google News и публичные Telegram-страницы за последние {MAX_HOURS} часов.",
        "Жёсткий негатив отсеял. Местные темы смотрю мягче: для маленького города это правильно.",
        "",
    ]

    blocks = [
        ("kashin", kashin_items),
        ("tver", tver_items),
        ("world", world_items),
    ]

    for category, items in blocks:
        lines.append(f"<b>{category_title(category)}</b>")
        lines.append("")

        if not items:
            if category == "kashin":
                lines.append("Свежей местной живой темы не нашлось. Для выпуска лучше сделать «Кашинскую строку».")
            elif category == "tver":
                lines.append("Нормальной областной темы пока нет.")
            else:
                lines.append("Лёгкой темы Россия/мир пока не нашлось.")
            lines.append("")
            continue

        for index, item in enumerate(items, start=1):
            lines.extend(build_item_lines(item, index))

    lines.append("Для Митрича лучше брать одну тему из каждого блока. Если кашинский блок пустой — делаем «Кашинскую строку», а не заменяем её федеральной новостью.")

    return "\n".join(lines)


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    parts = split_message(text, TELEGRAM_MESSAGE_LIMIT)

    for index, part in enumerate(parts, start=1):
        try:
            response = requests.post(
                url,
                data={
                    "chat_id": CHAT_ID,
                    "text": part,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
            response.raise_for_status()
            print(f"Отправлена часть {index}/{len(parts)}, длина: {len(part)} символов")
            time.sleep(0.5)

        except requests.exceptions.HTTPError as error:
            print(f"Ошибка Telegram при отправке части {index}/{len(parts)}")
            print(f"Длина части: {len(part)} символов")
            print(f"Текст ошибки: {error}")
            print(f"Ответ Telegram: {response.text}")
            raise

        except Exception as error:
            print(f"Неожиданная ошибка Telegram при отправке части {index}/{len(parts)}")
            print(f"Длина части: {len(part)} символов")
            print(f"Текст ошибки: {error}")
            raise


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("Не задан BOT_TOKEN")

    if not CHAT_ID:
        raise ValueError("Не задан CHAT_ID")

    collected_news = collect_news()
    message = build_message(collected_news)
    send_message(message)

    all_sent_items = (
        collected_news["kashin"]
        + collected_news["tver"]
        + collected_news["world"]
    )

    remember_items(all_sent_items, collected_news["memory"])
