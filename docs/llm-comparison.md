# LLM Provider Architecture & Cost Comparison

This document details the comparative technical analysis, provider capabilities, structured output reliability, token pricing, and cost projections across three major Large Language Model providers evaluated for the NEXUS AI-Powered Link Analysis API.

---

## 1. Evaluated Providers & Models

| Evaluation Dimension | **Google Gemini (Primary)** | **OpenAI (Secondary)** | **Groq / Llama 3.3 (Alternative)** |
| :--- | :--- | :--- | :--- |
| **Model** | `gemini-2.5-flash` / `gemini-1.5-flash` | `gpt-4o-mini` | `llama-3.3-70b-versatile` |
| **Provider Architecture** | Google DeepMind native multimodal reasoning engine | OpenAI GPT-4o optimized distillation | Meta open-weights on Groq LPU inference |
| **Native JSON Schema Mode** | **Yes** (`response_mime_type: "application/json"`) | **Yes** (`response_format: {"type": "json_object"}`) | **Yes** (`response_format: {"type": "json_object"}`) |
| **Context Window** | **1,048,576 tokens** | 128,000 tokens | 128,000 tokens |
| **Inference Latency** | Ultra-low (~800ms - 1.4s) | Low (~1.0s - 1.8s) | Ultra-fast (~400ms - 800ms) |
| **Input Pricing (per 1M tokens)** | **$0.075** | $0.150 | $0.590 |
| **Output Pricing (per 1M tokens)** | **$0.300** | $0.600 | $0.790 |

---

## 2. Deep Dive Architectural Trade-Offs

### 1. Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`) — *Selected Primary Provider*
- **Why Selected**:
  1. **Unmatched Cost Efficiency**: At \$0.075/1M input and \$0.30/1M output, Gemini Flash is 50% cheaper than `gpt-4o-mini` while offering superior reasoning on corporate website semantics.
  2. **Enormous Context Budget**: 1M+ token context window guarantees zero risk of token overflow even when scraping dense, JavaScript-heavy enterprise web applications.
  3. **Guaranteed JSON Conformance**: Supports strict `application/json` output generation without requiring external tool-calling wrappers.
  4. **Google Cloud Alignment**: Direct native integration into Google Cloud Run, Secret Manager, and Firebase ecosystems without multi-cloud key sprawl.

### 2. OpenAI (`gpt-4o-mini`) — *Secondary Fallback*
- **Strengths**: Industry-standard reliability for strict JSON conformance and excellent zero-shot classification of niche B2B services.
- **Trade-off**: Approximately 2x higher token cost than Gemini Flash.

### 3. Groq (`llama-3.3-70b-versatile`) — *Open Alternative*
- **Strengths**: Extreme inference speed driven by LPUs; ideal for real-time interactive user-facing dashboards.
- **Trade-off**: Higher cost per million tokens than Gemini Flash for long text prompts, and potential rate limits on standard developer tiers.

---

## 3. Cost Projection & Unit Economics

A typical website scrape extracts **~1,200 to 2,500 prompt tokens** (HTML title, meta tags, H1-H3 headings, body text) and generates **~600 to 800 completion tokens** (5 services, audience, competitors, 5 platform queries, SEO improvements).

### Per-Query Cost Comparison:

| Provider & Model | Avg Input Tokens | Avg Output Tokens | Cost Per Analysis (USD) | Analyses per \$1.00 USD |
| :--- | :--- | :--- | :--- | :--- |
| **Google Gemini Flash** | 2,000 | 700 | **\$0.00036** | **~2,777 requests / \$1** |
| **OpenAI GPT-4o-mini** | 2,000 | 700 | **\$0.00072** | **~1,388 requests / \$1** |
| **Groq Llama 3.3 70B** | 2,000 | 700 | **\$0.00173** | **~578 requests / \$1** |

---

## 4. Automatic Cost Telemetry

Every request to `POST /link-analysis` returns actual token counts and calculated cost dynamically in the `llm_metadata` response object:

```json
"llm_metadata": {
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "prompt_tokens": 1420,
  "completion_tokens": 680,
  "estimated_cost_usd": 0.0003105
}
```
