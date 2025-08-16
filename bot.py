
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)
from collections import defaultdict, deque
from datetime import datetime, timedelta
import random
import pickle
from pathlib import Path
import logging
import pytz

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(name)

TOKEN = ".........."
DATA_FILE = "bot_data.pkl"
CHANNEL_LINK = "https://t.me/+s8nALxPQZ5QwYmEy"
KOREAN_BOT_LINK = "http://t.me/koreanchickbot"
TIMEZONE = pytz.timezone('Europe/Moscow')

WORDS = [
    "айдол", "амбар", "арбуз", "атлас", "балет", "банан", "базар", "берег", "бетон", "бидон",
    "билет", "биржа", "бисер", "богач", "бокал", "бонус", "бочка", "борец", "бренд", "броня",
    "бронх", "бремя", "буква", "букет", "валик", "венок", "весло", "весна", "ветер", "взнос",
    "взрыв", "вирус", "вожак", "газон", "глина", "гонка", "грант", "гроза", "груша", "дверь",
    "десна", "доска", "дождь", "забор", "завод", "залог", "зверь", "зебра", "знамя", "игрок",
    "икона", "инжир", "искус", "кабан", "капля", "карта", "касса", "кимчи", "класс", "клише",
    "книга", "князь", "ковер", "крыша", "куксу", "купол", "лампа", "лента", "лиана", "линия",
    "лишай", "маска", "место", "мешок", "молот", "норма", "обмен", "образ", "округ", "оплот",
    "осень", "отель", "отряд", "пакет", "палка", "парус", "паром", "песок", "печка", "песня",
    "плато", "повар", "полёт", "полка", "порох", "птица", "пульт", "район", "рамка", "резец",
    "родня", "ручка", "сетка", "сфера", "столб", "сумка", "фокус", "форма", "фильм", "чайка",
    "щиток", "кошка", "хауси", "слоны", "змея", "флаг"
]

class GameData:
    def init(self):
        self.user_words = defaultdict(deque)
        self.game_stats = defaultdict(lambda: {
            "games_played": 0,
            "wins": 0,
            "current_streak": 0,
            "max_streak": 0,
            "last_win": None,
            "username": None,
            "first_name": None,
            "words_guessed": []
        })
        self.admin_stats = {
            "total_games": 0,
            "games_history": [],
            "last_update": datetime.now(TIMEZONE),
            "all_words": WORDS.copy()
        }
    
    @classmethod
    def load(cls):
        try:
            if Path(DATA_FILE).exists():
                with open(DATA_FILE, "rb") as f:
                    return pickle.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
        return cls()
    
    def save(self):
        try:
            with open(DATA_FILE, "wb") as f:
                pickle.dump(self, f)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")

