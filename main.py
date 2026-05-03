import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from command_engine import CommandEngine
import cpuinfo
import psutil
import pynvml
import platform
import subprocess
import requests
import markdown
import os
import re
import json
import asyncio
import matplotlib
# ---------------------------------------------------------------------------------------------------------------------------------------- #
last_context = []
last_llm_stats = {}
user_contexts = {}
ADMIN_IDS = {5264908688}
psutil.virtual_memory()
TOKEN = "8641635572:AAFPuYvAXvjq0s_97TTbvQ7Dc1tapardLwk"
PREFIX = "/"
host_list = {'main_pc': "Intel(R) Celeron(R) N5100 @ 1.10GHz", 'main-laptop': "AMD Ryzen 5 5500"}
def get_env(): # Определение хоста для решения, запускать ИИ или нет. Также будет защищать от посторонних хостов, но вряд ли это как-то поможет
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True)
        has_nvidia = result.returncode == 0
    except:
        has_nvidia = False
    if platform.system() == "Windows" and has_nvidia:
        return "pc"
    else:
        return "laptop"
def format_stats(stats: dict) -> str:
    return f"""📊 *metadata:*
time: {stats['duration_ms']:.2f}
prompt_token_count: {stats['prompt_eval_count']}
answer_token_count: {stats['eval_count']}
generation_speed: {stats['tokens_per_second']:.1f} токен/сек"""
env = get_env()
def ask_llm(prompt: str, user_id: int) -> tuple:
    """Возвращает (ответ_модели, статистика)"""
    try:
        # Получаем контекст пользователя
        context = user_contexts.get(user_id, [])
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma-4-e4b",
                "prompt": prompt,
                "stream": False,
                "context": context,
                "options": {
                    "temperature": 0.75,
                    "max_tokens": 750
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            # Сохраняем новый контекст
            user_contexts[user_id] = data.get("context", [])
            
            # Статистика
            duration_ms = data.get("total_duration", 0) / 1_000_000
            prompt_tokens = data.get("prompt_eval_count", 0)
            answer_tokens = data.get("eval_count", 0)
            eval_duration = data.get("eval_duration", 0)
            speed = answer_tokens / (eval_duration / 1_000_000_000) if eval_duration > 0 else 0
            
            stats_text = f"_⏱️ {duration_ms:.0f} мс | 📥 {prompt_tokens} | 📤 {answer_tokens} | ⚡ {speed:.1f} ток/сек_"
            
            return data['response'], stats_text
        else:
            return f"❌ Ошибка Ollama: {response.status_code}", ""
            
    except requests.exceptions.ConnectionError:
        return "❌ Ollama не запущен", ""
    except Exception as e:
        return f"❌ Ошибка: {str(e)}", ""
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()])

engine = CommandEngine(PREFIX)
# ---------------------------------------------------------------------------------------------------------------------------------------- #
@engine.register("start")
def cmd_start():
    return """**Вас приветствует исследовательский проект-полигон Sophisticus, направленный на приватное и автономное взаимодействие с LLM, а также ИИ-агент с мониторингом и управлением.\n
      **ВАЖНОЕ СООБЩЕНИЕ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ:**\n
      Пользователи проекта Sophisticus! Мы уважаем ваше личное пространство и защищаем ваши сообщения. Мы не можем прочитать ваш диалог. Никто из нас.
Но мы прямо говорим: мы идём на жертву: модель не запоминает, о чём вы её спрашивали ранее. Никакой истории, никаких «я помню, ты говорил...».
Пожалуйста, отнеситесь к этому с пониманием. Нам важна ваша приватность. Мы активно работаем над улучшением этой системы и получением наилучшего опыта сотрудничества с проектом!
И помните: Империя заботится о вас!
— Sophisticus CEO
"""

@engine.register("help")
def cmd_help():
    return "/status - **статус**\n/echo <текст> - повторить\n/ask <текст> - **задать вопрос новейшей модели Gemma 4**"
