import pandas as pd
from typing import Dict, Any, List, Tuple

class DepoIndexValidator:
    """
    Enforces the 4-Pillar Validation Framework for litigation deposition indexing:
    - Pillar 1: Coordinate existence & anchor confidence score
    - Pillar 2: Monotonic boundary integrity & span breadth
    - Pillar 3: Semantic topic validity
    - Pillar 4: Substantive factual evidence verification
    """

    def __init__(self, df: pd.DataFrame, canonical_taxonomy: List[str] = None, min_score: float = 70.0):
        self.df = df
        self.canonical_taxonomy = canonical_taxonomy or []
        self.min_score = min_score

    def validate_coordinates(self, start_res: Dict[str, Any], end_res: Dict[str, Any]) -> Tuple[bool, str]:
        """Pillar 1: Coordinate existence and provenance score threshold."""
        if start_res.get("global_id") is None or end_res.get("global_id") is None:
            return False, "Unresolved quote coordinates: start or end global_id is None."

        start_score = start_res.get("score", 0.0)
        end_score = end_res.get("score", 0.0)

        if start_score < self.min_score:
            return False, f"Start quote match score ({start_score:.1f}%) below minimum threshold ({self.min_score}%)."
        if end_score < self.min_score:
            return False, f"End quote match score ({end_score:.1f}%) below minimum threshold ({self.min_score}%)."

        return True, "Passed coordinate validation."

    def validate_boundary(self, start_gid: int, end_gid: int, min_lines: int = 2) -> Tuple[bool, str]:
        """Pillar 2: Boundary monotonicity and minimum line span."""
        if start_gid is None or end_gid is None:
            return False, "Null global boundary IDs."

        if end_gid < start_gid:
            return False, f"Boundary inversion detected: end_gid ({end_gid}) precedes start_gid ({start_gid})."

        span_length = end_gid - start_gid + 1
        if span_length < min_lines:
            return False, f"Span too brief ({span_length} lines); does not represent substantive inquiry."

        return True, "Passed boundary validation."

    def validate_semantic(self, topic: str) -> Tuple[bool, str]:
        """Pillar 3: Semantic topic check against taxonomy or structural rules."""
        if not topic or not isinstance(topic, str):
            return False, "Topic string is null or empty."

        clean_topic = topic.strip()
        words = clean_topic.split()

        if len(words) < 2:
            return False, f"Topic '{clean_topic}' is too short/generic."
        if len(words) > 16:
            return False, f"Topic '{clean_topic}' exceeds macro-title length."

        # Procedural noise filter
        noise_markers = ["form objection", "off the record", "recess", "reporter question"]
        if any(marker in clean_topic.lower() for marker in noise_markers):
            return False, f"Topic '{clean_topic}' contains non-substantive conversational noise."

        # Check taxonomy membership if taxonomy is configured
        if self.canonical_taxonomy:
            if clean_topic not in self.canonical_taxonomy:
                # Soft match check
                matched = any(clean_topic.lower() == t.lower() for t in self.canonical_taxonomy)
                if not matched:
                    return False, f"Topic '{clean_topic}' does not conform to defined canonical taxonomy."

        return True, "Passed semantic validation."

    def validate_evidence(self, evidence_summary: str) -> Tuple[bool, str]:
        """Pillar 4: Evidence factual presence and depth check."""
        if not evidence_summary or not isinstance(evidence_summary, str):
            return False, "Supporting evidence summary is empty."

        clean_ev = evidence_summary.strip()
        if len(clean_ev) < 25 or len(clean_ev.split()) < 5:
            return False, "Supporting evidence summary lacks sufficient substantive detail."

        return True, "Passed evidence validation."

    def execute_fallback(
        self,
        candidate: Dict[str, Any],
        start_res: Dict[str, Any],
        end_res: Dict[str, Any],
        failures: List[str]
    ) -> Dict[str, Any]:
        """Pillar 5 / Fallback logging: flags failed entries cleanly for audit inspection."""
        s_page = start_res.get("page", "Unknown")
        s_line = start_res.get("line", "Unknown")
        e_page = end_res.get("page", "Unknown")
        e_line = end_res.get("line", "Unknown")

        return {
            "topic": candidate.get("topic", "Unspecified Inquiry"),
            "start": f"Page {s_page}, Line {s_line}",
            "end": f"Page {e_page}, Line {e_line}",
            "start_gid": start_res.get("global_id", 0),
            "end_gid": end_res.get("global_id", 0),
            "supporting_evidence": candidate.get("evidence", "No evidence summary provided."),
            "validation_status": "FALLBACK_TRIGGERED",
            "validation_failures": failures,
            "validation_scores": {
                "start_score": start_res.get("score", 0.0),
                "end_score": end_res.get("score", 0.0)
            },
            "anchors": {
                "start_quote": start_res.get("matched_text", ""),
                "end_quote": end_res.get("matched_text", "")
            }
        }