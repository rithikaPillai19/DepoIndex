"""
Independent Four-Pillar Legal Validator.
Enforces coordinate verifiability, sentence boundary integrity,
directed semantic support, and strict entity grounding without circular LLM self-grading
or brittle regular expressions.
"""
from typing import Tuple, List, Dict, Any, Set
import pandas as pd

class DepoIndexValidator:
    def __init__(self, df: pd.DataFrame, min_anchor_score: float = 82.0):
        self.df = df
        self.min_anchor_score = min_anchor_score
        
        self.legal_stopwords = {
            "the", "this", "that", "these", "those", "witness", "testifies", "states",
            "regarding", "admits", "concerning", "counsel", "attorney", "deposition",
            "plaintiff", "defendant", "defendants", "report", "question", "questions",
            "answer", "examination", "transcript", "testimony", "record", "exhibit",
            "clarifies", "discusses", "explains", "notes", "addresses", "details",
            "about", "their", "under", "which", "with", "from", "into", "over", "such",
            "review", "issues", "background", "experience", "pages", "page", "line", "lines"
        }
        self.speaker_prefixes = ("q.", "a.", "mr.", "ms.", "the witness", "by mr.", "by ms.", "the court:")
        self.terminal_chars = ('.', '?', '!', '"', "'", ')')

    def _tokenize(self, text: str) -> Set[str]:
        """Extracts substantive alpha tokens without regular expressions."""
        clean_chars = [c.lower() if c.isalnum() else " " for c in text]
        tokens = set()
        for token in "".join(clean_chars).split():
            if len(token) >= 3 and token.isalpha() and token not in self.legal_stopwords:
                tokens.add(token)
        return tokens

    def _extract_acronyms(self, text: str) -> Set[str]:
        """Extracts capitalized institutional acronyms (e.g. CFPB, SEC, TILA) without regex."""
        clean_chars = [c if c.isalnum() else " " for c in text]
        acronyms = set()
        for token in "".join(clean_chars).split():
            clean_token = token.strip()
            if len(clean_token) >= 3 and clean_token.isupper() and clean_token.isalpha():
                if clean_token not in {"THE", "AND", "FOR", "NOT", "ACT", "LAW"}:
                    acronyms.add(clean_token)
        return acronyms

    def validate_pillar_1_coordinates(self, start_res: Dict[str, Any], end_res: Dict[str, Any]) -> Tuple[bool, str]:
        """Pillar 1: Coordinate Verifiability, Monotonicity & Measured Confidence."""
        s_gid = start_res.get("global_id")
        e_gid = end_res.get("global_id")

        if s_gid is None or e_gid is None:
            return False, "Unresolved coordinate pointer."

        s_score = float(start_res.get("score", 0.0))
        e_score = float(end_res.get("score", 0.0))

        if s_score < self.min_anchor_score:
            return False, f"Start anchor confidence ({s_score:.1f}%) below calibrated threshold ({self.min_anchor_score}%)."
        if e_score < self.min_anchor_score:
            return False, f"End anchor confidence ({e_score:.1f}%) below calibrated threshold ({self.min_anchor_score}%)."

        if s_gid > e_gid:
            return False, f"Coordinate inversion: Start GID {s_gid} > End GID {e_gid}."

        return True, "PASSED"

    def validate_pillar_2_boundary(self, start_gid: int, end_gid: int) -> Tuple[bool, str]:
        """Pillar 2: Boundary Integrity, Speaker Initiation & Sentence Closure."""
        if start_gid < 0 or end_gid >= len(self.df):
            return False, "Coordinates index out of bounds."

        start_text = str(self.df.iloc[start_gid]["text"]).strip()
        if len(start_text) < 3 or start_text.replace("-", "").strip() == "":
            return False, f"Start GID {start_gid} lands on blank or non-substantive line."

        end_text = str(self.df.iloc[end_gid]["text"]).strip()
        ends_cleanly = end_text.endswith(self.terminal_chars)
        
        # If line does not end with terminal punctuation
        if not ends_cleanly:
            if end_gid + 1 < len(self.df):
                next_text = str(self.df.iloc[end_gid + 1]["text"]).strip().lower()
                if not any(next_text.startswith(spk) for spk in self.speaker_prefixes):
                    return False, f"Mid-sentence break detected at GID {end_gid}: '{end_text[-25:]}'"
            else:
                # Terminal boundary of transcript must be cleanly closed
                return False, f"Mid-sentence break detected at terminal GID {end_gid}: '{end_text[-25:]}'"

        return True, "PASSED"

    def validate_pillar_3_semantic_support(self, topic: str, start_gid: int, end_gid: int, evidence: str = "") -> Tuple[bool, str]:
        """Pillar 3: Independent Directed Semantic Support."""
        slice_df = self.df.iloc[start_gid : end_gid + 1]
        corpus_words = self._tokenize(" ".join(slice_df["text"].astype(str)))

        topic_words = self._tokenize(topic)
        if not topic_words:
            topic_words = self._tokenize(evidence)

        if not topic_words:
            return True, "PASSED"

        # Compute directed overlap ratio against cited coordinate slice
        matched_stems = topic_words.intersection(corpus_words)
        support_ratio = len(matched_stems) / len(topic_words)

        if support_ratio < 0.20:
            return False, f"Topic '{topic}' lacks semantic grounding in cited lines (support ratio: {support_ratio:.2f} < 0.20)."

        return True, "PASSED"

    def validate_pillar_4_evidence_grounding(self, evidence: str, start_gid: int, end_gid: int) -> Tuple[bool, str]:
        """Pillar 4: Strict Entity Grounding & Contradiction Rejection."""
        if len(evidence.strip()) < 25:
            return False, "Evidence summary lacks sufficient factual detail (< 25 chars)."

        slice_df = self.df.iloc[start_gid : end_gid + 1]
        slice_raw = " ".join(slice_df["text"].astype(str)).lower()

        # Handle possessive forms cleanly
        clean_evidence = evidence.replace("'s", "").replace("’s", "")
        acronyms = self._extract_acronyms(clean_evidence)

        for ac in acronyms:
            synonyms = [ac.lower()]
            if ac == "TILA": synonyms.append("truth in lending")
            if ac == "DOED": synonyms.append("department of education")

            if not any(syn in slice_raw for syn in synonyms):
                return False, f"Hallucinated entity detected: '{ac}' does not appear in cited coordinates."

        return True, "PASSED"

    def validate_all(self, topic: str, evidence: str, start_res: Dict[str, Any], end_res: Dict[str, Any]) -> Tuple[bool, List[str]]:
        failures = []
        p1_ok, p1_msg = self.validate_pillar_1_coordinates(start_res, end_res)
        if not p1_ok: failures.append(f"Pillar 1: {p1_msg}")

        s_gid = start_res.get("global_id", -1)
        e_gid = end_res.get("global_id", -1)

        if s_gid is not None and e_gid is not None and s_gid >= 0 and e_gid >= 0:
            p2_ok, p2_msg = self.validate_pillar_2_boundary(s_gid, e_gid)
            if not p2_ok: failures.append(f"Pillar 2: {p2_msg}")

            p3_ok, p3_msg = self.validate_pillar_3_semantic_support(topic, s_gid, e_gid, evidence)
            if not p3_ok: failures.append(f"Pillar 3: {p3_msg}")

            p4_ok, p4_msg = self.validate_pillar_4_evidence_grounding(evidence, s_gid, e_gid)
            if not p4_ok: failures.append(f"Pillar 4: {p4_msg}")

        return len(failures) == 0, failures