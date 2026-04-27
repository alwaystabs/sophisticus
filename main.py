import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
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
# ---------------------------------------------------------------------------------------------------------------------------------------- #
psutil.virtual_memory()
# --- Настройки ---
TOKEN = "8641635572:AAFPuYvAXvjq0s_97TTbvQ7Dc1tapardLwk"  # Получи у @BotFather
PREFIX = "/"
MASTER_KEY = ""
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
    
env = get_env()
def ask_llm(prompt: str) -> str:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma-4-e4b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.75,
                    "max_tokens": 750
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["response"]
        else:
            return f"❌ Ошибка Ollama: {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return "❌ Ollama не запущен. Требуется запустить `ollama serve` в терминале"
    except Exception as e:
        return f"❌ Неизвестная ошибка: {str(e)}"

# --- Логирование (чтобы видеть ошибки) ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Создаём движок команд ---
engine = CommandEngine(PREFIX)

# --- Регистрируем команды через наш движок ---
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
    pynvml.nvmlShutdown()
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
        return "❌ Не задан вопрос. Напишите: /ask Ваш вопрос"
    try:
        if env == "pc":
            ai_status = "✅ Хост RTX A4000, запуск AI..." # AI функция вынесена, делать через subprocess - нестабильно, делаем через прямой API Ollama
            return f"Статус: {ai_status}\n----------------------------------------------------\nВопрос: {text}\n----------------------------------------------------\n**🤔 Думаю...**\n{ask_llm(text)}"
        elif env == "laptop":
            ai_status = "❌ Хост на Celeron, запуск AI невозможен" # 26.04.2026 / TODO: ответ с LLM; функция определения системы вынесена в отдельную функцию из-за ее размеров
            return f"Статус: {ai_status}, продолжение невозможно"
        else:
            ai_status = "Хост неизвестен, продолжение невозможно" # TODO: доработать список известных хостов и внесение новых значений в них
            return ai_status
    except Exception as e:
        return f"Неизвестная ошибка. {str(e)}"

# --- Обработчик команд Telegram ---
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    
    # Убираем префикс и разбиваем на команду и аргументы
    if not text.startswith(PREFIX):
        return
    
    parts = text[len(PREFIX):].split(maxsplit=1)
    cmd_name = parts[0].lower()
    args_text = parts[1] if len(parts) > 1 else ""
    
    # Выполняем команду через наш движок
    response = engine.execute(cmd_name, args_text)
    await update.message.reply_text(response, parse_mode='Markdown')

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