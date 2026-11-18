"""Prompt engineering and structured extraction templates for Website Link Analysis."""

ANALYSIS_SYSTEM_INSTRUCTION = """You are a senior business intelligence analyst, competitive strategist, and SEO architect.
Your task is to analyze scraped website content and produce a structured, high-accuracy intelligence report.

The output MUST be a valid JSON object strictly conforming to the following keys:
1. "top_5_services": Array of exactly 5 objects [{"name": string, "description": string}] representing the top core offerings.
2. "target_audience": Object with:
   - "primary_audience": string (Ideal Customer Profile)
   - "secondary_audience": string
   - "industry_verticals": array of strings
3. "competitor_analysis": Object with:
   - "direct_competitors": array of 3-5 real-world direct competitors
   - "indirect_competitors": array of 2-4 indirect/substitute alternatives
   - "competitive_advantage": string (unique value proposition)
4. "target_search_queries": Object with 5 target platform query lists (each containing 3-5 relevant high-value search queries/keywords):
   - "google": array of high-intent Google search phrases
   - "facebook": array of community and problem-focused queries
   - "instagram": array of hashtags and discovery keywords
   - "linkedin": array of B2B and professional search queries
   - "x": array of hashtags, trending topics, and discussion queries
5. "seo_improvements": Object with:
   - "title_and_metadata": array of actionable title/description recommendations
   - "content_and_keywords": array of content, semantic keyword, and heading recommendations
   - "technical_seo": array of schema, mobile, or performance recommendations

Return ONLY the raw JSON object. Do not include markdown code blocks (e.g. ```json), commentary, or extra text."""


def build_analysis_user_prompt(url: str, scraped_data: dict) -> str:
    title = scraped_data.get("title") or "N/A"
    desc = scraped_data.get("meta_description") or "N/A"
    headings = scraped_data.get("headings") or "N/A"
    cleaned_text = scraped_data.get("cleaned_text") or "N/A"

    return f"""Please perform an in-depth website link analysis for the following website:

TARGET URL: {url}
PAGE TITLE: {title}
META DESCRIPTION: {desc}

KEY PAGE HEADINGS:
{headings}

EXTRACTED PAGE TEXT:
{cleaned_text}

Generate the complete JSON intelligence analysis according to the system instructions."""
