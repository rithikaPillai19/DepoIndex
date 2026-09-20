from rapidfuzz import fuzz, process
import pandas as pd

class ProvenanceResolver:
    def __init__(self, transcript_df: pd.DataFrame):
        self.df = transcript_df
        self.normalized_lines = [str(t).lower().strip() for t in self.df["text"].tolist()]

    def resolve_quote(self, quote: str, search_start_id: int = 0, search_window: int = 250):
        if not quote or not str(quote).strip():
            return {"page": None, "line": None, "global_id": search_start_id, "score": 0.0, "status": "EMPTY"}

        clean_quote = str(quote).lower().strip()
        search_end_id = min(search_start_id + search_window, len(self.normalized_lines))
        candidates = self.normalized_lines[search_start_id:search_end_id]

        if not candidates:
            candidates = self.normalized_lines
            search_start_id = 0

        match = process.extractOne(clean_quote, candidates, scorer=fuzz.partial_ratio)

        if match:
            matched_text, raw_score, relative_idx = match
            score = round(float(raw_score), 2)
            actual_global_id = search_start_id + relative_idx
            row = self.df.iloc[actual_global_id]

            return {
                "page": int(row["page"]),
                "line": int(row["line"]),
                "global_id": actual_global_id,
                "score": score,
                "matched_text": self.df.iloc[actual_global_id]["text"]
            }

        return {"page": None, "line": None, "global_id": search_start_id, "score": 0.0, "status": "UNRESOLVED"}