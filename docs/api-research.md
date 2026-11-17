# NEXUS Platform API Research & Feasibility Analysis

This document details the official API research, architectural trade-offs, authentication mechanisms, constraints, and operational feasibility for the publishing platforms integrated into NEXUS.

---

## Executive Summary of Platform Candidates

| Platform | Official API / Protocol | Auth Mechanism | Pricing / Tier | URL Verification Capability | Public Visibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bluesky** | AT Protocol (`com.atproto.*`) | App Password / JWT Session | Free / Open | Returns AT URI (`at://.../post/{rkey}`) | **Public** (web accessible via bsky.app) |
| **Mastodon** | REST API v1 (`POST /api/v1/statuses`) | OAuth2 Bearer Token | Free / Self-hostable | Returns canonical status URL | **Public** (instance web UI) |
| **Telegram** | Bot API (`POST /sendMessage`) | Bot Token (`bot<token>`) | Free | Resolvable for public channels (`t.me/{user}/{id}`) | **Public** for public channels; **Private** for user/group chats |
| **Discord** | Webhook API (`POST /api/webhooks`) | Webhook Token | Free | Deterministic jump URL (`discord.com/channels/...`) | **Private** (requires guild membership/login) |
| **Reddit** | OAuth2 API (`POST /api/submit`) | Script App Client ID + Secret | Free Tier (100 QPM for non-commercial) | Returns canonical submission URL | **Public** (web accessible via reddit.com) |
| *X (formerly Twitter)* | Twitter API v2 (`POST /2/tweets`) | OAuth 1.0a / OAuth 2.0 | Paid ($100-$200/mo Basic tier) | Returns tweet ID | Public |
| *LinkedIn* | Posts API (`POST /rest/posts`) | OAuth 2.0 3-Legged User Token | Free with App Review | Returns post URN | Public |

---

## Selected Platforms: Detailed Research

