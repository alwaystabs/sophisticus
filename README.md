# Sophisticus 🤖

**Sophisticus** is a Telegram bot that serves as an interface to a local Large Language Model (LLM) on your computer. It gives you full control: send AI queries, monitor system hardware (GPU, CPU, RAM, disks), manage operational modes, and even switch the bot to maintenance mode.

---

## 🚀 Features

- 🧠 **Local AI** — Send queries to the `Gemma 4 E4B` model via `/ask`. Works completely offline; your data never leaves your machine.
- 📊 **System Monitoring** — The `/status` command shows GPU temperature and load, CPU stats, RAM usage, disk health, and network info.
- 🔧 **Management** — Adjust model temperature (`/ai_temp`), restart Ollama (`/reload`), and enable maintenance mode (`/shutdown`).
- 🌐 **External APIs** — Get current weather (`/weather`) and exchange rates (coming soon).
- 🛡️ **Privacy** — The bot does not store chat history. The code is open, so you can verify its security.

---

## 📋 Commands

### Core
- `/start` — Welcome message with project rules.
- `/help` — List of commands.
- `/cmd_list` — Full list of all commands.
- `/status` — Detailed server statistics (GPU, CPU, RAM, disks, network).

### AI & Model Management
- `/ask [question]` — Ask the local language model.
- `/ai_temp [value]` — Change model "temperature" (creativity).
- `/stats_answer` — Statistics of the last model request.
- `/reload` — Restart Ollama.

### Admin
- `/shutdown` — Switch the bot to maintenance mode.
- `/wake` — Exit maintenance mode.
- `/logs` — Show recent log entries.
- `/source` — Link to the source code (this repository).

### Other
- `/echo [text]` — Simple echo command for testing.
- `/weather [city]` — Get current weather.
- `/llm` — Enable dialog mode (all messages go to the model).
- `/stop` — Disable dialog mode.

> **Important:** Commands `/shutdown`, `/wake`, and `/logs` are available only to the admin specified in `config.py`.

---

## 🛠️ Installation & Setup

### 1. Install Ollama
Download and install [Ollama](https://ollama.com) for Windows. Then, pull the model:
```bash
ollama pull gemma-4-e4b
```

### 2. Clone the Repository
```bash
git clone https://github.com/alwaystabs/sophisticus.git
cd sophisticus
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure `config.py`
Create a `config.py` file in the project root with the following content:
```python
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_ID = {123456789}  # Your Telegram user ID
API_WEATHER_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
```
- Get your bot token from [@BotFather](https://t.me/BotFather).
- Find your Telegram user ID via [@userinfobot](https://t.me/userinfobot).
- Get your weather API key from [OpenWeatherMap](https://openweathermap.org/api).

### 5. Run the Bot
```bash
python main.py
```

---

## 🤝 Contributing

Contributions are welcome! If you find a bug or have a feature idea:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

---

## 📜 License

Distributed under the MIT License. See the `LICENSE` file for more information.

---

## 📬 Contact

Author: [alwaystabs](https://github.com/alwaystabs)  
Project Link: [https://github.com/alwaystabs/sophisticus](https://github.com/alwaystabs/sophisticus)

## Security

Please review our [Security Policy](SECURITY.md) for responsible disclosure guidelines.