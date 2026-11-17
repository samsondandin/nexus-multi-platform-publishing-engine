# Security & Configuration Guide

## 1. Secrets & Credential Management

- **Zero Hardcoded Secrets**: NEXUS strictly requires all credentials, API tokens, webhooks, and private keys to be injected via environment variables.
- **Git Hygiene**:
  - The `.gitignore` file enforces that `.env`, `.env.*.local`, `.venv`, and credential files are strictly excluded from source control.
  - An `.env.example` file is provided with empty keys and descriptive comments for developers.
- **Log Sanitation**:
  - The application logs never output authorization headers, raw API tokens, passwords, or webhook secrets.
  - In error reporting, URLs are cleaned and sensitive query parameters are stripped.

---

## 2. Input Sanitation & Injection Prevention

- **Strict Message Validation**:
  - All input messages are validated using Pydantic models with field validators before execution.
  - Messages exceeding 200 characters are rejected immediately.
  - Silently truncating messages is explicitly forbidden to prevent unintended payload modification.
- **URL Protocol Whitelisting**:
  - Only `http://` and `https://` schemes are accepted.
  - Insecure, local file, or dangerous protocols (such as `file://`, `ftp://`, `javascript:`, or `data:`) are strictly rejected with HTTP 422.
- **Network Location Verification**:
  - URLs must contain a valid domain or IP address with proper dot notation or `localhost`.
  - Malformed host strings are rejected.

---

## 3. Network & Transport Security

- All outgoing platform calls use HTTPS TLS connections with certificate verification managed by HTTPX and standard system trust stores.
- Platform request timeouts are enforced on all HTTP operations (`REQUEST_TIMEOUT_SECONDS=10.0`) to prevent socket hanging and denial of service.

---

## 4. Known Security Limitations & Operational Boundaries

- **Discord Webhook Secrets**: A Discord webhook URL acts as a bearer credential. Anyone with read access to the webhook URL can post messages to the associated Discord channel. Store this secret securely in environment variables.
- **Rate Limit Amplification**: Sending rapid high-frequency requests to `/posting` will cause external platforms to return HTTP 429. NEXUS reports these status codes transparently without crashing.
