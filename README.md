Yes. The uploaded content is already intended to be a README, but it contains escaped Markdown (`\#`, `\*`, `\|`, etc.). I can convert it into clean, copy-paste-ready Markdown.

The main content covers the project overview, architecture, validation pillars, benchmarks, repository structure, setup, testing, and deliverables. 

````markdown
# DepoIndex: Verifiable AI Deposition Topic Indexer

An auditable litigation support system that extracts, structures, and indexes legal deposition transcripts into verified, gap-free topic indices with strict, line-level source provenance.

[![Deployed Application](https://img.shields.io/badge/Streamlit-Live%20Demo-FF4B4B?logo=streamlit&logoColor=white)](https://depoindex-rithikapillai.streamlit.app/)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![Tests](https://img.shields.io/badge/pytest-4%20passed-brightgreen.svg)](tests/test_invariants.py)

---

## Deployed Application

Access the interactive verification dashboard:

👉 **[https://depoindex-rithikapillai.streamlit.app/](https://depoindex-rithikapillai.streamlit.app/)**

---

## Technical Approach & Architecture

Standard LLM pipelines fail on legal transcripts because language models hallucinate page and line boundaries across long token contexts.

DepoIndex resolves this with a **Two-Pass Hybrid Architecture** combined with a strict, four-pillar validation suite and a post-mutation revalidation gate.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                    Pass 0: Metadata & Invariants                       │
│                                                                        │
│  Matter Caption Parser → Bounds Clamping [Page 7:11 to Page 88:17]    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│          Step 1 & 2: Monotonic Parsing & Coarse Cataloging              │
│                                                                        │
│  Y-Clustering (ε_y = 3.0 pt) → Monotonic Global ID (GID) Grid         │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│          Step 3 & 4: Macro Discovery & Boundary Snapping               │
│                                                                        │
│  15-Page Catalog Windows → Speaker Turns & Sentence Closure Snapping  │
│  Measured Confidence Scoring (82.0% – 96.0%)                           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│          Step 5: Seam Healing, Merging & Revalidation Gate             │
│                                                                        │
│  Absorb Transitions (≤12 lines) → Multi-Page Gap Recovery (P48-52,    │
│  P74-78)                                                              │
│                                                                        │
│  └──> MANDATORY REVALIDATION GATE (Pillars 1–4 Re-Check on All States)│
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    Step 6: Production Deliverables                     │
│                                                                        │
│  Persis_Yu_Topic_Index.csv | topic_index.json | quarantine_audit.json │
└────────────────────────────────────────────────────────────────────────┘
````

### Core Architecture Highlights

1. **Pass 0 Metadata Extraction & Bound Clamping**

   Automatically identifies examining/defending attorneys and deponent role while clamping processing strictly to substantive testimony (Page 7, Line 11 through Page 88, Line 17), excluding captions, errata sheets, and index concordances (Pages 89–94).

2. **Layout-Agnostic, Regex-Free Text Ingestion**

   Extracts text using calibrated spatial Y-clustering (`ε_y = 3.0 pt`), assigning monotonic Global IDs (`global_id`, `page`, `line`, `text`).

   The pipeline relies on set-based string parsing rather than brittle regex to handle varying court reporter layouts.

3. **Deterministic Anchor Resolution & Measured Snapping**

   Initiating speaker turns (`Q.`, `A.`, `MR. PURCELL`) and clean sentence closures (`.`, `?`, `!`, `"`, `'`, `)`) are snapped before validation.

   Snap confidence is dynamically calculated using string similarity and distance penalties rather than hardcoding arbitrary `100.0` scores.

4. **The Four-Pillar Legal Validator**

   Every topic entry must satisfy four non-permissive criteria:

   * **Pillar 1: Coordinate Verifiability & Monotonicity**

     * `s_gid ≤ e_gid`
     * Measured match score ≥ `82.0%`

   * **Pillar 2: Boundary Integrity & Sentence Closure**

     * Terminal punctuation validation without cutoffs.

   * **Pillar 3: Independent Directed Semantic Support**

     * Set-based keyword stem overlap ≥ `20%` against the coordinate corpus.

   * **Pillar 4: Evidence & Entity Grounding**

     * Statutory acronyms (`CFPB`, `TILA`, `SEC`, `ITT`, `PEAKS`) and proper nouns must appear within the coordinate slice.

5. **Mandatory Post-Mutation Revalidation Gate**

   Any post-discovery modification, including boundary snapping, duplicate merging, seam bridging, or gap recovery, strips the entry's verified status.

   Complete re-validation across all four pillars is required before export.

6. **Fail-Closed Auditing & Gap Recovery**

   Unresolvable candidates are quarantined with detailed failure diagnostics in:

   `output/quarantine_audit.json`

   Multi-page omitted ranges (Pages 48–52 and Pages 74–78) are recovered via bounded synthesis to guarantee continuous, gap-free deposition coverage.

---

## Calibration & Empirical Benchmarks

Parameters were benchmarked against ground-truth deposition segments and court colloquy distractors.

| Parameter                    | Calibrated Value | Calibration Objective / Finding                                                                                                                                   |
| ---------------------------- | ---------------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Y-Clustering (`ε_y`)**     |         `3.0 pt` | Evaluated across 250 ground-truth transcript lines; achieves 100% visual line reconstruction without vertical line collisions.                                    |
| **Fuzzy Anchor Score (`θ`)** |          `82.0%` | Benchmarked across 80 ground-truth quotes and 50 adversarial colloquy distractors ("Yes, sir", "Object to form"); achieves a False Acceptance Rate (FAR) of 0.0%. |
| **Minimum Anchor Length**    |       `18 chars` | Filters out non-unique colloquy fragments during string recovery.                                                                                                 |
| **Seam Gap Absorption**      |     `≤ 12 lines` | Safely bridges reporter notation, pauses, and brief transcript breaks without semantic drift.                                                                     |

---

## Before vs. After System Comparison

| Dimension                       | Earlier Version                                                                      | Revised Design                                                                                   |
| ------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| **Opening Coverage**            | Started at Page 12, dropping opening testimony due to an unsnapped break.            | Strictly starts at **Page 7, Line 11**; snapping occurs pre-validation.                          |
| **Downstream Mutation**         | Mutations (merging, snapping) were trusted directly into export without re-checking. | **Mandatory Revalidation Gate** re-validates 100% of post-mutation objects across all 4 pillars. |
| **Confidence Scoring**          | Assigned hardcoded `100.0` score to snapped or recovered lines.                      | Dynamically measures confidence (`82.0% – 96.0%`) with distance penalties.                       |
| **Semantic & Entity Grounding** | Superficial token presence check.                                                    | Directed semantic coverage ratio (`≥ 20%`) and statutory acronym grounding.                      |
| **Seam Continuity**             | Dropped 5-page gaps (Pages 48–52 and Pages 74–78).                                   | **100% Line-Level Continuity**; recovers gaps using grounded slice text.                         |
| **Terminal Invariant**          | Drifted into Page 94, capturing errata sheets and index concordance tables.          | Clamped strictly to deposition conclusion at **Page 88, Line 17**.                               |

---

## Repository Structure

```text
depo-index/
├── data/
│   ├── Persis_Yu_Deposition_Problem_statement.pdf  # Target transcript PDF
│   ├── parsed_transcript.json                      # Monotonic coordinate grid (Pass 1 cache)
│   └── page_index.json                             # Coarse catalog previews
│
├── output/
│   ├── Persis_Yu_Topic_Index.csv                  # Production court-admissible CSV
│   ├── topic_index.json                           # Full structured JSON with audit trails
│   └── quarantine_audit.json                      # Forensic log of quarantined candidates
│
├── src/
│   ├── __init__.py
│   ├── models.py                                  # Pydantic schemas (Pass 0 metadata, index entries)
│   ├── parser.py                                  # AST coordinate extraction & grid audit
│   ├── indexer.py                                 # Coarse catalog generation
│   ├── router.py                                  # Macro discovery with exponential backoff
│   ├── segmenter.py                               # Dialogue quote & anchor extraction
│   ├── resolver.py                                # RapidFuzz anchor resolution & snapping
│   ├── validator.py                               # Four-Pillar Legal Validation Suite
│   ├── pipeline.py                                # End-to-end pipeline with Revalidation Gate
│   ├── runner.py                                  # Top-level execution entrypoint
│   ├── evaluate.py                                # Automated compliance & continuity auditor
│   └── stability_check.py                         # Multi-run stability benchmark harness
│
├── tests/
│   └── test_invariants.py                         # Adversarial failure-mode test suite
│
├── calibrate.py                                   # Benchmark harness for ε_y and θ thresholds
├── app.py                                         # Interactive Streamlit UI
├── requirements.txt                               # Project dependencies
└── README.md                                      # System documentation
```

---

## Setup & Reproduction

### 1. Prerequisites & Environment Setup

Clone the repository and install dependencies in a virtual environment:

```bash
# Clone repository
git clone https://github.com/your-username/depo-index.git

cd depo-index

# Set up Python virtual environment
python -m venv venv

# Activate virtual environment

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Credentials

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY="your-gemini-api-key-here"
```

### 3. Run Invariant Unit Tests

Execute the adversarial unit test suite covering ungrounded entities, mid-sentence cuts, unsupported topics, and post-mutation tampering:

```bash
python -m pytest tests/test_invariants.py -v
```

Expected result:

```text
tests/test_invariants.py::test_adversarial_hallucinated_entity_fails_closed PASSED
tests/test_invariants.py::test_adversarial_mid_sentence_boundary_fails_closed PASSED
tests/test_invariants.py::test_adversarial_unsupported_topic_fails_closed PASSED
tests/test_invariants.py::test_stale_validation_fails_on_post_mutation_tampering PASSED

============================== 4 passed in 0.45s ==============================
```

### 4. Execute Production Indexing Pipeline

Run the complete pipeline to extract metadata, parse coordinates, route topics, recover gaps, and enforce the revalidation gate:

```powershell
Remove-Item -Path "data\parsed_transcript.json", "output\topic_index.json", "Persis_Yu_Topic_Index.csv" -ErrorAction SilentlyContinue

python -m src.pipeline
```

### 5. Audit & Evaluate Pipeline Deliverables

Verify topic count, start/end bounds, and 100% line continuity:

```bash
python -m src.evaluate
```

Expected output:

```text
=======================================================
=== DEPOSITION INDEX COMPLIANCE & CONTINUITY REPORT ===
=======================================================

Total Substantive Topics: 18 (or 19)

✓ Topic Count Invariant: PASSED
✓ Deposition Start Anchor: PASSED (Page 7, Line 11)
✓ Deposition End Anchor: PASSED (Page 88, Line 17)

=== Seam Continuity Audit ===

  ✓ Seam Continuity: 100% Contiguous across all pages. (0 gaps detected)
```

### 6. Run Multi-Run Stability Benchmark

Evaluate stability across 3 consecutive pipeline iterations:

```bash
python -m src.stability_check
```

### 7. Launch Interactive Dashboard

Run the Streamlit verification UI locally:

```bash
streamlit run app.py
```

---

## Deliverables & Output Formats

### 1. `Persis_Yu_Topic_Index.csv`

Production-ready, court-admissible topic index with columns:

* `Topic`
* `Start`
* `End`
* `Supporting Evidence`

### 2. `output/topic_index.json`

Machine-readable JSON export with coordinate IDs:

* `start_gid`
* `end_gid`

Includes audit trails for verification.

### 3. `output/quarantine_audit.json`

Fail-closed log detailing:

* Rejected candidates
* Recovery attempts
* Failure reasons

---

```

