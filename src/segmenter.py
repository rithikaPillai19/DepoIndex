import os
import json
import time
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is not set in your .env file")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

# Active production model on Groq's developer tier
MODEL_NAME = "openai/gpt-oss-120b"

class TopicSpan(BaseModel):
    topic_label: str = Field(description="Concise, substantive legal topic title")
    start_quote: str = Field(description="Exact verbatim 4-8 words where this topic began")
    end_quote: str = Field(description="Exact verbatim 4-8 words where this topic ended")
    evidence_summary: str = Field(description="1-2 sentences summarizing key testimony in this span")

SYSTEM_PROMPT = """You are an expert AI Litigation Specialist analyzing a deposition transcript.
Identify distinct topics discussed in the testimony.

Rules:
1. Topic labels must be concise, substantive legal or factual categories (e.g., 'Retention and Default Rates at ITT', 'Role of Vervent in Servicing vs Origination').
2. Provide verbatim quotes for `start_quote` and `end_quote` so they can be matched to exact transcript lines.
3. Do not invent line numbers. Only supply topic labels, quotes, and concise summaries.
4. Distinguish brief objections or procedural digressions from actual topic shifts.
5. You MUST return valid JSON in this exact structure:
{
  "topics": [
    {
      "topic_label": "Topic Title",
      "start_quote": "exact words starting topic",
      "end_quote": "exact words ending topic",
      "evidence_summary": "summary of discussion"
    }
  ]
}
"""

def process_chunk(chunk_text: str, max_retries: int = 5) -> Optional[List[TopicSpan]]:
    prompt = f"Transcript segment:\n{chunk_text}\n\nReturn the JSON object containing topics:"
    
    for attempt in range(max_retries):
        try:
            time.sleep(1.0)
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            raw_text = response.choices[0].message.content.strip()
            data = json.loads(raw_text)

            if isinstance(data, dict):
                for key in ["topics", "items", "data"]:
                    if key in data and isinstance(data[key], list):
                        data = data[key]
                        break
                if isinstance(data, dict):
                    data = [data]

            valid_topics = []
            for item in data:
                try:
                    valid_topics.append(TopicSpan(**item))
                except Exception:
                    continue

            return valid_topics

        except Exception as e:
            err_msg = str(e)
            wait_time = (attempt + 1) * 3
            print(f"\n[Groq Notice]: {err_msg[:80]}... Waiting {wait_time}s (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)

    print("\n[Error]: Exceeded maximum retries for this chunk.")
    return None