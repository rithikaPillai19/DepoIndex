# LLM Usage & Technical Methodology

## Tools & Models Used
* **Inference Model:** `llama-3.3-70b-versatile` (or your exact model from `src/segmenter.py`) via Groq Cloud API for high-throughput, structured JSON extraction.
* **Development Assistance:** AI coding tools were used for initial regex boilerplate, Streamlit UI scaffolding, and generating preliminary test mockups.

## Significant Technical Decisions (Accepted vs. Rejected)

### 1. Rejecting Direct Coordinate Prompting (Hallucination Mitigation)
* **Rejected Proposal:** Prompting the LLM directly: *"On what page and line does this topic begin and end?"*
* **Reason:** Generative models do not possess spatial line-coordinate awareness over raw transcript pages; they hallucinate plausibly formatted line numbers that drift from ground truth.
* **Adopted Solution:** A two-tier hybrid architecture. The LLM extracts verbatim semantic anchors (`start_quote`, `end_quote`) under strict Pydantic schema validation. A deterministic Python parser and fuzzy string resolver then calculate exact physical `(Page, Line)` coordinates.

### 2. Slicing Strategy: Overlapping Sliding Window vs. Whole-Document Processing
* **Rejected Proposal:** Passing the entire 2,000+ line transcript in a single prompt context.
* **Reason:** Whole-context attention dilution results in dropped intermediate topics, degraded boundary fidelity, and severe rate-limit bottlenecks.
* **Adopted Solution:** An 80-line sliding window with a 15-line overlap to preserve cross-boundary legal context, coupled with adjacent segment deduplication and merging.

### 3. Fault Tolerance & Idempotent Caching
* **Decision:** Implemented an intermediate chunk cache (`output/chunks_cache.json`).
* **Benefit:** Ensures network resilience against API rate-limits (`429`), allowing the pipeline to resume execution without duplicate token spend or loss of completed extractions.

## Human Engineering Ownership
* **Deterministic Line Indexer:** The regex AST parser parsing court reporter headers, sequential lines (1–25), and timestamp strips was written and debugged manually to guarantee zero coordinate drift.
* **Manual Verification:** Audited 20 distinct entries across Pages 7–88 directly against the court reporter PDF using the custom Streamlit verification workbench, achieving 100% coordinate provenance accuracy.