@engine.register("stat")
def pc_stats():
    pynvml.nvmlInit()
    sensor = pynvml.NVML_TEMPERATURE_GPU
    device_count = pynvml.nvmlDeviceGetCount()
    
    # Собираем данные GPU для всех карт
    gpu_info = []
    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        gpu_fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
        gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, sensor)
        gpu_info.append(f"Карта {i+1}: {gpu_name}, {gpu_temp}°C, кулер {gpu_fan_speed}%")
    
    # Собираем данные CPU (один раз, вне цикла)
    cpu_name = cpuinfo.get_cpu_info()['brand_raw']
    cpu_freq_info = psutil.cpu_freq()
    cpu_freq = cpu_freq_info.current if cpu_freq_info is not None else "N/A"
    cpu_percent = psutil.cpu_percent()
    
    # Данные RAM
    ram_load = psutil.virtual_memory().used / (1024**3)
    ram_available = psutil.virtual_memory().available / (1024**3)
    ram_total = psutil.virtual_memory().total / (1024**3)
    
    # Формируем вывод
    if device_count == 0:
        gpu_text = "❌ Не обнаружено"
    elif device_count == 1:
        gpu_text = f"{gpu_info[0]}"
    else:
        gpu_text = "Обнаружено несколько карт:\n" + "\n".join(gpu_info)
    return f"""
    📹 **GPU**:
    {gpu_text}
    🖥️ **CPU**:
    Название: {cpu_name}
    Частота: {cpu_freq} МГц
    Загрузка: {cpu_percent}%
    
    💾 **RAM**:
    Всего: {ram_total:.1f} ГБ
    Занято: {ram_load:.1f} ГБ
    Доступно: {ram_available:.1f} ГБ
    """
@engine.register("cpu")
def show_cpu():
    cpu_name = cpuinfo.get_cpu_info()['brand_raw']
    cpu_freq_info = psutil.cpu_freq()
    cpu_freq = cpu_freq_info.current if cpu_freq_info is not None else "N/A"
    cpu_percent = psutil.cpu_percent()
    return f"""
🖥️ Стата CPU:
Название: {cpu_name}
Загрузка (%): {cpu_percent}
Частота: {cpu_freq} (Если здесь N/A, значит процессор не поддерживается модулем pycpuinfo)
"""
@engine.register("gpu")
def show_gpu():
    gpu_info = []
    pynvml.nvmlInit()
    sensor = pynvml.NVML_TEMPERATURE_GPU
    device_count = pynvml.nvmlDeviceGetCount()
    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        gpu_fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
        gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, sensor)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        power_mw = pynvml.nvmlDeviceGetPowerUsage(handle)
        power_w = power_mw // 1000
        gpu_info.append(
        f"🎮 **{gpu_name}**\n"
        f"🌡️ {gpu_temp}°C | 🌀 {gpu_fan_speed}% | ⚡ {power_w} Вт\n"
        f"💾 Видеопамять:\n"
        f"   Всего: {mem.total // (1024**2)} МБ\n"
        f"   Занято: {mem.used // (1024**2)} МБ\n"
        f"   Свободно: {mem.free // (1024**2)} МБ"
    )
    pynvml.nvmlShutdown()
    if not gpu_info:
        return "❌ GPU не обнаружены"

    return "\n\n".join(gpu_info)
