import os
import re
import json
import html
import time
import hashlib
from datetime import datetime, timedelta
from difflib import SequenceMatcher

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


ADVERTISEMENT_WORDS = [
    "продается", "продаётся", "продам", "куплю", "аренда", "арендую",
    "сдается", "сдаётся", "сдам", "квартира", "ипотека", "цена",
    "стоимость", "скидка", "скидк", "акция", "промокод", "реклама",
    "подписка", "подписаться", "подпишитесь", "наш чат", "канал в max",
    "мы в max", "прислать новость", "присылайте новости", "забрать",
    "заказать", "бронь", "бронирование",
    "однокомнатная", "двухкомнатная", "трехкомнатная", "трёхкомнатная",
    "санузел", "балкон", "дом кирпичный", "комнат",
]


HIDDEN_PROMO_WORDS = [
    "попробуйте", "перейдите", "подробнее по ссылке", "ссылка в описании",
    "ссылка ниже", "бота который", "бота, который", "телеграм бот",
    "телеграм-бот", "telegram bot", "поддержать проект",
    "зарегистрируйтесь", "регистрация по ссылке", "участвуйте в акции",
    "участвуйте в розыгрыше", "переходите", "жмите", "напишите в бот",
    "наш бот", "бот поможет", "бот для", "переходите по ссылке",
]


HARD_TRASH_WORDS = [
    "убил", "убийство", "убийца", "погиб", "погибли", "погибший",
    "смерть", "умер", "скончался", "скончалась", "труп",
    "пострадал", "пострадали", "пострадавший", "пострадавшие",
    "насилие", "изнасил", "напал", "нападение", "драка",
    "криминал", "преступление", "уголовн", "воровств", "украл",
    "краж", "мошенник", "мошенничество", "коррупц",
    "дтп", "авария", "сбил", "столкнулись", "столкновение",
    "пожар", "загорел", "сгорел", "сгорела", "возгорание",
    "взрыв", "взорвался", "взорвалась", "теракт",
    "беспилотник", "беспилотники", "бпла", "дрон", "дроны",
    "ракета", "обстрел", "фронт", "война", "сво", "украин",
    "санкции", "суд", "приговор", "арест", "задержан", "задержали",
    "розыск", "наркот", "кладбище", "кладбища", "захоронение",
    "могила", "ритуальн", "трагедия", "трагедии", "чп",
]


HEAVY_DRAMA_WORDS = [
    "passed away", "brain tumor", "brain tumour", "cancer", "died",
    "funeral", "grief", "death", "in memory of", "memorial",
    "тяжелая болезнь", "тяжёлая болезнь", "тяжело болен", "тяжело больна",
    "умер", "умершем", "умершего", "память о погибшем", "память об умершем",
    "памяти погибшего", "памяти умершего", "онкология", "опухоль",
]


REGIONAL_NEGATIVE_WORDS = [
    "не может оправиться", "последствия циклона", "разрушения",
    "разрушен", "разрушена", "разрушены", "завалены", "завалило",
    "повреждены", "повреждено", "повреждена", "пострадали",
    "ущерб", "бедствие", "ураган", "сильный ветер повредил",
]


ABSTRACT_PR_WORDS = [
    "формирование новых подходов", "площадка для диалога",
    "человеческие инициативы", "ответственное отношение к климату",
    "лидеры предприниматели эксперты", "лидеры, предприниматели, эксперты",
    "стратегическая сессия", "экспертная площадка", "новые подходы",
    "межсекторное взаимодействие", "устойчивое развитие",
    "ценностно ориентированный", "комплексный подход",
]


MEDICAL_EMERGENCY_WORDS = [
    "санитарный вертолет", "санитарный вертолёт", "санавиация",
    "медицинская эвакуация", "медицинской эвакуации",
    "госпитализация", "госпитализировали", "госпитализирован",
    "доставили в больницу", "доставлен в больницу", "экстренно доставили",
    "экстренная помощь", "реанимация", "реанимобиль",
    "тяжелая болезнь", "тяжёлая болезнь", "тяжело болен", "тяжело больна",
    "опухоль", "онкология", "онкологическое", "рак мозга", "инсульт",
    "инфаркт", "кома",
]


