# MyJDownloader Telegram Bot

A Telegram bot that lets you send download links to [MyJDownloader](https://my.jdownloader.org/) and get the finished file back directly in your chat.

Send a URL to the bot, it queues the download in JDownloader, tracks progress with a live-updating message, and uploads the resulting file back to Telegram once it's done.

## Features

- 📥 Add downloads to JDownloader just by sending a URL to the bot
- 🏷️ Optional custom file name (`<url> <filename>`)
- 📊 Live progress updates (percentage, size, status) in Telegram
- 📤 Automatic upload of the finished file back to the chat
- 🔒 Optional chat allow-list (`ALLOWED_CHAT_IDS`) to restrict who can use the bot
- 🐳 Fully containerized with Docker Compose (bot + JDownloader + Mini App API + Mini App web frontend)
- 📱 A Telegram Mini App (`web/`) with the same functionality (queue, accounts, duplicates, variant picker) as a graphical web UI inside Telegram, served by its own nginx container and talking to the API (`api/`) over CORS

## Tech Stack

- [Python 3.12](https://www.python.org/)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 20.7
- [FastAPI](https://fastapi.tiangolo.com/) — Mini App API
- [myjdapi](https://github.com/mmarquezs/My.Jdownloader-API-Library) — MyJDownloader API client
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment variable loading
- nginx — serves the Mini App web frontend (vanilla HTML/CSS/JS, no build step)
- Docker & Docker Compose

## Project Structure

```
.
├── docker-compose.yml       # Orchestrates jdownloader, bot, api, and web containers
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
├── api/                     # Mini App API (FastAPI)
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # API-specific env vars
│   ├── auth.py               # Telegram Mini App initData validation
│   ├── routers/              # /api/queue, /api/accounts endpoints
│   ├── tests/                # Unit test suite (pytest)
│   ├── Dockerfile
│   └── requirements.txt
└── web/                     # Mini App frontend (vanilla HTML/CSS/JS, no build step), served by nginx
    ├── index.html            # Template; ${API_BASE_URL} substituted at container startup
    ├── style.css
    ├── app.js
    ├── Dockerfile             # nginx:alpine
    └── docker-entrypoint.sh   # envsubst step run by nginx's docker-entrypoint.d/
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
JD_EMAIL=your_myjdownloader_email
JD_PASSWORD=your_myjdownloader_password
JD_DEVICENAME=MyJDownloader
ALLOWED_CHAT_IDS=123456789,987654321
POLL_INTERVAL=10
MAX_FILE_SIZE_MB=50
```

| Variable            | Required | Default            | Description                                                    |
| -------------------- | :------: | ------------------- | ---------------------------------------------------------------- |
| `TELEGRAM_TOKEN`     |    ✅    | —                   | Telegram bot token from BotFather                                |
| `JD_EMAIL`           |    ✅    | —                   | MyJDownloader account email                                       |
| `JD_PASSWORD`        |    ✅    | —                   | MyJDownloader account password                                    |
| `JD_DEVICENAME`      |    ❌    | machine hostname    | Name of the JDownloader device to connect to                     |
| `ALLOWED_CHAT_IDS`   |    ❌    | *(empty = anyone)*  | Comma-separated Telegram chat IDs allowed to use the bot          |
| `POLL_INTERVAL`      |    ❌    | `10`                | Seconds between download status checks                           |
| `MAX_FILE_SIZE_MB`   |    ❌    | `50`                | Maximum file size (MB) the bot will upload back to Telegram       |
| `CORS_ORIGINS`       |    ❌    | `http://localhost:8080` | Comma-separated origins allowed to call the Mini App API (the `web` container's origin) |
| `API_BASE_URL`       |    ❌    | `http://localhost:8000` | Base URL where the `web` frontend reaches the API; baked into `index.html` at container startup |

### 3. Run with Docker Compose

```bash
docker compose up -d --build
```

This starts four containers:
- `jdownloader` — the JDownloader instance
- `bot` — the Telegram bot
- `api` — the Mini App API (FastAPI); not yet exposed publicly (Cloudflare Tunnel setup is a future step)
- `web` — the Mini App frontend (nginx), talking to `api` over CORS; not yet exposed publicly either, see [Project Structure](#project-structure)

### 4. Start chatting

Open your bot in Telegram and send `/start`, then send it a download link.

## Usage

Just send a URL to start a download:

```
https://example.com/file.zip
https://example.com/file.zip my_custom_name.zip
```

If a link offers more than one file or quality (e.g. a YouTube video with several resolutions,
audio-only, thumbnail, subtitles), the bot shows a button per option with an icon and description
(🎬 video, 🎵 audio, 🖼 thumbnail, 📝 subtitles, plus resolution/bitrate when available) so you can
pick exactly what you want. Package names in JDownloader are tagged with the detected platform
(YouTube, Instagram, X, Facebook, TikTok, etc.).

### Commands

| Command                                       | Description                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------- |
| `/start`, `/help`                              | Show the welcome message and command list                          |
| `/queue <url> [name] [force]`                  | Add a download to the queue (or just `/queue` to be asked for it)   |
| `/list`                                        | Show the queue with download percentage                             |
| `/status`                                      | Show the queue with status text (Name, Status, URL)                 |
| `/remove <name>`                               | Remove a download from the queue/JDownloader and delete its local file |
| `/accounts`                                     | List configured premium accounts                                    |
| `/addaccount <hoster> <username> <password>`   | Add a premium account                                               |
| `/removeaccount <uuid>`                        | Remove a premium account                                            |

### Interactive /queue

Send `/queue` with no arguments and the bot asks you for the URL (validating it looks like a
real link) and then for a file name (send `-` to use the default one).

### Duplicate detection

If a URL or file name was already queued before, `/queue` shows buttons instead of downloading
right away:
- **Download again** — re-runs the download (same as adding `force` at the end manually).
- **Send existing file** — if the file is still on disk, resends it immediately without
  re-downloading.

This history — including the resulting file path once a download finishes — is stored in
`downloads/.bot_data/history.json` and survives container restarts.

## Development

### Setup

```bash
# Bot
cd bot
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt

# Mini App API (separate venv, Python 3.12 recommended)
cd api
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
