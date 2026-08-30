# MyJDownloader Telegram Bot

A Telegram bot that lets you send download links to [MyJDownloader](https://my.jdownloader.org/) and get the finished file back directly in your chat.

Send a URL to the bot, it queues the download in JDownloader, tracks progress with a live-updating message, and uploads the resulting file back to Telegram once it's done.

## Features

- 📥 Add downloads to JDownloader just by sending a URL to the bot
- 🏷️ Optional custom file name (`<url> <filename>`)
- 📊 Live progress updates (percentage, size, status) in Telegram
- 📤 Automatic upload of the finished file back to the chat
- 🔒 Optional chat allow-list (`ALLOWED_CHAT_IDS`) to restrict who can use the bot
- 🐳 Fully containerized with Docker Compose (bot + JDownloader + Mini App API)
- 📱 A Telegram Mini App API (`api/`) exposing the same functionality (queue, accounts, duplicates) over HTTP for a future graphical web UI inside Telegram

## Tech Stack

- [Python 3.12](https://www.python.org/)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 20.7
- [FastAPI](https://fastapi.tiangolo.com/) — Mini App API
- [myjdapi](https://github.com/mmarquezs/My.Jdownloader-API-Library) — MyJDownloader API client
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment variable loading
- Docker & Docker Compose

## Project Structure

```
.
├── docker-compose.yml       # Orchestrates jdownloader, bot, and api containers
├── downloads/               # Shared volume where finished downloads land
├── shared/                  # Code shared by bot/ and api/ (JDownloader service, history, utils)
│   ├── config.py
│   ├── data/                 # DownloadJob model + duplicate-download history
│   ├── services/             # MyJDownloader API integration
│   └── utils/                # Formatters, validators, file helpers, platform detection
├── bot/                     # Telegram bot (python-telegram-bot)
│   ├── main.py              # Application entry point
│   ├── config.py            # Bot-specific env vars (re-exports shared/config.py)
│   ├── handlers/             # Telegram command/message handlers
│   ├── tests/                # Unit test suite (pytest)
│   ├── Dockerfile
│   └── requirements.txt
└── api/                     # Mini App API (FastAPI)
    ├── main.py              # FastAPI app entry point
    ├── config.py            # API-specific env vars
    ├── auth.py               # Telegram Mini App initData validation
    ├── routers/              # /api/queue, /api/accounts endpoints
    ├── tests/                # Unit test suite (pytest)
    ├── Dockerfile
    └── requirements.txt
```

## Prerequisites

- Docker and Docker Compose
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A [MyJDownloader](https://my.jdownloader.org/) account with a device set up

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/HackproTm/myjdownloader-bot.git
cd myjdownloader-bot
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
MYJD_EMAIL=your_myjdownloader_email
MYJD_PASSWORD=your_myjdownloader_password
MYJD_DEVICE_NAME=MyJDownloader
ALLOWED_CHAT_IDS=123456789,987654321
POLL_INTERVAL=10
MAX_FILE_SIZE_MB=50
```

| Variable            | Required | Default            | Description                                                    |
| -------------------- | :------: | ------------------- | ---------------------------------------------------------------- |
| `TELEGRAM_TOKEN`     |    ✅    | —                   | Telegram bot token from BotFather                                |
| `MYJD_EMAIL`         |    ✅    | —                   | MyJDownloader account email                                       |
| `MYJD_PASSWORD`      |    ✅    | —                   | MyJDownloader account password                                    |
| `MYJD_DEVICE_NAME`   |    ❌    | machine hostname    | Name of the JDownloader device to connect to                     |
| `ALLOWED_CHAT_IDS`   |    ❌    | *(empty = anyone)*  | Comma-separated Telegram chat IDs allowed to use the bot          |
| `POLL_INTERVAL`      |    ❌    | `10`                | Seconds between download status checks                           |
| `MAX_FILE_SIZE_MB`   |    ❌    | `50`                | Maximum file size (MB) the bot will upload back to Telegram       |

### 3. Run with Docker Compose

```bash
docker compose up -d --build
```

This starts two containers:
- `jdownloader` — the JDownloader instance
- `bot` — the Telegram bot

### 4. Start chatting

Open your bot in Telegram and send `/start`, then send it a download link.

## Usage

```
https://example.com/file.zip
https://example.com/file.zip my_custom_name.zip
```

| Command   | Description                       |
| --------- | ---------------------------------- |
| `/start`  | Show the welcome message and usage |
| `/help`   | Same as `/start`                   |

## Development

### Setup

```bash
# Bot
cd bot
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt

# Mini App API (separate venv, Python 3.12 recommended)
cd /api
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt
```

### Running tests

```bash
cd bot && source .venv/bin/activate && python -m pytest -q
cd api && source .venv/bin/activate && python -m pytest -q
```

### Code style

This project uses 2-space indentation for Python code, enforced via [yapf](https://github.com/google/yapf) (`.style.yapf` at the repo root) and [.editorconfig](.editorconfig).

```bash
yapf -i -r --exclude '*/.venv/*' --exclude '*/__pycache__/*' bot/ shared/ api/
```

### Linting

Static checks (unused imports, undefined names, common bugs) run via [ruff](https://github.com/astral-sh/ruff) (`pyproject.toml` at the repo root, covers `bot/`, `shared/`, and `api/`).

```bash
ruff check .
```

## License

This project does not currently specify a license.
