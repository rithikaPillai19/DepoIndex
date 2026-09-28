import pandas as pd
from typing import Tuple, List, Dict, Any

class DepoIndexValidator:
    def __init__(self, df: pd.DataFrame, min_anchor_score: float = 82.0):
        self.df = df
        self.min_anchor_score = min_anchor_score

    def validate_pillar_1_coordinates(self, start_res: Dict[str, Any], end_res: Dict[str, Any]) -> Tuple[bool, str]:
        """Pillar 1: Coordinate Verifiability & Anchor Precision."""
        if start_res.get("global_id") is None or end_res.get("global_id") is None:
            return False, "Failed to resolve start or end coordinate anchor."
        if start_res.get("score", 0.0) < self.min_anchor_score:
            return False, f"Start quote anchor score ({start_res.get('score'):.1f}) below threshold {self.min_anchor_score}."
        if end_res.get("score", 0.0) < self.min_anchor_score:
            return False, f"End quote anchor score ({end_res.get('score'):.1f}) below threshold {self.min_anchor_score}."
        if start_res["global_id"] > end_res["global_id"]:
            return False, f"Coordinate inversion: Start GID {start_res['global_id']} > End GID {end_res['global_id']}."
        return True, "PASSED"

    def validate_pillar_2_boundary(self, start_gid: int, end_gid: int) -> Tuple[bool, str]:
        """Pillar 2: Boundary Integrity, Dialogue Initiation & Sentence Completion."""
        if start_gid < 0 or end_gid >= len(self.df):
            return False, "Coordinates index out of bounds."

        # Verify Start: Must not anchor to blank or pure punctuation
        start_text = str(self.df.iloc[start_gid]["text"]).strip()
        if len(start_text) < 3 or start_text.replace("-", "").strip() == "":
            return False, f"Start coordinate GID {start_gid} lands on blank or non-substantive line."

        # Verify End: Sentence closure check (must end with terminal punctuation or speaker transition)
        end_text = str(self.df.iloc[end_gid]["text"]).strip()
        terminal_chars = ('.', '?', '!', '"', "'")
        ends_cleanly = end_text.endswith(terminal_chars)

        if not ends_cleanly and end_gid + 1 < len(self.df):
            next_text = str(self.df.iloc[end_gid + 1]["text"]).strip()
            if not any(next_text.startswith(spk) for spk in ["Q.", "A.", "MR.", "MS.", "THE WITNESS"]):
                return False, f"Mid-sentence break detected at GID {end_gid}: '{end_text[-25:]}'"

        return True, "PASSED"

    def validate_pillar_3_semantic_support(self, topic: str, start_gid: int, end_gid: int) -> Tuple[bool, str]:
        """Pillar 3: Independent Semantic Support (Checks lexical alignment with text)."""
        words = topic.strip().split()
        if len(words) < 2 or len(words) > 16:
            return False, f"Topic title length ({len(words)} words) violates legal indexing standard."

        slice_df = self.df.iloc[start_gid : end_gid + 1]
        slice_corpus = " ".join([str(t).lower() for t in slice_df["text"].tolist()])

        # Independent support verification
        topic_stems = [
            w.lower().strip(":,.") for w in words 
            if len(w) > 3 and w.lower() not in ["about", "their", "under", "which", "with", "from"]
        ]
        if topic_stems and not any(stem in slice_corpus for stem in topic_stems):
            return False, f"Topic '{topic}' has no lexical grounding in cited coordinate slice."

        return True, "PASSED"

    def validate_pillar_4_evidence_grounding(self, evidence: str, start_gid: int, end_gid: int) -> Tuple[bool, str]:
        """Pillar 4: Evidence Entailment & Anti-Hallucination Entity Grounding."""
        if len(evidence.strip()) < 25:
            return False, "Evidence summary lacks sufficient factual detail (< 25 characters)."

        slice_df = self.df.iloc[start_gid : end_gid + 1]
        slice_text = " ".join([str(t) for t in slice_df["text"].tolist()])

        evidence_words = evidence.replace("(", " ").replace(")", " ").replace(".", " ").split()
        
        # Capture proper nouns and acronyms (len >= 2 with uppercase, e.g., CFPB, TILA, Biden)
        named_entities = [
            w.strip(",;:'\"") for w in evidence_words 
            if len(w) >= 2 and w[0].isupper() and w.lower() not in [
                "the", "this", "that", "witness", "testifies", "states", "regarding", 
                "admits", "concerning", "these", "those"
            ]
        ]

        missing_entities = [ent for ent in named_entities if ent.lower() not in slice_text.lower()]
        
        # If any specific named entity or agency is completely absent, reject
        if len(missing_entities) >= 1:
            return False, f"Evidence cites entity '{missing_entities[0]}' not present in coordinate slice."

        return True, "PASSED"

    def validate_all(self, topic: str, evidence: str, start_res: Dict[str, Any], end_res: Dict[str, Any]) -> Tuple[bool, List[str]]:
        failures = []
        p1_ok, p1_msg = self.validate_pillar_1_coordinates(start_res, end_res)
        if not p1_ok: 
            failures.append(f"Pillar 1: {p1_msg}")

        s_gid = start_res.get("global_id", -1)
        e_gid = end_res.get("global_id", -1)

        if s_gid is not None and e_gid is not None and s_gid >= 0 and e_gid >= 0:
            p2_ok, p2_msg = self.validate_pillar_2_boundary(s_gid, e_gid)
            if not p2_ok: 
                failures.append(f"Pillar 2: {p2_msg}")

            p3_ok, p3_msg = self.validate_pillar_3_semantic_support(topic, s_gid, e_gid)
            if not p3_ok: 
                failures.append(f"Pillar 3: {p3_msg}")

            p4_ok, p4_msg = self.validate_pillar_4_evidence_grounding(evidence, s_gid, e_gid)
            if not p4_ok: 
                failures.append(f"Pillar 4: {p4_msg}")

        return len(failures) == 0, failures