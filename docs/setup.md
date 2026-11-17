# Local Environment Setup & Execution Guide

## Prerequisites

- **Python**: Version 3.10, 3.11, 3.12, 3.13, or 3.14.
- **Git**: Version 2.30+.
- **Virtual Environment Tool**: `venv` or `virtualenv`.

---

## 1. Clone & Set Up Virtual Environment

```bash
# Clone the repository
git clone https://github.com/samsondandin/nexus-multi-platform-publishing-engine.git
cd nexus-multi-platform-publishing-engine

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS / Linux:
source .venv/bin/activate
# On Windows (cmd):
.venv\Scripts\activate.bat
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Environment Configuration

Copy the example configuration to `.env`:

```bash
cp .env.example .env
```

Edit `.env` to supply genuine credentials for the platforms you wish to activate. Platforms left empty will automatically report as `unconfigured` without crashing the engine.

### How to Obtain Platform Credentials

1. **Bluesky**:
   - Register on [bsky.app](https://bsky.app).
   - Go to **Settings -> Privacy & Security -> App Passwords**.
   - Create an App Password and set `BLUESKY_HANDLE` and `BLUESKY_APP_PASSWORD`.
2. **Mastodon**:
   - Register on any Mastodon instance (e.g. `mastodon.social`).
   - Navigate to **Preferences -> Development -> New Application**.
   - Grant `write:statuses` scope and copy the generated Bearer Access Token.
3. **Telegram**:
   - Message `@BotFather` on Telegram and create a new bot via `/newbot`.
   - Copy the API token into `TELEGRAM_BOT_TOKEN`.
   - Create a channel or group, add the bot as administrator, and specify `TELEGRAM_CHAT_ID` (e.g. `@your_channel`).
4. **Discord**:
   - Open your Discord Server Settings -> **Integrations -> Webhooks**.
   - Click **New Webhook**, select the target channel, and copy the Webhook URL into `DISCORD_WEBHOOK_URL`.
5. **Reddit**:
   - Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
   - Click **Create App** and choose `script`.
   - Fill in `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, and `REDDIT_SUBREDDIT`.

---

## 4. Launch Application

Run the application with Uvicorn on port 4000:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Access the interactive API interfaces:
- **Swagger UI**: [http://localhost:4000/docs](http://localhost:4000/docs)
- **ReDoc**: [http://localhost:4000/redoc](http://localhost:4000/redoc)
- **Health Check**: [http://localhost:4000/health](http://localhost:4000/health)

---

## 5. Send a Test Request

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Discover our latest multi-platform publishing engine. https://example.com"
  }'
```
