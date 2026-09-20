import json
import os
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field
from typing import List

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class TopicPageMapping(BaseModel):
    topic: str = Field(..., description="Canonical macro-topic name.")
    start_page: int = Field(..., description="Page number where discussion starts.")
    end_page: int = Field(..., description="Page number where discussion ends.")

def route_topics_via_index(page_index_path: str, canonical_taxonomy: list) -> List[TopicPageMapping]:
    with open(page_index_path, "r", encoding="utf-8") as f:
        page_index = json.load(f)

    # Convert the index into a compact string table
    index_catalog = "\n".join([f"Page {p['page']}: {p['preview']}..." for p in page_index])

    system_prompt = f"""
You are a legal research assistant. You are given a Document Page Index of a full deposition.
Match each canonical topic to its candidate page range (start_page and end_page).

CANONICAL TOPICS:
{json.dumps(canonical_taxonomy, indent=2)}

OUTPUT FORMAT:
Respond with a valid json object:
{{
  "mappings": [
    {{
      "topic": "<Exact topic title>",
      "start_page": <int>,
      "end_page": <int>
    }}
  ]
}}
"""

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Document Page Index:\n{index_catalog}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.0
    )

    data = json.loads(completion.choices[0].message.content)
    raw_mappings = data.get("mappings", data if isinstance(data, list) else [])
    return [TopicPageMapping(**m) for m in raw_mappings if m.get("topic") in canonical_taxonomy]