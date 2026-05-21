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
import os
import json
import asyncio
import re
import matplotlib # Сделать графики наконец
from datetime import datetime
import socket
# ---------------------------------------------------------------------------------------------------------------------------------------- #
last_context = []
last_llm_stats = {}
user_contexts = {}
llm_mode = {}
ADMIN_IDS = {5264908688}
psutil.virtual_memory()
maintenance = False
maintenance_message = "😓 На данный момент бот находится в тех. работах. Приносим извинения за возможные доставленные неудобства!"
TOKEN = "8641635572:AAFPuYvAXvjq0s_97TTbvQ7Dc1tapardLwk"
PREFIX = "/"
host_list = {'main_pc': "Intel(R) Celeron(R) N5100 @ 1.10GHz",
                               'main-laptop': "AMD Ryzen 5 5500"}

async def status_with_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = cmd_status()
    keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="refresh_status")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
def get_env():  # Определение хоста для решения, запускать ИИ или нет. Также будет защищать от посторонних хостов, но вряд ли это как-то поможет
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
    global last_llm_stats
    try:
        context = user_contexts.get(user_id, [])
        
        # СИСТЕМНЫЙ ПРОМПТ (инструкция для модели)
        system_prompt = (
            "Ты — полезный ассистент Sophisticus. Всегда отвечай, не форматируя текст вообще. Без тегов и специальных символов, их не должно быть вообще. Знаки препинания прошу все еще оставить."
            "Твои ответы должны быть чистыми, структурированными и безопасными."
        )
        
        # Объединяем системный промпт с вопросом пользователя
        full_prompt = f"{system_prompt}\n\nПользователь спрашивает: {prompt}"

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma-4-e4b",
                "prompt": full_prompt,
                "stream": False,
                "context": context,
                "options": {
                    "temperature": 0.75,
                    "max_tokens": 500
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
            speed = answer_tokens / \
                (eval_duration / 1_000_000_000) if eval_duration > 0 else 0

            stats_text = f"_⏱️ {duration_ms:.0f} мс | 📥 {prompt_tokens} | 📤 {answer_tokens} | ⚡ {speed:.1f} ток/сек_"
            last_llm_stats = {
            "duration_ms": duration_ms,
            "prompt_eval_count": prompt_tokens,
            "eval_count": answer_tokens,
            "tokens_per_second": speed
            }
            return data['response'], stats_text
        else:
            return f"❌ Ошибка Ollama: {response.status_code}", ""
    
    except requests.exceptions.ConnectionError:
        return "❌ Ollama не запущен", ""
    except Exception as e:
        return f"❌ Ошибка: {str(e)}", ""
def get_disk_info():
    """Собирает информацию о дисках"""
    result = []
    for part in psutil.disk_partitions():
        # Пропускаем CD-ROM и пустые
        if 'cdrom' in part.opts or part.fstype == '':
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            used_gb = usage.used // (1024**3)
            total_gb = usage.total // (1024**3)
            percent = usage.percent
            emoji = "🟢" if percent < 70 else "🟡" if percent < 90 else "🔴"
            result.append(f"{part.device} ({part.fstype}): {used_gb}/{total_gb} ГБ ({percent}%) {emoji}")
        except PermissionError:
            result.append(f"{part.device}: ❌ нет доступа")
    return "\n".join(result) if result else "❌ Не удалось получить данные"

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO,
                    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()])

