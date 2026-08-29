# MyJDownloader Telegram Bot

A Telegram bot that lets you send download links to [MyJDownloader](https://my.jdownloader.org/) and get the finished file back directly in your chat.

Send a URL to the bot, it queues the download in JDownloader, tracks progress with a live-updating message, and uploads the resulting file back to Telegram once it's done.

## Features

- 📥 Add downloads to JDownloader just by sending a URL to the bot
- 🏷️ Optional custom file name (`<url> <filename>`)
- 🎛️ When a link offers multiple files/resolutions (e.g. a YouTube video with several
  qualities, audio-only, subtitles, thumbnail), the bot asks you which one to download
- 🏷️ Package names in JDownloader are tagged with the detected platform (YouTube, Instagram, X, Facebook, etc.)
- 📊 Live progress updates (percentage, size, status) in Telegram
- 📤 Automatic upload of the finished file back to the chat
- 📋 Queue management commands (`/queue`, `/list`, `/status`, `/remove`) with duplicate-download detection
- 🔒 Optional chat allow-list (`ALLOWED_CHAT_IDS`) to restrict who can use the bot
- 🐳 Fully containerized with Docker Compose (bot + JDownloader)

## Tech Stack

- [Python 3.15](https://www.python.org/)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 20.7
- [myjdapi](https://github.com/mmarquezs/My.Jdownloader-API-Python-Library) — MyJDownloader API client
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment variable loading
- Docker & Docker Compose

## Project Structure

```
.
├── docker-compose.yml       # Orchestrates the bot and JDownloader containers
├── downloads/               # Shared volume where finished downloads land
└── bot/
    ├── main.py              # Application entry point
    ├── config.py            # Environment-based configuration
    ├── data/                # Data models (DownloadJob, etc.)
    ├── services/             # MyJDownloader API integration
    ├── handlers/             # Telegram command/message handlers
    ├── utils/                # Formatters, validators, file helpers, logging
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
git clone <repository-url>
cd myjdownload-app
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

### Queue management

```
/queue <url> [name] [force]   Add a download to the queue (like sending a plain URL)
/list                         Show the queue with download percentage
/status                       Show the queue with status text (Name, Status, URL)
/remove <name>                Remove a download from the queue/JDownloader and delete its local file
```

Send `/queue` with no arguments and the bot will ask you for the URL (validating it looks like a
real link) and then for a file name (send `-` to use the default one).

If a URL or file name was already queued before, `/queue` asks you (with buttons) whether to
download it again or, if the file is still on disk, resend it straight away without re-downloading.
This history — including the resulting file path once a download finishes — is stored in
`downloads/.bot_data/history.json` and survives container restarts. You can still force a
re-download without the prompt by adding `force` at the end: `/queue <url> <name> force`.

When a link offers more than one file or quality (e.g. a YouTube video with several resolutions,
audio-only, thumbnail, subtitles), the bot shows a button per option with an icon and description
(🎬 video, 🎵 audio, 🖼 thumbnail, 📝 subtitles, plus resolution/bitrate when available) so you can
pick exactly what you want.

### Premium accounts

Some hosts (Instagram, YouTube, X, Facebook, etc.) require an authenticated account to work in JDownloader. Manage them directly from Telegram:

```
/accounts                                    List configured accounts
/addaccount <hoster> <username> <password>   Add or update an account (e.g. /addaccount instagram.com myuser mypass)
/removeaccount <uuid>                        Remove an account (uuid shown by /accounts)
```

The `/addaccount` message is deleted immediately after processing so the password doesn't linger in the chat history.

| Command   | Description                       |
| --------- | ---------------------------------- |
| `/start`  | Show the welcome message and usage |
| `/help`   | Same as `/start`                   |

## Development

### Setup

```bash
cd bot
python -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt
```

### Running tests

```bash
cd bot
source .venv/bin/activate
python -m pytest -q
```

### Code style

This project uses 2-space indentation for Python code, enforced via [yapf](https://github.com/google/yapf) (`bot/.style.yapf`) and [.editorconfig](.editorconfig).

```bash
cd bot
source .venv/bin/activate
yapf -i -r --exclude '.venv/*' --exclude '__pycache__/*' .
```

### Linting

Static checks (unused imports, undefined names, common bugs) run via [ruff](https://github.com/astral-sh/ruff) (`bot/pyproject.toml`).

```bash
cd bot
source .venv/bin/activate
ruff check .
```

## License

This project does not currently specify a license.
