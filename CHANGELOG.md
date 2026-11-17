# Changelog

All notable changes to the NEXUS Multi-Platform Publishing Engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-17

### Added
- Core FastAPI application with lifespan management and structured UTC logging.
- `POST /posting` endpoint for concurrent multi-platform publishing.
- Strict input validation engine enforcing:
  - Max length of 200 characters without silent truncation.
  - Requirement of exactly one valid HTTP or HTTPS URL.
  - Rejection of malformed URLs, empty messages, or unsupported protocols.
- Base platform adapter interface (`BasePlatformAdapter`) establishing uniform contracts for authentication checks, execution, and error handling.
- Five production-grade platform adapters:
  - **Bluesky** (`app.platforms.bluesky.py`): AT Protocol authentication (`createSession`) and record creation (`app.bsky.feed.post`).
  - **Mastodon** (`app.platforms.mastodon.py`): REST API v1 status posting with Bearer auth and public visibility.
  - **Telegram** (`app.platforms.telegram.py`): Bot API `sendMessage` supporting public channel link derivation.
  - **Discord** (`app.platforms.discord.py`): Execute Webhook API with `wait=true` message link derivation.
  - **Reddit** (`app.platforms.reddit.py`): OAuth2 password grant and `POST /api/submit` for public submissions.
- Asynchronous orchestrator (`PostingService`) providing fault-isolated concurrent publishing via `asyncio.gather()`.
- System observability endpoints:
  - `GET /`: Project metadata and direct documentation links.
  - `GET /health`: Service health and active platform metrics.
  - `GET /platforms`: Supported platform catalog and configuration status.
- Comprehensive automated test suite with 32 deterministic unit/integration tests and 5 opt-in live publishing tests.
- Full technical documentation suite under `docs/` and root `README.md`.
