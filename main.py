import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from command_engine import CommandEngine
import cpuinfo
# --- Настройки ---
TOKEN = "8641635572:AAFNhNFasRZR8BAIL9cJ88c8wmFpv7i6D74"  # Получи у @BotFather
PREFIX = "/"

# --- Логирование (чтобы видеть ошибки) ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Создаём движок команд ---
engine = CommandEngine(PREFIX)

# --- Регистрируем команды через наш движок ---
@engine.register("start")
def cmd_start():
    return "Привет! Я бот. Вот мои команды:\n/help - помощь\n/status - статус"

@engine.register("help")
def cmd_help():
    return "/start - приветствие\n/status - статус\n/echo <текст> - повторить"

@engine.register("status")
def cmd_status():
    return "✅ Бот работает, GPU готов"

@engine.register("echo")
def cmd_echo(text):
    return f"Ты сказал: {text}"
@engine.register("ask")
def ai_ask():
    cpu_model = cpuinfo.get_cpu_info()['brand_raw']
    if cpu_model == 'Intel(R) Celeron(R) N5100 @ 1.10GHz':
        return "Хост на Celeron N5100, запуск AI невозможен"
    elif cpu_model == "AMD Ryzen 5 5500":
        return "Хост на A4000, запуск AI..." # 26.04.2026 / Ясное дело, что на Celeron нейронку не стартанешь



# --- Обработчик команд Telegram ---
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # Убираем префикс и разбиваем на команду и аргументы
    if not text.startswith(PREFIX):
        return
    
    parts = text[len(PREFIX):].split(maxsplit=1)
    cmd_name = parts[0].lower()
    args_text = parts[1] if len(parts) > 1 else ""
    
    # Выполняем команду через наш движок
    response = engine.execute(cmd_name, args_text)
    await update.message.reply_text(response)

# --- Обработчик обычных сообщений (не команд) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"Я не понимаю команды. Попробуй /help")

# --- Запуск бота ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(MessageHandler(filters.COMMAND, handle_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()