### 1. Bluesky (AT Protocol)
- **Official Documentation**: [https://docs.bsky.app/docs/category/http-reference](https://docs.bsky.app/docs/category/http-reference)
- **Protocol & Transport**: Authenticated JSON-RPC / XRPC over HTTPS.
- **Authentication**:
  - Endpoint: `POST /xrpc/com.atproto.server.createSession`
  - Credentials: `identifier` (handle, e.g. `alice.bsky.social`) and `password` (App Password created under Settings -> App Passwords).
  - Yields `accessJwt` (short-lived bearer token) and account `did`.
- **Publishing Endpoint**:
  - Endpoint: `POST /xrpc/com.atproto.repo.createRecord`
  - Collection: `app.bsky.feed.post`
  - Payload:
    ```json
    {
      "repo": "did:plc:...",
      "collection": "app.bsky.feed.post",
      "record": {
        "$type": "app.bsky.feed.post",
        "text": "Message content with URL",
        "createdAt": "2026-11-17T12:00:00Z"
      }
    }
    ```
- **Content Limits**: 300 graphemes per post record. NEXUS's 200-character limit fits natively.
- **URL Verification**: Returns `uri` formatted as `at://{did}/app.bsky.feed.post/{rkey}`. NEXUS derives the canonical web URL: `https://bsky.app/profile/{handle}/post/{rkey}`.
- **Public Visibility**: Completely public; unauthenticated users can view posts on the web without logging in.

---

### 2. Mastodon (REST API v1)
- **Official Documentation**: [https://docs.joinmastodon.org/methods/statuses/](https://docs.joinmastodon.org/methods/statuses/)
- **Protocol & Transport**: RESTful HTTP API over HTTPS.
- **Authentication**:
  - HTTP Header: `Authorization: Bearer <access_token>`
  - Scopes Required: `write:statuses`
- **Publishing Endpoint**:
  - Endpoint: `POST {instance_url}/api/v1/statuses`
  - Form/JSON Parameters:
    - `status`: Text content to post.
    - `visibility`: `public` (explicitly requested by NEXUS).
- **Content Limits**: Default 500 characters on standard Mastodon instances (configurable per instance). NEXUS's 200-character limit easily complies.
- **URL Verification**: Mastodon returns HTTP 200 with a complete Status entity. The `url` field contains the canonical permalink on that instance.
- **Public Visibility**: Completely public when published with `visibility: public`.

---

### 3. Telegram (Bot API)
- **Official Documentation**: [https://core.telegram.org/bots/api#sendmessage](https://core.telegram.org/bots/api#sendmessage)
- **Protocol & Transport**: JSON over HTTPS.
- **Authentication**:
  - Bot token obtained from `@BotFather`.
  - Format: `https://api.telegram.org/bot<token>/sendMessage`
- **Publishing Endpoint**:
  - Endpoint: `POST /bot<token>/sendMessage`
  - Parameters:
    - `chat_id`: Integer or string channel username (`@channel_name`).
    - `text`: Message body.
    - `disable_web_page_preview`: `false` (allows URL previews).
- **Content Limits**: Up to 4,096 characters per message.
- **URL Verification & Public Access**:
  - If `chat_id` is a public channel/supergroup with a public username: message is viewable at `https://t.me/{username}/{message_id}` (`public_access = true`).
  - If `chat_id` is an integer user ID or private group: message has no public web link (`posted_url = None`, `public_access = false`).
  - NEXUS inspects the `chat.username` attribute in the API response to dynamically ascertain true public accessibility.

---

### 4. Discord (Webhook API)
- **Official Documentation**: [https://discord.com/developers/docs/resources/webhook#execute-webhook](https://discord.com/developers/docs/resources/webhook#execute-webhook)
- **Protocol & Transport**: RESTful JSON over HTTPS.
- **Authentication**:
  - Token embedded directly in the Webhook URL: `https://discord.com/api/webhooks/{webhook.id}/{webhook.token}`.
- **Publishing Endpoint**:
  - Endpoint: `POST /api/webhooks/{webhook.id}/{webhook.token}?wait=true`
  - Parameter `?wait=true`: Instructs Discord to wait for message persistence and return the created Message object (rather than `204 No Content`).
  - Payload: `{"content": "..."}`.
- **Content Limits**: 2,000 characters.
- **URL Verification & Public Access**:
  - Response provides `id`, `channel_id`, and `guild_id`.
  - Permlink: `https://discord.com/channels/{guild_id}/{channel_id}/{message_id}`.
  - **Public Access**: `false`. Discord channels require authentication and server membership; unauthenticated web users cannot view posts.

---

### 5. Reddit (OAuth2 API)
- **Official Documentation**: [https://www.reddit.com/dev/api#POST_api_submit](https://www.reddit.com/dev/api#POST_api_submit)
- **Protocol & Transport**: OAuth2 + REST API over HTTPS.
- **Authentication**:
  - Token endpoint: `POST https://www.reddit.com/api/v1/access_token`
  - HTTP Basic Auth: `(client_id, client_secret)`
  - Grant Type: `password` with developer `username` and `password`.
  - Headers: Unique descriptive `User-Agent` string (strictly enforced by Reddit).
- **Publishing Endpoint**:
  - Endpoint: `POST https://oauth.reddit.com/api/submit`
  - Form Parameters:
    - `sr`: target subreddit name.
    - `kind`: `self` (text post).
    - `title`: First 80 characters of message.
    - `text`: Full message.
    - `resubmit`: `true`.
- **Content Limits**: Up to 40,000 characters for self-post body.
- **URL Verification**: Response contains `json.data.url` (canonical Reddit permalink).
- **Public Visibility**: Completely public on public subreddits.

---

## Why Other Candidates Were Deprioritized

1. **X / Twitter API**:
   - In 2023, Twitter eliminated free API tiers. The "Free" tier is write-only with an extreme 1,500 tweets/month limit across all apps and frequently suffers undocumented gating. Production API access requires $100-$200/month "Basic" tier subscriptions.
2. **LinkedIn Posts API**:
   - Requires formal developer application review and approval for Community Management or Share on LinkedIn permissions. OAuth tokens require 3-legged browser redirect authentication, making automated background CLI server publishing fragile without persistent user refresh tokens.
