"""
Macro-Topic Discovery Router.
Routes catalog slices into discrete substantive windows (5-8 pages each) to ensure continuous coverage.
"""
import json
import os
import time
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    timeout=60.0
)

# Prioritize the reliable flash-preview tier
CANDIDATE_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-flash-lite-latest"
]

class PageTopicCandidate(BaseModel):
    topic: str = Field(..., description="Substantive examination topic name in Title Case.")
    start_page: int = Field(..., description="Starting page number.")
    end_page: int = Field(..., description="Ending page number.")
    expected_theme: str = Field(..., description="Summary of inquiry.")

def route_topics_from_index(page_catalog_path: str = "data/page_index.json", batch_size: int = 15) -> List[PageTopicCandidate]:
    with open(page_catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    all_topics: List[PageTopicCandidate] = []
    step = batch_size - 2

    for i in range(0, len(catalog), step):
        sub_catalog = catalog[i : i + batch_size]
        if not sub_catalog:
            break
        start_p = sub_catalog[0]["page"]
        end_p = sub_catalog[-1]["page"]

        print(f"  Routing Catalog Slice: Pages {start_p} to {end_p}...", flush=True)
        catalog_summary = "\n".join([f"Page {p['page']}: {p['preview']}" for p in sub_catalog])

        prompt = f"""You are a senior litigation analyst indexing a legal deposition.
Review this catalog of Pages {start_p} to {end_p} and identify 2 to 4 distinct substantive examination topics.

Rules:
1. Divide the pages into continuous, cohesive substantive topics (each 3 to 7 pages long).
2. Cover the full range from {start_p} to {end_p} without skipping pages.
3. Exclude administrative matters and breaks.

Page Summaries:
{catalog_summary}

Respond STRICTLY with valid JSON:
{{
  "topics": [
    {{
      "topic": "Topic Name in Title Case",
      "start_page": {start_p},
      "end_page": {end_p},
      "expected_theme": "Key theme"
    }}
  ]
}}"""

        success = False
        for model_name in CANDIDATE_MODELS:
            for attempt in range(4):
                try:
                    completion = client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                        response_format={"type": "json_object"}
                    )
                    raw_text = completion.choices[0].message.content or "{}"
                    if "```json" in raw_text:
                        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in raw_text:
                        raw_text = raw_text.split("```")[1].split("```")[0].strip()

                    payload = json.loads(raw_text)
                    for t in payload.get("topics", []):
                        if t.get("topic") and t.get("start_page"):
                            all_topics.append(PageTopicCandidate(**t))
                    success = True
                    break
                except Exception as e:
                    err_msg = str(e)
                    # Retry on 503 (High Demand) and 429 (Rate Limit)
                    if "503" in err_msg or "429" in err_msg:
                        wait_sec = 4.0 * (attempt + 1)
                        print(f"    [Transient {err_msg[:3]} on {model_name}]: Backing off {wait_sec:.0f}s...", flush=True)
                        time.sleep(wait_sec)
                        continue
                    elif "404" in err_msg:
                        break
                    else:
                        print(f"    [Notice on {model_name}]: {e}")
                        break
            if success:
                break

        time.sleep(1.0)

    return all_topics