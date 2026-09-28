"""
Provenance Resolver with Empirical Calibration Threshold (82.0) and Dialogue Snapping.
"""
import pandas as pd
from rapidfuzz import fuzz
from typing import Dict, Any

CALIBRATED_ANCHOR_THRESHOLD = 82.0
MIN_QUOTE_LENGTH = 18

class ProvenanceResolver:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.normalized_lines = [str(t).lower().strip() for t in self.df["text"].tolist()]

    def resolve_quote(self, quote: str, search_start_id: int = 0, search_window: int = 160) -> Dict[str, Any]:
        if not quote or len(quote.strip()) < 4:
            return {"global_id": None, "page": None, "line": None, "score": 0.0}

        clean_q = quote.lower().strip()
        start_idx = max(0, search_start_id)
        end_idx = min(len(self.df), start_idx + search_window)

        # 1. Exact Substring Search
        for gid in range(start_idx, end_idx):
            line_txt = self.normalized_lines[gid]
            if clean_q in line_txt or (len(clean_q) > 20 and line_txt in clean_q):
                row = self.df.iloc[gid]
                return {
                    "global_id": int(gid),
                    "page": int(row["page"]),
                    "line": int(row["line"]),
                    "text": str(row["text"]),
                    "score": 100.0
                }

        # 2. Multi-line Slotted Fuzzy Search with Empirical Thresholding
        best_score = 0.0
        best_gid = None

        for span_len in [1, 2, 3]:
            for gid in range(start_idx, end_idx - span_len + 1):
                window_text = " ".join(self.normalized_lines[gid : gid + span_len])
                score = fuzz.partial_ratio(clean_q, window_text)
                if score > best_score:
                    best_score = score
                    best_gid = gid

        if best_gid is not None and best_score >= CALIBRATED_ANCHOR_THRESHOLD:
            row = self.df.iloc[best_gid]
            return {
                "global_id": int(best_gid),
                "page": int(row["page"]),
                "line": int(row["line"]),
                "text": str(row["text"]),
                "score": float(best_score)
            }

        return {"global_id": None, "page": None, "line": None, "score": float(best_score)}

    def snap_to_speaker_start(self, gid: int) -> int:
        """Requirement 4: Anchors start to valid initiating speaker line."""
        max_idx = len(self.df) - 1
        current = min(max(0, gid), max_idx)

        # Look back up to 3 lines for an initiating question tag
        for back_idx in range(current, max(0, current - 3), -1):
            txt = str(self.df.iloc[back_idx]["text"]).strip()
            if any(txt.startswith(pfx) for pfx in ["Q.", "BY MR.", "BY MS."]):
                return back_idx

        # Otherwise ensure line is substantive
        while current < max_idx:
            txt = str(self.df.iloc[current]["text"]).strip()
            if len(txt) > 3 and not txt.replace("-", "").strip() == "":
                return current
            current += 1
        return current

    def snap_to_sentence_end(self, gid: int) -> int:
        """Requirement 4: Forbids mid-sentence splits (e.g. Page 52 Lines 24-25)."""
        max_idx = len(self.df) - 1
        current = min(max(0, gid), max_idx)

        while current < max_idx:
            txt = str(self.df.iloc[current]["text"]).strip()
            if txt.endswith(('.', '?', '!', '"', "'")):
                return current
            if current + 1 < len(self.df):
                next_txt = str(self.df.iloc[current + 1]["text"]).strip()
                if any(next_txt.startswith(pfx) for pfx in ["Q.", "A.", "MR.", "MS.", "THE WITNESS"]):
                    return current
            current += 1
        return current
    def recover_quote_anchor(self, quote: str, search_start_id: int, window: int = 180) -> Dict[str, Any]:
        """Bounded repair strategy: strips conversational filler and expands window by 15 lines."""
        fillers = ["you know", "uh", "um", "i mean", "like", "so"]
        cleaned_quote = quote.lower()
        for f in fillers:
            cleaned_quote = cleaned_quote.replace(f, " ")
        cleaned_quote = " ".join(cleaned_quote.split())

        # Attempt search with adjusted window (+15 lines)
        return self.resolve_quote(cleaned_quote, search_start_id=max(0, search_start_id - 10), search_window=window + 15)