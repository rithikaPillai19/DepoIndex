# DepoIndex: Verifiable AI Deposition Topic Indexer

An auditable, verifiable litigation tool that transforms unstructured legal deposition transcripts into a gap-free, court-admissible topic index with strict coordinate provenance.

[![Deployed Application](https://img.shields.io/badge/Streamlit-Live%20Demo-FF4B4B?logo=streamlit&logoColor=white)](https://depoindex-rithikapillai.streamlit.app/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Deployed Application
Access the interactive verification dashboard:  
👉 **[https://depoindex-rithikapillai.streamlit.app/](https://depoindex-rithikapillai.streamlit.app/)**

---

## Technical Approach & Architecture

Standard LLM pipelines fail at deposition indexing because language models routinely hallucinate page and line boundaries across long token contexts. DepoIndex resolves this with a **Two-Pass Hybrid Architecture** coupled with an empirical, non-permissive verification suite.