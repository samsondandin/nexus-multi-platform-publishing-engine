"""Unit tests for message validation logic."""

import pytest

from app.schemas import PostingRequest
from app.utils.validation import extract_and_validate_url, validate_message_content


class TestValidation:
    """Test suite covering all mandatory input validation requirements."""

    def test_valid_message_with_https_url(self):
        msg = "Check out our latest business platform and grow your online visibility. https://example.com"
        result = validate_message_content(msg)
        assert result == msg

    def test_valid_message_with_http_url(self):
        msg = "Visit our service at http://localhost:4000/docs for details."
        result = validate_message_content(msg)
        assert result == msg

    def test_valid_message_with_trailing_punctuation(self):
        msg = "Here is our product: https://example.com/product! Check it out."
        url = extract_and_validate_url(msg)
        assert url == "https://example.com/product"

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
        with pytest.raises(ValueError, match="at least one valid HTTP or HTTPS URL"):
            validate_message_content("This message has no URL whatsoever.")

    def test_reject_message_with_multiple_urls(self):
        msg = "Check https://example.com and also visit https://anotherexample.org"
        with pytest.raises(ValueError, match="exactly one valid URL, but 2 were found"):
            validate_message_content(msg)

    def test_reject_unsupported_protocol(self):
        msg = "Download file here: ftp://files.example.com/data.zip"
        with pytest.raises(ValueError, match="unsupported URL protocol"):
            validate_message_content(msg)

    def test_reject_malformed_url_no_domain(self):
        msg = "Check this out https://invalid and learn more."
        with pytest.raises(ValueError, match="Malformed URL"):
            validate_message_content(msg)

    def test_pydantic_schema_validation_success(self):
        payload = {"message": "Great tools at https://nexus.example.org/tools"}
        req = PostingRequest(**payload)
        assert req.message == payload["message"]

    def test_pydantic_schema_validation_failure(self):
        with pytest.raises(Exception):
            PostingRequest(message="No URL here")