@engine.register("ai_temp")
def change_ai_temp(value):
    if os.path.exists('current_temp.json') == False:
        default_config = {"temperature": 0.75}
        with open('current_temp.json', 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return "Файл не существует. Создан файл current_temp.json с дефолтным значением температуры модели 0.75"
    try:
        if value == "":
            return "Допустимы только числа"
        if value == None:
            return "Введите значение!"
        temp_value = float(value)
        if not (0.1 <= temp_value <= 2.0):
            return "Доступно значение в пределах разумного (0.1-2.0). Текст недопустим"
        with open('current_temp.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        config["temperature"] = float(value)
        with open('current_temp.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return f"Изменено на {value}"
    except FileNotFoundError as e:
        return f"Файл не найден. {str(e)}"
    except json.JSONDecodeError as e:
        return f"Битый файл. {str(e)}"
@engine.register("status")
def cmd_status():
    return "✅ Бот работает, GPU готов"
@engine.register("stats_answer")
def check_last_message():
    if not last_llm_stats:
        return "📊 Нет данных. Сначала отправьте запрос через /ask"
    
    return f"""📊 *Статистика последнего запроса к модели*

⏱️ *Время генерации:* {last_llm_stats.get('duration_ms', 0):.0f} мс
📥 *Токенов в запросе:* {last_llm_stats.get('prompt_eval_count', 0)}
📤 *Токенов в ответе:* {last_llm_stats.get('eval_count', 0)}
⚡ *Скорость:* {last_llm_stats.get('tokens_per_second', 0):.1f} токен/сек"""
# @engine.register("logs")
# def cmd_logs():
#     try:
#         with open("bot.log", "r", encoding='utf-8') as f:
#             lines = f.readlines()
        
#         # Берём последние 30 строк (или сколько влезет в 4000 символов)
#         log_text = "".join(lines[-30:])
        
#         # Если текст длиннее 4000 символов, обрезаем
#         if len(log_text) > 3900:
#             log_text = log_text[-3900:] + "\n\n...(обрезано)"
        
#         return f"📋 *Последние строки лога:*\n```\n{log_text}\n```"
#     except Exception as e:
#         return f"❌ Ошибка при чтении лога: {e}"
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🔒 Доступ запрещён. Только для администратора.")
        return
    
    try:
        with open("bot.log", "r", encoding='utf-8') as f:
            lines = f.readlines()
        log_text = "".join(lines[-30:])
        if len(log_text) > 3900:
            log_text = log_text[-3900:] + "\n\n...(обрезано)"
        await update.message.reply_text(f"📋 *Последние строки лога:*\n```\n{log_text}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
@engine.register("reload")
def model_reload():
    result = subprocess.run(['ollama', 'restart'], capture_output=True, encoding='utf-8')
    if result.returncode == 0:
        return f"Ollama перезапустилась успешно! {result.stdout}"
    else:
        return f"Ollama не перезапустилась: {result.stderr}"
@engine.register("echo")
def cmd_echo(text):
    return f"Ты сказал: {text}"
@engine.register("ask")
def ai_ask(text=None):
    if text is None or text.strip() == "":
        return "❌ Не задан вопрос"
    if env != "pc":
        return "❌ Запуск AI возможен только на ПК с A4000"
    answer, stats = ask_llm(text, 0)
    return f"{answer}\n\n{stats}"
@engine.register("source")
def show_source():
    return "**Проект Sophisticus - open-source проект, свободный и бесплатный**.\nРепозиторий GitHub: github.com/alwaystabs/sophisticus"
# ---------------------------------------------------------------------------------------------------------------------------------------- #
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    
    if not text.startswith(PREFIX):
        return
    
    parts = text[len(PREFIX):].split(maxsplit=1)
    cmd_name = parts[0].lower()
    args_text = parts[1] if len(parts) > 1 else ""
    
    # Выполняем команду через наш движок
    response = await asyncio.to_thread(engine.execute, cmd_name, args_text)
    await update.message.reply_text(response)
async def stat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "refresh_gpu":
        new_text = show_gpu()
        await query.edit_message_text(text=new_text, reply_markup=query.message.reply_markup)
    elif query.data == "refresh_stat":
        new_text = pc_stats()
        await query.edit_message_text(text=new_text, reply_markup=query.message.reply_markup)
# --- Обработчик обычных сообщений (не команд) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"Я не понимаю команды. Попробуй /help")
async def gpu_with_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = show_gpu()  # твоя существующая функция
    keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="refresh_gpu")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
# --- Запуск бота ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(MessageHandler(filters.COMMAND, handle_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(stat_callback, pattern="refresh_gpu"))
    app.add_handler(CallbackQueryHandler(stat_callback, pattern="refresh_stat"))
    app.add_handler(CommandHandler("gpub", gpu_with_button))
    app.add_handler(CommandHandler("logs", logs_command))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()