# Инициализация данных
bot_data = GameData.load()
active_games = {}

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Начать игру", callback_data='start_game')],
        [InlineKeyboardButton("📊 Мои результаты", callback_data='my_stats')],
        [InlineKeyboardButton("❓ Как играть", callback_data='help')],
        [InlineKeyboardButton("📢 Перейти в канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton("🥢Вкусная пауза", url=KOREAN_BOT_LINK)]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_data.game_stats[user.id]["username"] = user.username
    bot_data.game_stats[user.id]["first_name"] = user.first_name
    bot_data.save()
    
    await update.message.reply_text(
        "🎲 Добро пожаловать в игру «5 букв»!\n"
        "Угадай слово из 5 букв за 6 попыток👇",
        reply_markup=get_main_menu()
    )

VizoraX, [16.08.2025 9:11]
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎲 Добро пожаловать в игру «5 букв»!\n"
        "Угадай слово из 5 букв за 6 попыток👇",
        reply_markup=get_main_menu()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start_game':
        await start_game(update, context)
    elif query.data == 'my_stats':
        await show_stats(update, context)
    elif query.data == 'help':
        await show_help(update, context)

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    
    if user_id in active_games:
        await query.edit_message_text("Вы уже в игре! Присылайте слова из 5 букв.")
        return
    
    # Если слова закончились, перемешиваем заново
    if not bot_data.user_words[user_id]:
        words = bot_data.admin_stats["all_words"].copy()
        random.shuffle(words)
        bot_data.user_words[user_id] = deque(words)
    
    current_word = bot_data.user_words[user_id][0]
    active_games[user_id] = {
        "word": current_word,
        "attempts": [],
        "max_attempts": 6
    }
    
    bot_data.game_stats[user_id]["games_played"] += 1
    bot_data.admin_stats["total_games"] += 1
    bot_data.admin_stats["last_update"] = datetime.now(TIMEZONE)
    
    # Обновляем имя пользователя при каждом запуске игры
    bot_data.game_stats[user_id]["username"] = user.username
    bot_data.game_stats[user_id]["first_name"] = user.first_name
    
    bot_data.save()
    
    await query.edit_message_text(
        f"🔠 Игра началась! У тебя {active_games[user_id]['max_attempts']} попыток.\n"
        "Присылай слово из 5 букв:"
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    help_text = (
        "❓ Как играть:\n"
        "1. Нажми 'Начать игру'\n"
        "2. Присылай слова из 5 русских букв\n"
        "3. Бот даст подсказки:\n"
        "   ✅ - буква на своем месте\n"
        "   🔄 - буква есть, но не там\n"
        "   ❌ - буквы нет в слове\n\n"
        "Пример:\n"
        "Слово: КОШКА\n"
        "Ты: КАШПО\n"
        "Бот: Попытка 1/6:\n"
        "К А Ш П О\n"
        "✅ 🔄 ✅ ❌ 🔄\n\n"
        "Ты: КОШКА\n"
        "Бот: 🎉 Победа!"
    )
    await query.edit_message_text(help_text, reply_markup=get_main_menu())

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    stats = bot_data.game_stats[user_id]
    
    win_rate = (stats["wins"] / stats["games_played"] * 100) if stats["games_played"] > 0 else 0
    last_win = stats["last_win"].astimezone(TIMEZONE).strftime("%d.%m.%Y %H:%M") if stats["last_win"] else "еще не было"
    period = bot_data.admin_stats["last_update"].astimezone(TIMEZONE).strftime("%d.%m.%Y %H:%M")
    
    stats_text = (
        f"📊 Ваши результаты (обновлено {period}):\n"
        f"• Игр: {stats['games_played']}\n"
        f"• Побед: {stats['wins']} ({win_rate:.1f}%)\n"
        f"• Текущая серия: {stats['current_streak']}\n"
        f"• Макс. серия: {stats['max_streak']}\n"
        f"• Последняя победа: {last_win}"
    )
    await query.edit_message_text(stats_text, reply_markup=get_main_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text.strip().lower()
    
    if user_id not in active_games:
        await update.message.reply_text("Сначала начните игру через меню (/start).")

VizoraX, [16.08.2025 9:11]
return
    
    game = active_games[user_id]
    
    if len(text) != 5 or not text.isalpha() or not all(letter in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for letter in text):
        await update.message.reply_text("Нужно слово из 5 русских букв!")
        return
    
    if text in game["attempts"]:
        await update.message.reply_text("Это слово уже было!")
        return
    
    game["attempts"].append(text)
    result = analyze_attempt(text, game["word"])
    attempt_num = len(game["attempts"])
    
    if text == game["word"]:
        stats = bot_data.game_stats[user_id]
        stats["wins"] += 1
        stats["current_streak"] += 1
        stats["max_streak"] = max(stats["max_streak"], stats["current_streak"])
        stats["last_win"] = datetime.now(TIMEZONE)
        stats["words_guessed"].append(game["word"])
        
        bot_data.user_words[user_id].popleft()
        bot_data.admin_stats["last_update"] = datetime.now(TIMEZONE)
        
        # Добавляем в историю игр
        bot_data.admin_stats["games_history"].append({
            "user_id": user_id,
            "username": user.username,
            "first_name": user.first_name,
            "word": game["word"],
            "is_win": True,
            "attempts": attempt_num,
            "timestamp": datetime.now(TIMEZONE)
        })
        
        bot_data.save()
        
        # Формируем текст с последней попыткой
        last_attempt = (
            f"Попытка {attempt_num}/{game['max_attempts']}:\n"
            f"{' '.join(text.upper())}\n"
            f"{' '.join(result)}"
        )
        
        win_text = (
            f"🎉 Победа! Слово: {game['word'].upper()}\n"
            f"Попыток использовано: {attempt_num}\n\n"
            f"{last_attempt}\n\n"
            f"Хочешь отгадать еще одно слово?👀\n"
            f"Жми /start"
        )
        
        await update.message.reply_text(win_text)
        del active_games[user_id]
        return
    
    if attempt_num >= game["max_attempts"]:
        bot_data.game_stats[user_id]["current_streak"] = 0
        bot_data.admin_stats["last_update"] = datetime.now(TIMEZONE)
        
        # Добавляем в историю игр
        bot_data.admin_stats["games_history"].append({
            "user_id": user_id,
            "username": user.username,
            "first_name": user.first_name,
            "word": game["word"],
            "is_win": False,
            "attempts": attempt_num,
            "timestamp": datetime.now(TIMEZONE)
        })
        
        bot_data.save()
        
        lose_text = (
            f"К сожалению, попытки закончились😔\n"
            f"Слово было: {game['word'].upper()}\n\n"
            f"Хочешь попробовать отгадать другое слово?👀\n"
            f"Жми /start"
        )
        
        await update.message.reply_text(lose_text)
        del active_games[user_id]
        return
    
    attempt_text = (
        f"Попытка {attempt_num}/{game['max_attempts']}:\n"
        f"{' '.join(text.upper())}\n"
        f"{' '.join(result)}"
    )
    
    await update.message.reply_text(attempt_text)

def analyze_attempt(attempt: str, target_word: str) -> list:
    result = ['❌'] * 5
    target_letters = list(target_word)
    
    # Сначала проверяем точные совпадения
    for i in range(5):
        if attempt[i] == target_letters[i]:
            result[i] = "✅"
            target_letters[i] = None
    
    # Затем проверяем буквы на других позициях
    for i in range(5):
        if result[i] == "✅":
            continue
        if attempt[i] in target_letters:
            result[i] = "🔄"
            target_letters[target_letters.index(attempt[i])] = None
    
    return result

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        last_update = bot_data.admin_stats["last_update"].astimezone(TIMEZONE).strftime("%d.%m.%Y %H:%M")

VizoraX, [16.08.2025 9:11]
total_games = bot_data.admin_stats["total_games"]
        unique_players = len(bot_data.game_stats)
        avg_games = total_games / unique_players if unique_players > 0 else 0
        
        stats_text = (
            f"📊 Статистика за все время (обновлено {last_update}):\n\n"
            f"- Всего игр: {total_games}\n"
            f"- Уникальных игроков: {unique_players}\n"
            f"- Среднее количество игр: {avg_games:.1f}\n\n"
            f"Топ игроков:\n"
        )
        
        top_players = sorted(
            bot_data.game_stats.items(),
            key=lambda x: (x[1]["wins"], x[1]["games_played"]),
            reverse=True
        )
        
        for i, (user_id, stats) in enumerate(top_players, 1):
            username = f"@{stats['username']}" if stats["username"] else stats["first_name"] or f"ID {user_id}"
            stats_text += (
                f"{i}. {username}\n"
                f"Угаданных слов - {stats['wins']}\n"
                f"Всего игр - {stats['games_played']}\n\n"
            )
            if i >= 10:
                break
        
        await update.message.reply_text(stats_text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

async def stats_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        time_filter = datetime.now(TIMEZONE) - timedelta(days=30)
        recent_games = [g for g in bot_data.admin_stats["games_history"] if g["timestamp"] >= time_filter]
        
        total_games = len(recent_games)
        unique_players = len({g["user_id"] for g in recent_games})
        wins = sum(1 for g in recent_games if g["is_win"])
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        stats_text = (
            f"📊 Статистика канала за 30 дней:\n\n"
            f"- Игр: {total_games}\n"
            f"- Уникальных игроков: {unique_players}\n"
            f"- Побед: {wins} ({win_rate:.1f}%)\n\n"
            f"Последние 10 игр:\n"
        )
        
        for i, game in enumerate(reversed(recent_games[-10:]), 1):
            username = f"@{game['username']}" if game["username"] else game["first_name"] or f"ID {game['user_id']}"
            status = "Победа" if game["is_win"] else "Поражение"
            stats_text += (
                f"{i}. {username}: {game['word'].upper()} - {status} "
                f"({game['attempts']} попыток, {game['timestamp'].strftime('%d.%m %H:%M')})\n"
            )
        
        await update.message.reply_text(stats_text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

async def period_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("Использование: /period_stats ДД.ММ.ГГГГ ДД.ММ.ГГГГ")
            return
        
        start_date = datetime.strptime(context.args[0], "%d.%m.%Y").replace(tzinfo=TIMEZONE)
        end_date = datetime.strptime(context.args[1], "%d.%m.%Y").replace(tzinfo=TIMEZONE) + timedelta(days=1)
        
        period_games = [
            g for g in bot_data.admin_stats["games_history"]
            if start_date <= g["timestamp"] <= end_date
        ]
        
        total_games = len(period_games)
        unique_players = len({g["user_id"] for g in period_games})
        wins = sum(1 for g in period_games if g["is_win"])
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        stats_text = (
            f"📊 Статистика за период {context.args[0]} - {context.args[1]}:\n\n"
            f"- Игр: {total_games}\n"
            f"- Уникальных игроков: {unique_players}\n"
            f"- Побед: {wins} ({win_rate:.1f}%)\n\n"
            f"Топ игроков:\n"

VizoraX, [16.08.2025 9:11]
)
        
        player_stats = defaultdict(lambda: {"wins": 0, "games": 0})
        for game in period_games:
            player_stats[game["user_id"]]["games"] += 1
            if game["is_win"]:
                player_stats[game["user_id"]]["wins"] += 1
        
        sorted_players = sorted(
            player_stats.items(),
            key=lambda x: (x[1]["wins"], x[1]["games"]),
            reverse=True
        )
        
        for i, (user_id, stats) in enumerate(sorted_players, 1):
            user_info = next(
                (g for g in reversed(period_games) if g["user_id"] == user_id),
                {"username": None, "first_name": None}
            )
            username = f"@{user_info['username']}" if user_info["username"] else user_info["first_name"] or f"ID {user_id}"
            stats_text += (
                f"{i}. {username}\n"
                f"Угаданных слов - {stats['wins']}\n"
                f"Всего игр - {stats['games']}\n\n"
            )
            if i >= 10:
                break
        
        await update.message.reply_text(stats_text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", show_menu))
    
    # Обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Скрытые команды (не отображаются в меню)
    application.add_handler(CommandHandler("admin_stats", admin_stats))
    application.add_handler(CommandHandler("stats_channel", stats_channel))
    application.add_handler(CommandHandler("period_stats", period_stats))
    
    logger.info("Бот запущен")
    application.run_polling()

if name == "main":
    main()