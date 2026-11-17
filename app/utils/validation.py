"""Validation utilities for incoming publishing messages."""

import ipaddress
import re
from urllib.parse import urlparse

# Pattern matching any scheme prefix (e.g., http://, https://, ftp://, mailto:, ws://, etc.)
# Word-boundary or start-of-token check for explicit scheme protocols
SCHEME_PROTOCOL_PATTERN = re.compile(r'(?i)\b([a-z][a-z0-9+.-]*):(?:/{1,3})')

# Pattern to locate candidate HTTP/HTTPS URLs
HTTP_URL_CANDIDATE_PATTERN = re.compile(r'(?i)\b(https?://[^\s<>"]+)')

# Common surrounding/trailing punctuation in natural text that is not part of the URL
TRAILING_PUNCTUATION = '.,;:!?)]}\'">'
LEADING_PUNCTUATION = '([{\'"><'

# Basic valid domain label regex (RFC 1035 / RFC 1123)
DOMAIN_LABEL_REGEX = re.compile(r'^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)$')


def is_valid_ipv4(host: str) -> bool:
    """Check if host is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(host)
        return True
    except ValueError:
        return False


def is_valid_ipv6(host: str) -> bool:
    """Check if host is a valid IPv6 address."""
    try:
        ipaddress.IPv6Address(host)
        return True
    except ValueError:
        return False


def is_valid_hostname(host: str) -> bool:
    """Validate host string against standard FQDN or IP requirements."""
    if not host or len(host) > 253:
        return False

    # Check localhost
    if host.lower() == "localhost":
        return True

    # Check IP addresses
    if is_valid_ipv4(host) or is_valid_ipv6(host):
        return True

    # Check FQDN domain structure
    labels = host.split(".")
    if len(labels) < 2:
        return False

    # TLD must contain at least 2 characters and only alphabets/punycode
    tld = labels[-1]
    if len(tld) < 2 or not (tld.isalpha() or tld.startswith("xn--")):
        return False

    for label in labels:
        if not label or len(label) > 63:
            return False
        if not DOMAIN_LABEL_REGEX.match(label):
            return False

    return True


def extract_and_validate_url(message: str) -> str:
    """Validate that the message contains exactly one valid HTTP or HTTPS URL.

    Rules:
    1. Message must contain at least one valid HTTP or HTTPS URL.
    2. Message must contain no more than one valid HTTP or HTTPS URL.
    3. Rejects any non-HTTP/HTTPS URI protocols (e.g., ftp://, ws://, wss://, file://).
    4. Rejects malformed URLs (invalid hostnames, missing domains, bad ports, etc.).
    5. Correctly handles trailing/surrounding punctuation in natural language.
    6. Does not double-count URLs.

    Returns the cleaned, validated URL.
    Raises ValueError with descriptive message upon failure.
    """
    # 1. Check for any unsupported URI schemes in the text
    scheme_matches = SCHEME_PROTOCOL_PATTERN.findall(message)
    unsupported_schemes = [
        s.lower() for s in scheme_matches if s.lower() not in ("http", "https")
    ]
    if unsupported_schemes:
        raise ValueError(
            f"Message contains unsupported URI scheme ('{unsupported_schemes[0]}://'). "
            "Only HTTP and HTTPS URLs are permitted."
        )

    # 2. Extract potential HTTP/HTTPS URL tokens
    raw_candidates = HTTP_URL_CANDIDATE_PATTERN.findall(message)
    if not raw_candidates:
        raise ValueError("Message must contain exactly one valid HTTP or HTTPS URL, but none were found.")

    # 3. Clean leading and trailing punctuation from extracted URL candidates
    cleaned_candidates = []
    for candidate in raw_candidates:
        cleaned = candidate.lstrip(LEADING_PUNCTUATION)
        cleaned = cleaned.rstrip(TRAILING_PUNCTUATION)
        # Handle matched parentheses e.g. (https://example.com) -> https://example.com
        if cleaned.endswith(")") and "(" not in cleaned:
            cleaned = cleaned[:-1]
        if cleaned.endswith("]") and "[" not in cleaned:
            cleaned = cleaned[:-1]
        if cleaned:
            cleaned_candidates.append(cleaned)

    # 4. Enforce exactly one URL found
    if len(cleaned_candidates) > 1:
        raise ValueError(
            f"Message must contain exactly one valid HTTP or HTTPS URL, but {len(cleaned_candidates)} were found."
        )

    url_str = cleaned_candidates[0]

    # 5. Parse and rigorously validate URL components
    try:
        parsed = urlparse(url_str)
    except Exception as exc:
        raise ValueError(f"Malformed URL encountered: {exc}") from exc

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError("URL must use HTTP or HTTPS protocol.")

    if not parsed.netloc:
        raise ValueError("Malformed URL: Missing host or domain name.")

    # Validate port if present
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"Malformed URL: Invalid port specified ({exc}).") from exc

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Malformed URL: Missing valid hostname.")

    if not is_valid_hostname(hostname):
        raise ValueError(f"Malformed URL: Hostname '{hostname}' is not a valid domain or IP address.")

    return url_str


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

    # Validate URL presence and uniqueness (must be exactly one valid URL)
    extract_and_validate_url(trimmed)

    return trimmed
