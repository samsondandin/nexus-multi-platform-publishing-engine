"""Unit tests for message validation logic."""

import pytest
from pydantic import ValidationError

from app.schemas import PostingRequest
from app.utils.validation import extract_and_validate_url, validate_message_content


class TestValidation:
    """Test suite covering all mandatory input validation requirements and edge cases."""

    def test_valid_message_with_https_url(self):
        msg = "Check out our latest business platform and grow your online visibility. https://example.com"
        result = validate_message_content(msg)
        assert result == msg

    def test_valid_message_with_http_url(self):
        msg = "Visit our service at http://localhost:4000/docs for details."
        result = validate_message_content(msg)
        assert result == msg

    def test_valid_message_with_ipv4_url(self):
        msg = "Connect directly to http://192.168.1.1:8080/api for configuration."
        result = validate_message_content(msg)
        assert result == msg

    def test_valid_message_with_trailing_punctuation(self):
        msg = "Here is our product: https://example.com/product! Check it out."
        url = extract_and_validate_url(msg)
        assert url == "https://example.com/product"

    def test_valid_message_with_parentheses_around_url(self):
        msg = "Check out our documentation (https://example.com/docs) today."
        url = extract_and_validate_url(msg)
        assert url == "https://example.com/docs"

    def test_valid_message_with_brackets_around_url(self):
        msg = "Read the release notes [https://example.com/notes]."
        url = extract_and_validate_url(msg)
        assert url == "https://example.com/notes"

    def test_reject_empty_message(self):
        with pytest.raises(ValueError, match="empty or contain only whitespace"):
            validate_message_content("")

    def test_reject_whitespace_only_message(self):
        with pytest.raises(ValueError, match="empty or contain only whitespace"):
            validate_message_content("   \t\n  ")

    def test_reject_none_message(self):
        with pytest.raises(ValueError, match="cannot be null"):
            validate_message_content(None)

    def test_reject_message_exceeding_200_chars(self):
        long_msg = "A" * 185 + " https://example.com"
        assert len(long_msg) > 200
        with pytest.raises(ValueError, match="exceeds the maximum allowed limit of 200"):
            validate_message_content(long_msg)

    def test_message_at_exact_200_chars(self):
        base = "https://example.com "
        msg = base + "A" * (200 - len(base))
        assert len(msg) == 200
        assert validate_message_content(msg) == msg

    def test_reject_message_without_url(self):
        with pytest.raises(ValueError, match="exactly one valid HTTP or HTTPS URL, but none were found"):
            validate_message_content("This message has no URL whatsoever.")

    def test_reject_message_with_two_urls(self):
        msg = "Check https://example.com and also visit https://anotherexample.org"
        with pytest.raises(ValueError, match="exactly one valid HTTP or HTTPS URL, but 2 were found"):
            validate_message_content(msg)

    def test_reject_message_with_three_urls(self):
        msg = "See https://a.com, https://b.com, and https://c.com"
        with pytest.raises(ValueError, match="exactly one valid HTTP or HTTPS URL, but 3 were found"):
            validate_message_content(msg)

    def test_reject_unsupported_protocol_ftp(self):
        msg = "Download file here: ftp://files.example.com/data.zip"
        with pytest.raises(ValueError, match="unsupported URI scheme"):
            validate_message_content(msg)

    def test_reject_unsupported_protocol_websocket(self):
        msg = "Connect via ws://stream.example.com/socket for live data."
        with pytest.raises(ValueError, match="unsupported URI scheme"):
            validate_message_content(msg)

    def test_reject_malformed_url_no_tld(self):
        msg = "Check this out https://invalid and learn more."
        with pytest.raises(ValueError, match="not a valid domain or IP address"):
            validate_message_content(msg)

    def test_reject_malformed_url_empty_host(self):
        msg = "Look at http:///path/only for information."
        with pytest.raises(ValueError, match="Missing host or domain name"):
            validate_message_content(msg)

    def test_reject_malformed_url_invalid_port(self):
        msg = "Connect to http://example.com:999999/api today."
        with pytest.raises(ValueError, match="Invalid port specified"):
            validate_message_content(msg)

    def test_pydantic_schema_validation_success(self):
        payload = {"message": "Great tools at https://nexus.example.org/tools"}
        req = PostingRequest(**payload)
        assert req.message == payload["message"]

    def test_pydantic_schema_validation_failure(self):
        with pytest.raises(ValidationError):
            PostingRequest(message="No URL here")
