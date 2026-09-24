import os
import json
import re
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field
from typing import List

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)

class MacroTopicSpan(BaseModel):
    topic: str = Field(..., description="High-level substantive legal or factual examination topic in Title Case.")
    start_quote: str = Field(..., description="Exact verbatim opening sentence.")
    end_quote: str = Field(..., description="Exact verbatim closing sentence.")
    evidence_summary: str = Field(..., description="Substantive 1-2 sentence factual synthesis.")

def _robust_json_extract(text: str) -> dict:
    if not text:
        return {"topics": []}
    text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```$", "", text.strip(), flags=re.MULTILINE).strip()
    
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return json.loads(text[first_brace:last_brace + 1])
    return json.loads(text)

def extract_macro_topics(chunk_text: str) -> List[MacroTopicSpan]:
    prompt = f"""You are a senior litigation analyst indexing a legal deposition.
Identify only the overarching, substantive examination topics discussed in this transcript segment.

STRICT INSTRUCTIONS:
1. Macro-Level Only: Group questions, answers, and objections into parent subject topics (e.g., 'Witness Background & Qualifications', 'Review of Exhibit 1', 'Breach of Standard of Care').
2. Do NOT create micro-topics for single questions, individual objections, or breaks.
3. If no new substantive topic starts or is covered, return {{"topics": []}}.
4. 'start_quote': Exact verbatim starting sentence from the text.
5. 'end_quote': Exact verbatim concluding sentence of the inquiry.
6. 'evidence_summary': Concise, factual 1-2 sentence synthesis of testimony given.

Transcript Segment:
{chunk_text}

Respond STRICTLY with raw valid JSON:
{{
  "topics": [
    {{
      "topic": "<Substantive Topic Name in Title Case>",
      "start_quote": "<verbatim sentence>",
      "end_quote": "<verbatim sentence>",
      "evidence_summary": "<summary>"
    }}
  ]
}}"""

    try:
        completion = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1500
        )
        raw_content = completion.choices[0].message.content or ""
        payload = _robust_json_extract(raw_content)
        raw_topics = payload.get("topics", [])
        
        valid = []
        for t in raw_topics:
            if isinstance(t, dict) and t.get("topic") and t.get("start_quote") and t.get("end_quote"):
                valid.append(MacroTopicSpan(**t))
        return valid

    except Exception as e:
        print(f"[Extraction Warning]: {e}")
        return []