"""Unit and integration tests for AI-Powered Website Link Analysis and SSRF protection."""

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.config import settings
from app.main import app
from app.utils.ssrf import SSRFValidationError, validate_url_for_ssrf


class TestSSRFProtection:
    """Test suite covering SSRF defense against private IPs, loopback, and metadata."""

    def test_block_loopback_ipv4(self):
        with pytest.raises(SSRFValidationError, match="blocked"):
            validate_url_for_ssrf("http://127.0.0.1:8000/internal")

    def test_block_localhost_hostname(self):
        with pytest.raises(SSRFValidationError, match="restricted hostname"):
            validate_url_for_ssrf("http://localhost:8080/admin")

    def test_block_rfc1918_private_ips(self):
        # 10.0.0.0/8
        with pytest.raises(SSRFValidationError, match="blocked"):
            validate_url_for_ssrf("http://10.0.0.1/status")
        # 192.168.0.0/16
        with pytest.raises(SSRFValidationError, match="blocked"):
            validate_url_for_ssrf("http://192.168.1.1/router")
        # 172.16.0.0/12
        with pytest.raises(SSRFValidationError, match="blocked"):
            validate_url_for_ssrf("http://172.16.0.10/database")

    def test_block_cloud_metadata_ip(self):
        # AWS / GCP link-local metadata IP
        with pytest.raises(SSRFValidationError, match="blocked"):
            validate_url_for_ssrf("http://169.254.169.254/computeMetadata/v1/")

    def test_allow_public_ip_and_domain(self):
        # Valid public domain
        result = validate_url_for_ssrf("https://example.com/products")
        assert result == "https://example.com/products"

    def test_reject_unsupported_scheme(self):
        with pytest.raises(SSRFValidationError, match="scheme 'ftp' is not allowed"):
            validate_url_for_ssrf("ftp://example.com/file.txt")


class TestLinkAnalysisEndpoint:
    """Integration test suite covering POST /link-analysis."""

    @pytest.mark.asyncio
    async def test_ssrf_blocked_returns_400(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/link-analysis", json={"url": "http://127.0.0.1/admin"})
            assert resp.status_code == 400
            assert "SSRF Protection" in resp.json()["detail"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_unconfigured_llm_returns_503(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
        # Mock successful HTML fetch
        respx.get("https://example.com/").mock(
            return_value=Response(
                200,
                text="<html><head><title>Example</title></head><body><h1>Welcome</h1><p>Test text</p></body></html>",
            )
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/link-analysis", json={"url": "https://example.com/"})
            assert resp.status_code == 503
            assert "not configured" in resp.json()["detail"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_link_analysis_with_gemini(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock_gemini_key")

        # 1. Mock remote website scrape
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Acme Payments — Global Billing Platform</title>
            <meta name="description" content="Scale online payments and global subscriptions easily.">
        </head>
        <body>
            <h1>Accept Payments Anywhere</h1>
            <h2>Global Subscriptions</h2>
            <h2>Invoicing & Fraud Prevention</h2>
            <p>Acme helps developers accept payments, send payouts, and manage online businesses with unified APIs.</p>
        </body>
        </html>
        """
        respx.get("https://acme-payments.example.com/").mock(
            return_value=Response(200, text=html_content)
        )

        # 2. Mock Gemini API response
        mock_gemini_json = {
            "top_5_services": [
                {"name": "Payment Gateway", "description": "Online payment processing for cards and wallets."},
                {"name": "Subscription Billing", "description": "Recurring billing and invoice management."},
                {"name": "Global Payouts", "description": "Cross-border transfers to bank accounts."},
                {"name": "Fraud Detection", "description": "Machine learning radar to block fraudulent charges."},
                {"name": "Developer APIs", "description": "RESTful endpoints and webhooks for integration."},
            ],
            "target_audience": {
                "primary_audience": "Tech startups and SaaS companies needing modern payment infrastructure",
                "secondary_audience": "Global enterprise platforms and marketplace operators",
                "industry_verticals": ["E-Commerce", "SaaS", "Fintech"],
            },
            "competitor_analysis": {
                "direct_competitors": ["Stripe", "Adyen", "Braintree"],
                "indirect_competitors": ["PayPal", "Bank Merchant Accounts"],
                "competitive_advantage": "Unified API architecture with zero setup fees.",
            },
            "target_search_queries": {
                "google": ["best payment gateway for saas", "global subscription billing api", "acme payments reviews"],
                "facebook": ["small business payment tools", "how to accept international payments"],
                "instagram": ["#fintechtools", "#ecommercecheckout", "#onlinepayments"],
                "linkedin": ["enterprise payment gateways", "scalable billing infrastructure"],
                "x": ["#fintech", "#saasbilling", "#paymentgateway"],
            },
            "seo_improvements": {
                "title_and_metadata": ["Include 'SaaS Billing' in title tag to capture search intent."],
                "content_and_keywords": ["Expand H2 sections with developer code samples."],
                "technical_seo": ["Add Organization and SoftwareApplication schema markup."],
            },
        }

        gemini_response_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json_dump_str(mock_gemini_json)}
                        ]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 1200,
                "candidatesTokenCount": 650,
            },
        }

        respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=mock_gemini_key").mock(
            return_value=Response(200, json=gemini_response_payload)
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/link-analysis", json={"url": "https://acme-payments.example.com"})

        assert resp.status_code == 200
        data = resp.json()

        assert data["url"] == "https://acme-payments.example.com"
        assert data["scraped_title"] == "Acme Payments — Global Billing Platform"
        assert len(data["top_5_services"]) == 5
        assert data["target_audience"]["primary_audience"] is not None
        assert len(data["competitor_analysis"]["direct_competitors"]) > 0

        # Verify search queries across 5 target platforms
        queries = data["target_search_queries"]
        assert len(queries["google"]) > 0
        assert len(queries["facebook"]) > 0
        assert len(queries["instagram"]) > 0
        assert len(queries["linkedin"]) > 0
        assert len(queries["x"]) > 0

        # Verify SEO improvements
        assert len(data["seo_improvements"]["technical_seo"]) > 0

        # Verify LLM metadata and cost estimation
        meta = data["llm_metadata"]
        assert meta["provider"] == "gemini"
        assert meta["prompt_tokens"] == 1200
        assert meta["completion_tokens"] == 650
        assert meta["estimated_cost_usd"] > 0.0


def json_dump_str(d: dict) -> str:
    import json
    return json.dumps(d)
