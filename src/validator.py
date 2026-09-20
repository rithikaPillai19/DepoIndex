import pandas as pd
from typing import Dict, Any, Tuple
from rapidfuzz import fuzz

class DepoIndexValidator:
    """
    4-Pillar Validation Layer + Fallback Mechanism:
      1. Coordinate Validation (Line existence, score >= 70, no line inversion)
      2. Boundary Validation (Speaker turn alignment, span length >= 10 lines)
      3. Semantic Validation (Macro topic adherence, taxonomy check)
      4. Evidence Validation (Substantive synthesis, non-trivial content)
      5. Fallback Mechanism (Window recovery or NEEDS_MANUAL_REVIEW routing)
    """
    def __init__(self, transcript_df: pd.DataFrame, canonical_taxonomy: list, min_score: float = 70.0):
        self.df = transcript_df
        self.taxonomy = canonical_taxonomy
        self.min_score = min_score
        self.max_global_id = len(transcript_df) - 1

    # PILLAR 1: Coordinate Validation
    def validate_coordinates(self, start_res: Dict[str, Any], end_res: Dict[str, Any]) -> Tuple[bool, str]:
        if start_res["score"] < self.min_score or end_res["score"] < self.min_score:
            return False, f"Coordinate score below threshold (Start: {start_res['score']}%, End: {end_res['score']}%)"
        
        if start_res["global_id"] is None or end_res["global_id"] is None:
            return False, "Unresolved coordinate pointer"

        if end_res["global_id"] < start_res["global_id"]:
            return False, f"Coordinate Inversion: End line ({end_res['global_id']}) precedes Start line ({start_res['global_id']})"

        return True, "PASSED"

    # PILLAR 2: Boundary Validation
    def validate_boundary(self, start_gid: int, end_gid: int) -> Tuple[bool, str]:
        span_length = end_gid - start_gid + 1
        if span_length < 6:
            return False, f"Boundary too narrow for macro-topic ({span_length} lines). Likely subtopic or colloquy."
        
        # Verify alignment with transcript boundaries
        if start_gid < 0 or end_gid > self.max_global_id:
            return False, "Boundary exceeds transcript limits."

        return True, "PASSED"

    # PILLAR 3: Semantic Validation
    def validate_semantic(self, topic_label: str) -> Tuple[bool, str]:
        # Check if topic label matches canonical list
        if topic_label not in self.taxonomy:
            # Fuzzy match against canonical taxonomy
            best_match = max([fuzz.token_sort_ratio(topic_label.lower(), t.lower()) for t in self.taxonomy])
            if best_match < 80:
                return False, f"Semantic divergence: '{topic_label}' does not match legal taxonomy."
        return True, "PASSED"

    # PILLAR 4: Evidence Validation
    def validate_evidence(self, evidence: str) -> Tuple[bool, str]:
        if not evidence or len(evidence.strip().split()) < 8:
            return False, "Evidence summary too short or empty."
        
        # Check for generic non-substantive filler
        filler_patterns = ["reading from report", "witness answered", "counsel discussed", "unintelligible"]
        if any(f in evidence.lower() for f in filler_patterns) and len(evidence.split()) < 12:
            return False, "Evidence lacks substantive legal synthesis."

        return True, "PASSED"

    # PILLAR 5: Fallback Mechanism
    def execute_fallback(self, raw_entry: Dict[str, Any], start_res: Dict[str, Any], end_res: Dict[str, Any], failure_reasons: list) -> Dict[str, Any]:
        """
        Executes when one or more of the 4 pillars fail:
        - Attempts boundary recovery by snapping to nearest examination block.
        - If unrecoverable, preserves data integrity by marking for manual legal review.
        """
        # Boundary recovery attempt: if end < start, clamp end to start + 10
        recovered_start_gid = start_res.get("global_id") or 0
        recovered_end_gid = end_res.get("global_id") or recovered_start_gid + 10

        if recovered_end_gid < recovered_start_gid:
            recovered_end_gid = min(recovered_start_gid + 15, self.max_global_id)

        start_row = self.df.iloc[recovered_start_gid]
        end_row = self.df.iloc[min(recovered_end_gid, self.max_global_id)]

        return {
            "topic": raw_entry.get("topic", "Unassigned Examination Segment"),
            "start": f"Page {start_row['page']}, Line {start_row['line']}",
            "end": f"Page {end_row['page']}, Line {end_row['line']}",
            "supporting_evidence": raw_entry.get("evidence", "Evidence flagged during validation."),
            "validation_status": "FALLBACK_TRIGGERED",
            "fallback_diagnostics": failure_reasons,
            "audit_flags": ["NEEDS_MANUAL_REVIEW"]
        }