MCHS_EMERGENCY_CONTEXT_WORDS = [
    "мчс", "спасатели", "эвакуация", "эвакуировали", "спасли",
    "чп", "происшествие", "авария", "дтп", "пожар", "пострадал",
    "пострадали", "погиб", "погибли", "госпитализ",
]


SOFT_BAD_WORDS = [
    "штраф", "грязная вода", "плохая вода", "канализация", "отключение воды",
    "обсудили", "заявил", "заявила", "заявили", "правительство", "министр",
    "депутат", "госдума", "совещание", "переговор", "конфликт",
    "обход", "глушил", "мобильного интернета", "vpn", "заработок",
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


STOP_DUPLICATE_WORDS = [
    "в", "на", "и", "а", "по", "для", "из", "от", "до", "о", "об", "с",
    "со", "у", "к", "ко", "за", "при", "это", "как", "что", "где",
    "новости", "новость", "тверской", "области", "тверская", "область",
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
    text = re.sub(r"[^a-zа-я0-9_@. ]+", " ", text)
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


def log_skip(reason, source, title_or_text):
    print(f"Пропущено: {reason}. Источник: {source}. Текст: {short_text(title_or_text, 160)}")


def is_advertisement(text):
    return contains_any(text, ADVERTISEMENT_WORDS)


def is_hidden_promo(text):
    normalized = normalize_text(text)

    if contains_any(normalized, HIDDEN_PROMO_WORDS):
        return True

    if "@" in normalized:
        return True

    if "участвуйте" in normalized and (
        "акци" in normalized
        or "розыгрыш" in normalized
        or "конкурс" in normalized
        or "ссылк" in normalized
        or "зарегистр" in normalized
    ):
        return True

    return False


def is_hard_trash(text):
    return contains_any(text, HARD_TRASH_WORDS)


def is_heavy_drama(text):
    return contains_any(text, HEAVY_DRAMA_WORDS)


def is_regional_negative(text):
    return contains_any(text, REGIONAL_NEGATIVE_WORDS)


def is_abstract_pr(text):
    return contains_any(text, ABSTRACT_PR_WORDS)


def is_medical_emergency(text):
    normalized = normalize_text(text)

    if contains_any(normalized, MEDICAL_EMERGENCY_WORDS):
        return True

    has_mchs = "мчс" in normalized or "спасател" in normalized
    has_emergency_context = contains_any(normalized, MCHS_EMERGENCY_CONTEXT_WORDS)

    if has_mchs and has_emergency_context:
        return True

    return False


def has_soft_bad(text):
    return contains_any(text, SOFT_BAD_WORDS) or contains_any(text, BUREAUCRACY_WORDS)


def has_season_bad(text):
    current_month = datetime.now().month
    seasonal_bad_words = SEASON_BAD_MONTHS.get(current_month, [])
    return contains_any(text, seasonal_bad_words)


def rejection_reason(text, category):
    if is_advertisement(text):
        return "реклама или объявление"

    if is_hidden_promo(text):
        return "скрытая реклама или промо"

    if is_medical_emergency(text):
        return "медицина/ЧП"

    if is_heavy_drama(text):
        return "тяжёлая человеческая драма"

    if is_hard_trash(text):
        return "жёсткий негатив"

    if has_season_bad(text):
        return "сезонный фильтр"

    if category in ["tver", "world"] and is_regional_negative(text):
        return "негативная региональная формулировка"

    if category in ["tver", "world"] and has_soft_bad(text):
        return "региональный/общий мусор или чиновничья вода"

    if category == "world" and is_abstract_pr(text):
        return "абстрактный пресс-релиз без человеческой истории"

    return ""


def should_reject(text, category):
    return bool(rejection_reason(text, category))


def soft_penalty(text, category):
    penalty = 0

    if has_soft_bad(text):
        if category == "kashin":
            penalty += 0
        elif category == "tver":
            penalty += 4
        else:
            penalty += 6

    if is_abstract_pr(text):
        if category == "kashin":
            penalty += 4
        elif category == "tver":
            penalty += 8
        else:
            penalty += 12

    return penalty


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


def tokenize_for_duplicate(text):
    normalized = normalize_text(text)
    words = normalized.split()

    result = []
    for word in words:
        if len(word) < 4:
            continue
        if word in STOP_DUPLICATE_WORDS:
            continue
        result.append(word)

    return set(result)


def event_signature(title, summary, category):
    text = normalize_text(f"{title} {summary}")
    tokens = tokenize_for_duplicate(text)

    places = []
    for place in ["кашин", "калязин", "кесова", "тверь", "кимры", "бежецк", "торжок", "ржев", "осташков"]:
        if place in text:
            places.append(place)

    museum_words = ["музей", "ретро", "гараж", "советск", "эпох"]
    if any(word in text for word in museum_words):
        base = "museum_retro"
    elif "выставк" in text:
        base = "exhibition"
    elif "фестивал" in text or "праздник" in text:
        base = "event"
    elif "ремонт" in text or "дорог" in text or "улиц" in text:
        base = "city_works"
    else:
        important = sorted(tokens)[:5]
        base = "_".join(important)

    place_part = "_".join(places) if places else category
    return f"{place_part}_{base}"


def is_similar_title(title_a, title_b):
    norm_a = normalize_text(title_a)
    norm_b = normalize_text(title_b)

    if not norm_a or not norm_b:
        return False

    ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
    if ratio >= 0.74:
        return True

    tokens_a = tokenize_for_duplicate(norm_a)
    tokens_b = tokenize_for_duplicate(norm_b)

    if not tokens_a or not tokens_b:
        return False

    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)

    if len(intersection) >= 3 and len(intersection) / len(union) >= 0.34:
        return True

    return False


def find_duplicate_index(items, title, summary, category):
    new_signature = event_signature(title, summary, category)

    for index, item in enumerate(items):
        if item["category"] != category:
            continue

        old_signature = event_signature(item["title"], item.get("summary", ""), item["category"])

        if old_signature == new_signature:
            return index

        if is_similar_title(title, item["title"]):
            return index

    return None


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

        if is_similar_title(normalized_title, old_title):
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
        return "🟢 Нормальная областная тема для выпуска."

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
                    log_skip(
                        "слишком длинный Telegram-пост",
                        source_name,
                        f"{len(full_text)} символов"
                    )
                    continue

                title = short_text(full_text, 120)
                summary = short_text(full_text, 360)
                category = classify_item(title, summary, source_name, "local")
                reason = rejection_reason(full_text, category)

                if reason:
                    log_skip(reason, source_name, full_text)
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

    reason = rejection_reason(check_text, category)
    if reason:
        log_skip(reason, source, title)
        return

    title_key = normalize_text(title)

    if title_key in seen_titles:
        log_skip("точный дубль в текущем запуске", source, title)
        return

    if is_seen(title, link, memory):
        log_skip("дубль по памяти", source, title)
        return

    score = score_news(title, summary, source, category)

    if category == "kashin":
        min_score = 1
    elif category == "tver":
        min_score = 3
    else:
        min_score = 4

    if score < min_score:
        log_skip(f"низкий score {score}", source, title)
        return

    duplicate_index = find_duplicate_index(items, title, summary, category)

    new_item = {
        "source": source,
        "title": title,
        "summary": summary,
        "link": link,
        "score": score,
        "category": category,
    }

    if duplicate_index is not None:
        old_item = items[duplicate_index]

        if score > old_item["score"]:
            print(
                f"Заменён похожий дубль: '{short_text(old_item['title'], 90)}' "
                f"→ '{short_text(title, 90)}'"
            )
            items[duplicate_index] = new_item
            seen_titles.add(title_key)
        else:
            log_skip("похожий дубль в текущем запуске", source, title)

        return

    seen_titles.add(title_key)
    items.append(new_item)


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
        "Рекламу, жесть, ЧП, тяжёлую драму и похожие дубли отсеял.",
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
