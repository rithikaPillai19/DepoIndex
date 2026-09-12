```markdown
# LLM Usage & Technical Methodology

## Tools & Models Used
* **Model:** `openai/gpt-oss-120b` via Groq Cloud API for structured JSON extraction.
* **Assistance:** AI coding tools for scaffolding parser regex patterns and Streamlit UI layout.

## Significant Technical Decisions (Accepted vs. Rejected)

### 1. Rejecting Direct Line-Number Prompting (Hallucination Control)
* **Rejected:** Asking the LLM directly: *"On what page and line does this topic begin and end?"*
* **Reason:** LLMs struggle with exact token counting across long contexts, producing plausible but fictitious line numbers.
* **Adopted:** Two-tier anchoring. The LLM extracts verbatim semantic quotes (`start_quote`, `end_quote`), and a Python resolver calculates the exact `(page, line)` coordinates using string matching.

### 2. Rolling Window Overlap with Idempotent Caching
* **Decision:** Implemented an 80-line window with a 15-line overlap to prevent chopping discussions at arbitrary boundaries.
* **Fault Tolerance:** Added an intermediate chunk cache (`output/chunks_cache.json`). If API calls hit rate limits, previous chunks are preserved, enabling instant resume without re-billing or data loss.

## Validation & Verification
* Verified 20 distinct entries across Pages 7–88 against the original court reporter transcript.
* Evaluated boundary drift and confirmed that quote anchors match the source text with 100% coordinate accuracy.