import pymupdf  # updated from fitz
import json
import os
import re
import time
from typing import List, Dict, Any
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)

class PageTopicCandidate(BaseModel):
    topic: str = Field(..., description="Substantive examination topic name in Title Case.")
    start_page: int = Field(..., description="Estimated starting page number.")
    end_page: int = Field(..., description="Estimated ending page number.")
    expected_theme: str = Field(..., description="Key factual or legal inquiry theme.")

def build_document_page_index(pdf_path: str, output_path: str = "data/page_index.json") -> List[Dict[str, Any]]:
    """
    Scans every page to build a lightweight, token-compressed page catalog.
    """
    doc = pymupdf.open(pdf_path)
    page_catalog = []

    for page_num in range(1, len(doc) + 1):
        page = doc[page_num - 1]
        text = page.get_text("text").strip()

        # Skip administrative/empty pages or indices
        if not text or len(text.split()) < 15:
            continue
        if any(marker in text.upper() for marker in [
            "WORD INDEX", "CONCORDANCE", "CERTIFICATE OF NOTARY", "IN WITNESS WHEREOF"
        ]):
            continue

        # Keep only the first 5 substantive Q/A lines per page for token efficiency
        lines = [l.strip() for l in text.splitlines() if not l.strip().isdigit() and len(l.strip()) > 10][:5]
        clean_preview = " | ".join(lines)
        page_catalog.append({
            "page": page_num,
            "preview": clean_preview[:160]
        })

    doc.close()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(page_catalog, f, indent=2)

    print(f"✓ Generated Coarse Page Index across {len(page_catalog)} substantive pages.")
    return page_catalog

def route_topics_from_index(page_catalog_path: str = "data/page_index.json", batch_size: int = 30) -> List[PageTopicCandidate]:
    """
    Routes topics using batched slices of 30 pages to prevent 413/ITPM rate limit overages.
    """
    with open(page_catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    all_topics: List[PageTopicCandidate] = []

    for i in range(0, len(catalog), batch_size):
        sub_catalog = catalog[i : i + batch_size]
        start_p = sub_catalog[0]["page"]
        end_p = sub_catalog[-1]["page"]
        
        print(f"  Routing Catalog Slice: Pages {start_p} to {end_p}...", flush=True)
        catalog_summary = "\n".join([f"Page {p['page']}: {p['preview']}" for p in sub_catalog])

        prompt = f"""You are a litigation analyst examining a deposition catalog.
Identify overarching, substantive examination topics in this section.

Instructions:
1. Return high-level subject areas (e.g., 'Witness Background', 'Exhibit Review', 'Standard of Care').
2. Estimate start_page and end_page within Pages {start_p} to {end_p}.
3. Skip procedural noise (objections, breaks).

Page Previews:
{catalog_summary}

Respond STRICTLY with raw JSON:
{{
  "topics": [
    {{
      "topic": "<Substantive Topic in Title Case>",
      "start_page": <int>,
      "end_page": <int>,
      "expected_theme": "<1 sentence description>"
    }}
  ]
}}"""

        try:
            completion = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1000
            )
            raw_text = completion.choices[0].message.content or ""
            raw_text = re.sub(r"^```(?:json)?", "", raw_text.strip(), flags=re.MULTILINE)
            raw_text = re.sub(r"```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
            
            fb = raw_text.find("{")
            lb = raw_text.rfind("}")
            if fb != -1 and lb != -1:
                payload = json.loads(raw_text[fb : lb + 1])
                for t in payload.get("topics", []):
                    if t.get("topic") and t.get("start_page"):
                        all_topics.append(PageTopicCandidate(**t))
            
            # Short sleep to prevent hitting TPM limits across consecutive calls
            time.sleep(1.0)

        except Exception as e:
            print(f"  [Slice Routing Warning]: {e}")

    return all_topics