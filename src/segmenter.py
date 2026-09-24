import os
import json
import time
from typing import List
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

CANDIDATE_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite-preview"
]

class MacroTopicSpan(BaseModel):
    topic: str = Field(..., description="High-level substantive examination topic in Title Case.")
    start_quote: str = Field(..., description="Exact verbatim opening sentence from the text.")
    end_quote: str = Field(..., description="Exact verbatim closing sentence from the text.")
    evidence_summary: str = Field(..., description="Substantive 1-2 sentence factual synthesis.")

def extract_macro_topics(chunk_text: str) -> List[MacroTopicSpan]:
    prompt = f"""You are a senior litigation analyst indexing a legal deposition.
Identify overarching, substantive examination topics in this transcript segment.

Rules:
1. Macro-Level Only: Group questions, answers, and objections into parent legal topics.
2. 'start_quote': Verbatim starting sentence from the text.
3. 'end_quote': Verbatim ending sentence from the text.
4. 'evidence_summary': Substantive factual synthesis.

Transcript Segment:
{chunk_text}

Respond STRICTLY with valid JSON in this exact structure:
{{
  "topics": [
    {{
      "topic": "Topic Name",
      "start_quote": "Exact verbatim opening",
      "end_quote": "Exact verbatim ending",
      "evidence_summary": "1-2 sentence summary"
    }}
  ]
}}"""

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
                topics = []
                for t in payload.get("topics", []):
                    if t.get("topic") and t.get("start_quote") and t.get("end_quote"):
                        topics.append(MacroTopicSpan(**t))
                return topics
            except Exception as e:
                err = str(e)
                if "503" in err or "429" in err:
                    time.sleep(2.0 * (retry + 1))
                    continue
                else:
                    break
    return []