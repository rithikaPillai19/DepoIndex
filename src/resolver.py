import re
import pandas as pd
from rapidfuzz import fuzz
from typing import Dict, Any

class ProvenanceResolver:
    """
    Deterministically resolves and sanitizes verbatim transcript citations.
    Enforces sentence boundary integrity, speaker alignment, and zero-gap snapping.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.normalized_lines = [str(t).lower().strip() for t in self.df["text"].tolist()]

    def resolve_quote(self, quote: str, search_start_id: int = 0, search_window: int = 150) -> Dict[str, Any]:
        if not quote or len(quote.strip()) < 5:
            return {"global_id": None, "page": None, "line": None, "score": 0.0}

        clean_q = quote.lower().strip()
        start_idx = max(0, search_start_id)
        end_idx = min(len(self.df), start_idx + search_window)

        best_score = 0.0
        best_gid = None

        # 1. Exact Substring Search
        for gid in range(start_idx, end_idx):
            line_txt = self.normalized_lines[gid]
            if clean_q in line_txt or line_txt in clean_q:
                best_score = 100.0
                best_gid = gid
                break

        # 2. Multi-line Slotted Fuzzy Search
        if best_gid is None:
            for span_len in [1, 2, 3]:
                for gid in range(start_idx, end_idx - span_len + 1):
                    window_text = " ".join(self.normalized_lines[gid : gid + span_len])
                    score = fuzz.partial_ratio(clean_q, window_text)
                    if score > best_score and score >= 68.0:
                        best_score = score
                        best_gid = gid

        if best_gid is not None:
            row = self.df.iloc[best_gid]
            return {
                "global_id": int(best_gid),
                "page": int(row["page"]),
                "line": int(row["line"]),
                "text": str(row["text"]),
                "score": float(best_score)
            }

        return {"global_id": None, "page": None, "line": None, "score": 0.0}

    def snap_to_speaker_start(self, gid: int) -> int:
        """Requirement 4: Ensures start citation never lands on a blank or incomplete line."""
        max_idx = len(self.df) - 1
        current = min(max(0, gid), max_idx)

        # Walk backward to find the initiating 'Q.' or 'BY MR.' if within 3 lines
        for back_idx in range(current, max(0, current - 3), -1):
            txt = str(self.df.iloc[back_idx]["text"]).strip()
            if re.match(r"^(?:Q\.|BY\s+MR\.|BY\s+MS\.)", txt, re.IGNORECASE):
                return back_idx

        # Otherwise ensure text is substantive
        while current < max_idx:
            txt = str(self.df.iloc[current]["text"]).strip()
            if len(txt) > 3 and not re.match(r"^[-—\s]+$", txt):
                return current
            current += 1
        return current

    def snap_to_sentence_end(self, gid: int) -> int:
        """Requirement 4: Forbids mid-sentence splits (e.g. Page 52 Lines 24-25)."""
        max_idx = len(self.df) - 1
        current = min(max(0, gid), max_idx)

        while current < max_idx:
            txt = str(self.df.iloc[current]["text"]).strip()
            # If current line ends with sentence terminator, boundary is complete
            if re.search(r'[.?!"\']$', txt):
                return current
            # Check next line: if next line starts a new speaker, stop here anyway
            next_txt = str(self.df.iloc[current + 1]["text"]).strip()
            if re.match(r"^(?:Q\.|A\.|MR\.|MS\.|THE\s+WITNESS|THE\s+COURT)", next_txt, re.IGNORECASE):
                return current
            current += 1

        return current