# DepoIndex: Verifiable AI Deposition Topic Indexer

An AI litigation tool that transforms unstructured legal deposition transcripts into an auditable, verifiable topic index while maintaining deterministic source provenance.

---

## Technical Approach & Architecture

Standard LLM pipelines fail at transcript indexing because models hallucinate line numbers across large token contexts. DepoIndex resolves this with a **Two-Tier Deterministic Provenance Architecture**:

1. **Deterministic Coordinate Ingestion:** A regex-based AST parser processes raw deposition pages into indexed records `(page, line, text)`, completely decoupling coordinate tracking from model inference.
2. **Semantic Boundary Extraction:** The transcript is analyzed in rolling 80-line windows (with a 15-line overlap) using structured Pydantic schemas to identify legal topics and verbatim quote anchors.
3. **Anchor Resolution:** A fuzzy string matcher (`RapidFuzz`) maps verbatim start and end quotes back to physical line coordinates, guaranteeing zero line hallucination.
4. **Interactive Verification UI:** A Streamlit interface enables litigation teams to cross-reference every index entry with original transcript lines in real time.

---
## Deployed Site Link
https://depoindex-rithikapillai.streamlit.app/
## Setup & Reproduction

### Prerequisites
```bash
python -m venv venv
source venv/bin/activate  
pip install -r requirements.txt
