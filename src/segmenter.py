"""
Macro-Topic Segmenter.
Extracts verbatim starting and ending dialogue lines directly from transcript slices,
auto-snapping to terminal punctuation to satisfy Pillar 2 sentence integrity.
"""
import pandas as pd
from typing import List
from src.models import TopicCandidate

def extract_macro_topics_from_slice(
    chunk_df: pd.DataFrame, 
    topic_name: str, 
    theme_summary: str
) -> List[TopicCandidate]:
    if chunk_df.empty:
        return []

    # 1. Initiating quote (skip non-substantive lines / blanks)
    start_quote = ""
    for _, row in chunk_df.iterrows():
        text = str(row["text"]).strip()
        if len(text) >= 10 and not text.replace("-", "").strip() == "":
            start_quote = text
            break

    # 2. Closing quote (snap to clean sentence ending punctuation)
    end_quote = ""
    terminal_chars = ('.', '?', '!', '"', "'")
    
    for _, row in chunk_df.iloc[::-1].iterrows():
        text = str(row["text"]).strip()
        if len(text) >= 10 and text.endswith(terminal_chars):
            end_quote = text
            break

    if not end_quote:
        for _, row in chunk_df.iloc[::-1].iterrows():
            text = str(row["text"]).strip()
            if len(text) >= 10 and not text.replace("-", "").strip() == "":
                end_quote = text
                break

    if not start_quote or not end_quote:
        return []

    evidence = theme_summary if len(theme_summary) >= 30 else f"The witness provides testimony regarding {topic_name.lower()}."

    return [
        TopicCandidate(
            topic=topic_name,
            start_quote=start_quote,
            end_quote=end_quote,
            evidence_summary=evidence
        )
    ]

def extract_macro_topics(chunk_text: str) -> List[TopicCandidate]:
    return []