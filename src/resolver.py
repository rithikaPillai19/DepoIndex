from rapidfuzz import fuzz
import pandas as pd

class ProvenanceResolver:
    def __init__(self, transcript_df: pd.DataFrame):
        self.df = transcript_df

    def find_line_for_quote(self, quote: str, search_start_id: int = 0, window: int = 300) -> dict:
        """
        Finds the exact line matching the quote using fuzzy search over a rolling window.
        Returns a dict: {'page': int, 'line': int, 'global_id': int}
        """
        quote_clean = quote.lower().strip()
        best_score = -1.0
        best_match = None

        search_slice = self.df.iloc[search_start_id : search_start_id + window]
        
        for _, row in search_slice.iterrows():
            row_text = row["text"].lower()
            score = fuzz.partial_ratio(quote_clean, row_text)
            if score > best_score:
                best_score = score
                best_match = row

        if best_match is not None and best_score >= 70:
            return {
                "page": int(best_match["page"]),
                "line": int(best_match["line"]),
                "global_id": int(best_match["global_id"])
            }
        fallback = self.df.iloc[search_start_id]
        return {
            "page": int(fallback["page"]),
            "line": int(fallback["line"]),
            "global_id": int(fallback["global_id"])
        }