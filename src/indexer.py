import pymupdf
import json
import os
import time
from typing import List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Models confirmed available on your account
CANDIDATE_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite-preview"
]

class PageTopicCandidate(BaseModel):
    topic: str = Field(..., description="Substantive examination topic name in Title Case.")
    start_page: int = Field(..., description="Estimated starting page number.")
    end_page: int = Field(..., description="Estimated ending page number.")
    expected_theme: str = Field(..., description="Key factual or legal inquiry theme.")

def build_document_page_index(pdf_path: str, output_path: str = "data/page_index.json") -> List[Dict[str, Any]]:
    doc = pymupdf.open(pdf_path)
    page_catalog = []

    for page_num in range(1, len(doc) + 1):
        page = doc[page_num - 1]
        text = page.get_text("text").strip()

        if not text or len(text.split()) < 15:
            continue

        text_upper = text.upper()
        if any(marker in text_upper for marker in ["WORD INDEX", "CONCORDANCE", "CERTIFICATE OF NOTARY"]):
            continue

        split_lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().isdigit()]
        clean_preview = " | ".join(split_lines[:5])

        page_catalog.append({
            "page": int(page_num),
            "preview": clean_preview[:180]
        })

    doc.close()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(page_catalog, f, indent=2)

    print(f"✓ Generated Coarse Page Index across {len(page_catalog)} substantive pages.")
    return page_catalog

def route_topics_from_index(page_catalog_path: str = "data/page_index.json", batch_size: int = 40) -> List[PageTopicCandidate]:
    with open(page_catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    all_topics: List[PageTopicCandidate] = []

    for i in range(0, len(catalog), batch_size):
        sub_catalog = catalog[i : i + batch_size]
        start_p = sub_catalog[0]["page"]
        end_p = sub_catalog[-1]["page"]

        print(f"  Routing Catalog Slice: Pages {start_p} to {end_p}...", flush=True)
        catalog_summary = "\n".join([f"Page {p['page']}: {p['preview']}" for p in sub_catalog])

        prompt = f"""You are an expert legal deposition analyst.
Review this page catalog summary (Pages {start_p} to {end_p}) and extract all distinct substantive macro-topics.

Instructions:
1. Create concise topic names in Title Case (e.g., 'Witness Background & Qualifications', 'Review of PEAKS Loan Documents').
2. Identify start_page and end_page for each topic within the range.
3. Exclude procedural noise (recesses, administrative questions).

Page Previews:
{catalog_summary}

Respond STRICTLY with valid JSON in this exact structure:
{{
  "topics": [
    {{
      "topic": "Topic Name",
      "start_page": 1,
      "end_page": 5,
      "expected_theme": "Brief description"
    }}
  ]
}}"""

        success = False
        for model_name in CANDIDATE_MODELS:
            for retry in range(2):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.0
                        )
                    )
                    payload = json.loads(response.text)
                    for t in payload.get("topics", []):
                        if t.get("topic") and t.get("start_page"):
                            all_topics.append(PageTopicCandidate(**t))
                    success = True
                    break
                except Exception as e:
                    err = str(e)
                    if "503" in err or "429" in err:
                        time.sleep(2.0 * (retry + 1))
                        continue
                    else:
                        break
            if success:
                break

        time.sleep(0.5)

    return all_topics