from pydantic import BaseModel, Field
from typing import List
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
from src.resolver import ProvenanceResolver

load_dotenv()
client = OpenAI()

class TopicSpan(BaseModel):
    topic_label: str = Field(description="Concise, professional legal topic title (e.g., 'Loan Disclosures under Truth in Lending Act')")
    start_quote: str = Field(description="Exact verbatim 4-8 words where this topic began")
    end_quote: str = Field(description="Exact verbatim 4-8 words where this topic ended")
    evidence_summary: str = Field(description="1-2 sentences summarizing key testimony in this span")

class TopicSegmentationResult(BaseModel):
    topics: List[TopicSpan]

SYSTEM_PROMPT = """You are an expert AI Litigation Specialist analyzing a deposition transcript.
Your job is to identify distinct topics discussed in the testimony.

Rules:
1. Topic labels must be concise, substantive legal or factual categories (e.g., 'Retention and Default Rates at ITT', 'Role of Vervent in Servicing vs Origination').
2. Provide verbatim quotes for `start_quote` and `end_quote` so they can be mapped to exact line numbers.
3. Do not invent line numbers. Only supply topic labels, quotes, and concise summaries.
4. Distinguish brief objections or procedural digressions from actual topic shifts.
"""

def process_chunk(chunk_text: str) -> List[TopicSpan]:
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript segment:\n{chunk_text}"}
        ],
        response_format=TopicSegmentationResult,
        temperature=0.0  # Crucial for stability tests!
    )
    return response.choices[0].message.parsed.topics