def clean_html_for_telegram(text: str) -> str:
    """
    Превращает HTML от модели в форматированный текст для Telegram.
    Заменяет теги <b>, <i>, <code>, <pre> и превращает списки <ul>/<li> в текст с маркерами.
    """
    # 1. Заменяем поддерживаемые теги (жирный, курсив, код)
    text = re.sub(r'<b>(.*?)</b>', r'<b>\1</b>', text, flags=re.DOTALL)
    text = re.sub(r'<i>(.*?)</i>', r'<i>\1</i>', text, flags=re.DOTALL)
    text = re.sub(r'<code>(.*?)</code>', r'<code>\1</code>', text, flags=re.DOTALL)
    text = re.sub(r'<pre>(.*?)</pre>', r'<pre>\1</pre>', text, flags=re.DOTALL)
    
    # 2. Превращаем абзацы <p> в переносы строки
    text = re.sub(r'<p>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL)
    
    # 3. Превращаем ненумерованные списки в текст с маркерами
    # Находим все блоки <ul>...</ul>
    ul_pattern = re.compile(r'<ul>(.*?)</ul>', re.DOTALL)
    def replace_ul(match):
        li_content = match.group(1)
        # Каждый <li> заменяем на маркер • и перенос строки
        li_content = re.sub(r'<li>(.*?)</li>', r'• \1\n', li_content, flags=re.DOTALL)
        return li_content
    
    text = ul_pattern.sub(replace_ul, text)
    
    # 4. Удаляем все оставшиеся HTML-теги на всякий случай
    text = re.sub(r'<[^>]+>', '', text)
    
    # 5. Убираем множественные переносы строк
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
def cmd_status():
    # --- Время работы ---
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.now()
    uptime_delta = now - boot_time
    days = uptime_delta.days
    hours = uptime_delta.seconds // 3600
    minutes = (uptime_delta.seconds % 3600) // 60
    uptime_str = f"{days}д {hours}ч {minutes}м" if days > 0 else f"{hours}ч {minutes}м"
    
    # --- Сеть ---
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    # --- GPU через pynvml ---
    gpu_section = "❌ Не удалось получить данные GPU"
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        
        # Основные данные
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        gpu_fan = pynvml.nvmlDeviceGetFanSpeed(handle)
        power = pynvml.nvmlDeviceGetPowerUsage(handle) // 1000
        
        # Утилизация
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_load = util.gpu
        mem_load = util.memory
        
        # Память
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        mem_total = mem.total // (1024**2)
        mem_used = mem.used // (1024**2)
        mem_free = mem.free // (1024**2)
        
        # Частоты
        gpu_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
        
        # Драйвер
        try:
            driver_version = pynvml.nvmlSystemGetDriverVersion()
        except:
            driver_version = "N/A"
        
        # Процессы на GPU
        processes_info = []
        try:
            processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
            for proc in processes[:3]:
                try:
                    proc_name = pynvml.nvmlSystemGetProcessName(proc.pid)
                except:
                    proc_name = f"PID:{proc.pid}"
                proc_mem = proc.usedGpuMemory // (1024**2)
                processes_info.append(f"   • {proc_name}: {proc_mem} МБ")
        except:
            processes_info = ["   • (нет доступа)"]
        
        gpu_section = f"""🖥️ **GPU** ({gpu_name})
├ 🌡️ {gpu_temp}°C | ⚡ {power} Вт | 🌀 {gpu_fan}%
├ ⚙️ Загрузка: GPU {gpu_load}% | MEM {mem_load}%
├ 💾 Память: {mem_used}/{mem_total} МБ (свободно {mem_free} МБ)
├ ⚡ Частота GPU: {gpu_clock} МГц
├ 🔧 Драйвер: {driver_version}
└ 🔄 Процессы на GPU:
{chr(10).join(processes_info)}"""
        pynvml.nvmlShutdown()
    except Exception as e:
        gpu_section = f"❌ Ошибка GPU: {str(e)}"
    
    # --- CPU ---
    cpu_name = cpuinfo.get_cpu_info()['brand_raw']
    cpu_freq_info = psutil.cpu_freq()
    cpu_freq = f"{cpu_freq_info.current:.0f}" if cpu_freq_info is not None else "N/A"
    cpu_percent = psutil.cpu_percent()
    cpu_per_core = psutil.cpu_percent(percpu=True)
    core_loads = ", ".join([f"{p}%" for p in cpu_per_core])
    
    cpu_section = f"""🧠 **CPU** ({cpu_name})
├ 📊 Загрузка: {cpu_percent}%
├ 📈 По ядрам: {core_loads}
└ ⚡ Частота: {cpu_freq} МГц"""
    
    # --- RAM ---
    ram = psutil.virtual_memory()
    ram_total = ram.total // (1024**3)
    ram_used = ram.used // (1024**3)
    ram_free = ram.free // (1024**3)
    ram_percent = ram.percent
    
    ram_section = f"""💾 **RAM**
├ 📦 Всего: {ram_total} ГБ
├ 🔋 Занято: {ram_used} ГБ ({ram_percent}%)
└ 📀 Свободно: {ram_free} ГБ"""
    
    # --- Диски ---
    disk_section = f"💽 **Диски**\n{get_disk_info()}"
    
    # --- Система ---
    system_section = f"""⏱️ **Система**
├ Бот работает: с момента запуска
└ Сервер загружен: {uptime_str}
🌐 **Сеть**
└ IP: {local_ip} ({hostname})"""
    
    # Собираем всё вместе
    return f"""📊 **Sophisticus — Статус сервера**

{gpu_section}

{cpu_section}

{ram_section}

{disk_section}

{system_section}"""

engine = CommandEngine(PREFIX)
# ----------------------------------------------------------------------------------------------------------------------------------------
@engine.register("cmd_list")
def show_full_cmd():
    return """
/stat - статистика компьютера (сервера)
/ai_temp [value] - изменить температуру модели (вроде бы бесполезная функция)
/stats_answer - статистика последнего ответа модели
/reload - Перезапустить Ollama
/echo [prompt] - обычное эхо
/source - проект на GitHub
/weather [city] - погода в городе
/ask - отправить запрос Gemma 4
/logs - 100 последних строк лога
/llm - режим ИИ (все сообщения направляются ИИ)
/stop - выключить его
/start - приветственное сообщение
/shutdown - ввести режим тех. работ
/wake - выключить его
"""
@engine.register("stat")
def return_status():
    return cmd_status()
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
@engine.register("stats_answer")
def check_last_message():
    if not last_llm_stats:
        return "📊 Нет данных. Сначала отправьте запрос через /ask"
    
    return f"""📊 *Статистика последнего запроса к модели*

⏱️ *Время генерации:* {last_llm_stats.get('duration_ms', 0):.0f} мс
📥 *Токенов в запросе:* {last_llm_stats.get('prompt_eval_count', 0)}
📤 *Токенов в ответе:* {last_llm_stats.get('eval_count', 0)}
⚡ *Скорость:* {last_llm_stats.get('tokens_per_second', 0):.1f} токен/сек"""
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
@engine.register("source")
def show_source():
    return "Проект Sophisticus - open-source проект, свободный и бесплатный.\nРепозиторий GitHub: github.com/alwaystabs/sophisticus"
@engine.register("weather")
def cmd_weather(city: str = ""): # Город по умолчанию — Минск
    api_key = "4949884651f9c4496562601a52dd2b07"

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            return f"❌ Город `{city}` не найден. Проверь название."

        # Вытаскиваем нужные данные из ответа
        weather_desc = data["weather"][0]["description"]
        temp = round(data["main"]["temp"])
        feels_like = round(data["main"]["feels_like"])
        humidity = data["main"]["humidity"]

        return (f"📍 *{city.title()}*\n"
                f"🌡️ *{temp}°C* (ощущается как {feels_like}°C)\n"
                f"🌤️ {weather_desc.capitalize()}\n"
                f"💧 Влажность: {humidity}%")

    except Exception as e:
        return f"❌ Не удалось получить погоду: {e}"
@engine.register("rate")
def rate(v1, v2):
    # доделать валютность
    return "🔧 В разработке!"
# ----------------------------------------------------------------------------------------------------------------------------------------
async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    global maintenance
    maintenance = True
    await update.message.reply_text("🔧 Режим техобслуживания активирован.")

async def wake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    global maintenance
    maintenance = False
    await update.message.reply_text("✅ Бот снова в строю!")
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
async def llm_mode_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    llm_mode[user_id] = True
    await update.message.reply_text("🤖 Режим диалога с ИИ включён. Пишите любые сообщения, модель будет отвечать.")

async def llm_mode_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
     user_id = update.effective_user.id
     llm_mode.pop(user_id, None)
     await update.message.reply_text("🔘 Режим диалога выключен. Используйте /ask для вопросов.")
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global maintenance  # ← обязательно
    
    text = update.message.text.strip()
    
    if not text.startswith(PREFIX):
        return
    
    parts = text[len(PREFIX):].split(maxsplit=1)
    cmd_name = parts[0].lower()
    args_text = parts[1] if len(parts) > 1 else ""
    
    if maintenance and cmd_name != "wake":
        try:
            with open("maintenance.png", "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=maintenance_message,
                    parse_mode='HTML'
                )
        except FileNotFoundError:
            await update.message.reply_text(maintenance_message)
        return 
    
    
    response = await asyncio.to_thread(engine.execute, cmd_name, args_text)
    await update.message.reply_text(response, parse_mode='HTML')
    await update.message.reply_text(response)
async def stat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
     query = update.callback_query
     await query.answer()

     if query.data == "refresh_status":
        new_text = cmd_status()  
        await query.edit_message_text(
            text=new_text,
            reply_markup=query.message.reply_markup, 
            parse_mode='Markdown'
        )
 # --- Обработчик обычных сообщений (не команд) ---
 
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
     user_id = update.effective_user.id
     text = update.message.text

     # Если режим диалога включён
     if llm_mode.get(user_id):
         answer, stats = await asyncio.to_thread(ask_llm(text, user_id))
         await update.message.reply_text(f"{answer}\n\n{stats}")
     else:
         await update.message.reply_text(f"❓ Я не понимаю команды. Используйте /help или /llm для диалога с ИИ.")
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    
    text = update.message.text
    if text.startswith("/ask"):
        prompt = text[5:].strip()  
    else:
        prompt = text.strip()
    
    if not prompt:
        await update.message.reply_text("❌ Не задан вопрос. Напишите: /ask Ваш вопрос")
        return
    
    if env != "pc":
        await update.message.reply_text("❌ Запуск AI возможен только на ПК с A4000")
        return
    
    thinking_msg = await update.message.reply_text("🤔 Думаю...")
    
    answer, stats = ask_llm(prompt, user_id)

    clean_answer = clean_html_for_telegram(answer)
    
    await thinking_msg.edit_text(f"{clean_answer}\n\n{stats}", parse_mode='HTML')
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок, логирует их и отправляет уведомление админу"""
    error = context.error
    print(f"❌ Ошибка: {error}")
    
    with open("errors.log", "a", encoding="utf-8") as f:
        from datetime import datetime
        f.write(f"[{datetime.now()}] {error}\n")
        if update:
            f.write(f"  Update: {update}\n")
    
    # Отправляем админу (если есть update)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Произошла внутренняя ошибка. Администратор уже уведомлён."
            )
        except:
            pass
    try:
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"‼️  *Ошибка в боте*\n```\n{str(error)[:500]}\n```",
                parse_mode='Markdown'
            )
    except:
        pass  # если не отправилось — не страшно
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.replace("/ask", "", 1).strip()
    
    if not text:
        await update.message.reply_text("❌ Не задан вопрос")
        return
    if env != "pc":
        await update.message.reply_text("❌ Запуск AI возможен только на ПК с A4000")
        return
    
    answer, stats = ask_llm(text, user_id)
    await update.message.reply_text(f"{answer}\n\n{stats}")
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("hello.png", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption="""✨ Вас приветствует Sophisticus — исследовательский проект-полигон, объединяющий приватное взаимодействие с LLM, мониторинг железа и агентное управление.

🤝 Пользовательское соглашение (честно и прозрачно)

Используя бота, вы принимаете условия:
1. Бот не хранит историю диалогов на сервере
2. Все запросы обрабатываются анонимно
3. Модель не обучается на ваших сообщениях

Если вы не доверяете — вы всегда можете проверить код в открытом репозитории.

---

📋 Доступные команды (основные)

• /ask <вопрос> — задать вопрос локальной языковой модели (Gemma 4 E4B)
• /stat — полная статистика сервера (GPU, CPU, RAM, диски, сеть)
• /weather <город> — узнать погоду
• /logs — последние строки лога (доступно администратору)
• /source — исходный код проекта (GitHub)

Полный список команд: /help

---

🛡️ И помните: Империя заботится о вас!

— Sophisticus CEO
"""
)
# --- Запуск бота ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("llm", llm_mode_on))
    app.add_handler(CommandHandler("stop", llm_mode_off))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("shutdown", shutdown_command))
    app.add_handler(CommandHandler("wake", wake_command))
    app.add_handler(CommandHandler("statb", status_with_button))
    app.add_handler(CallbackQueryHandler(stat_callback, pattern="refresh_status"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    app.add_handler(MessageHandler(filters.COMMAND, handle_command))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()