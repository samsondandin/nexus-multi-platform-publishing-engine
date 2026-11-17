"""Validation utilities for incoming publishing messages."""

import re
from urllib.parse import urlparse

# Strict regex matching potential URLs starting with http:// or https://
# Extracts candidates from text without trailing punctuation
URL_REGEX = re.compile(
    r'(https?://(?:[a-zA-Z0-9\-._~%!$&\'()*+,;=:@]+|\[[a-fA-F0-9:]+\])(?::\d+)?(?:/[^\s]*)?)'
)

# Common trailing punctuation that may be attached to URLs in natural language
TRAILING_PUNCTUATION = '.,;:!?)]}\'">'


def extract_and_validate_url(message: str) -> str:
    """Validate that the message contains exactly one valid HTTP/HTTPS URL.

    Rules:
    1. Message must contain at least one URL.
    2. Message must not contain more than one URL.
    3. The URL must have a valid scheme (http or https) and a valid network location (domain/host).
    4. Malformed URLs are rejected.

    Returns the cleaned, validated URL.
    Raises ValueError with descriptive reason upon failure.
    """
    raw_matches = URL_REGEX.findall(message)

    if not raw_matches:
        # Check if user tried to pass a scheme-less URL or unsupported protocol (e.g. ftp://)
        if re.search(r'\b(?:ftp|file|ws|wss)://', message, re.IGNORECASE):
            raise ValueError("Message contains an unsupported URL protocol. Only HTTP and HTTPS are permitted.")
        raise ValueError("Message must contain at least one valid HTTP or HTTPS URL.")

    # Clean trailing punctuation from extracted URLs
    cleaned_urls = []
    for candidate in raw_matches:
        cleaned = candidate.rstrip(TRAILING_PUNCTUATION)
        if cleaned:
            cleaned_urls.append(cleaned)

    if len(cleaned_urls) > 1:
        raise ValueError(
            f"Message must contain exactly one valid URL, but {len(cleaned_urls)} were found."
        )

    url = cleaned_urls[0]

    # Validate parsed URL structure
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"Malformed URL encountered: {exc}") from exc

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("URL must use HTTP or HTTPS protocol.")

    if not parsed.netloc:
        raise ValueError("Malformed URL: Missing host / domain.")

    # Ensure host has at least a valid domain or IP
    host = parsed.hostname
    if not host or len(host) < 3 or ("." not in host and host != "localhost"):
        raise ValueError(f"Malformed URL domain: '{host}'.")

    return url


def validate_message_content(message: str) -> str:
    """Validate publishing message according to NEXUS business rules:

    1. Empty / whitespace-only messages are rejected.
    2. Message must not exceed 200 characters (never silently truncate).
    3. Message must contain exactly one valid HTTP or HTTPS URL.
    4. Malformed URLs are rejected.

    Returns the stripped message upon success.
    Raises ValueError on validation failure.
    """
    if message is None:
        raise ValueError("Message cannot be null.")

    trimmed = message.strip()
    if not trimmed:
        raise ValueError("Message cannot be empty or contain only whitespace.")

    if len(trimmed) > 200:
        raise ValueError(
            f"Message length ({len(trimmed)} characters) exceeds the maximum allowed limit of 200 characters. "
            f"Messages are never silently truncated."
        )

    # Validate URL presence and uniqueness
    extract_and_validate_url(trimmed)

    return trimmed
