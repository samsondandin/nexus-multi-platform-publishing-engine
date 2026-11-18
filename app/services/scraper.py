"""Asynchronous website content extraction service using HTTPX and BeautifulSoup."""

import re
from typing import Dict, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.utils.logging import logger
from app.utils.ssrf import validate_url_for_ssrf

# Maximum bytes to download from remote site to prevent memory exhaustion (2 MB)
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
# Maximum text length passed to LLM context
MAX_EXTRACTED_TEXT_CHARS = 10000


class ScrapingError(Exception):
    """Raised when website extraction fails due to network, status, or parsing errors."""

    pass


class WebsiteScraperService:
    """Safely extracts website metadata, structure, and text content with SSRF protection."""

    def __init__(self, timeout_seconds: float = 12.0):
        self.timeout_seconds = timeout_seconds
        self.user_agent = (
            "Mozilla/5.0 (compatible; NexusLinkAnalyzer/1.0; +https://github.com/samsondandin/nexus-multi-platform-publishing-engine)"
        )

    async def fetch_and_extract(self, url: str) -> Dict[str, Optional[str]]:
        """Fetch URL content safely, validating redirects against SSRF attacks.

        Returns:
            Dict with keys: url, title, meta_description, keywords, headings, cleaned_text
        """
        # Step 1: Pre-flight SSRF check on target URL
        validate_url_for_ssrf(url)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        current_url = url
        redirect_limit = 5
        timeout = httpx.Timeout(self.timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout, verify=True, follow_redirects=False) as client:
            response = None
            redirects_followed = 0

            while redirects_followed <= redirect_limit:
                try:
                    response = await client.get(current_url, headers=headers)
                except httpx.TimeoutException as exc:
                    raise ScrapingError(f"Connection to '{current_url}' timed out after {self.timeout_seconds}s.") from exc
                except httpx.NetworkError as exc:
                    raise ScrapingError(f"Network error while connecting to '{current_url}': {exc}") from exc

                # Handle HTTP redirects safely (re-evaluating SSRF target on each hop)
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        break
                    next_url = urljoin(current_url, location)
                    logger.info("Following safe redirect: %s -> %s", current_url, next_url)
                    # Enforce SSRF validation on redirect destination
                    validate_url_for_ssrf(next_url)
                    current_url = next_url
                    redirects_followed += 1
                    continue
                else:
                    break

            if response is None:
                raise ScrapingError("No response received from remote server.")

            if response.status_code >= 400:
                raise ScrapingError(
                    f"Target website returned HTTP error status {response.status_code} ({response.reason_phrase})."
                )

            # Check content length
            content = response.content[:MAX_RESPONSE_BYTES]
            html_text = content.decode("utf-8", errors="replace")

        # Step 2: Parse HTML content with BeautifulSoup
        return self._parse_html(current_url, html_text)

    def _parse_html(self, final_url: str, html_text: str) -> Dict[str, Optional[str]]:
        soup = BeautifulSoup(html_text, "html.parser")

        # Extract Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("meta", property="og:title"):
            title = soup.find("meta", property="og:title").get("content", "").strip()

        # Extract Meta Description
        meta_description = ""
        desc_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)}) or soup.find(
            "meta", property="og:description"
        )
        if desc_tag and desc_tag.get("content"):
            meta_description = desc_tag.get("content", "").strip()

        # Extract Meta Keywords
        keywords = ""
        kw_tag = soup.find("meta", attrs={"name": re.compile(r"keywords", re.I)})
        if kw_tag and kw_tag.get("content"):
            keywords = kw_tag.get("content", "").strip()

        # Extract Headings (H1, H2, H3)
        headings = []
        for tag_name in ["h1", "h2", "h3"]:
            for heading in soup.find_all(tag_name):
                h_text = heading.get_text(separator=" ", strip=True)
                if h_text and len(h_text) > 3 and len(h_text) < 120:
                    headings.append(f"{tag_name.upper()}: {h_text}")

        # Remove irrelevant noise elements
        for element in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form"]):
            element.decompose()

        # Clean body text
        raw_text = soup.get_text(separator=" ", strip=True)
        # Collapse multiple whitespace
        cleaned_text = re.sub(r"\s+", " ", raw_text).strip()

        # Truncate text to fit within LLM token budget
        truncated_text = cleaned_text[:MAX_EXTRACTED_TEXT_CHARS]

        return {
            "url": final_url,
            "title": title or "No title found",
            "meta_description": meta_description or "No meta description found",
            "keywords": keywords or None,
            "headings": "\n".join(headings[:20]),
            "cleaned_text": truncated_text,
        }


scraper_service = WebsiteScraperService()
