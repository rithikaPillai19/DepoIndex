import pytest
import pandas as pd
from src.validator import DepoIndexValidator
from src.resolver import ProvenanceResolver

@pytest.fixture
def sample_transcript_df():
    data = [
        {"global_id": 0, "page": 7, "line": 11, "text": "BY MR. PURCELL:"},
        {"global_id": 1, "page": 7, "line": 12, "text": "Q. Good afternoon, Ms. Yu."},
        {"global_id": 2, "page": 7, "line": 13, "text": "A. Good afternoon."},
        {"global_id": 3, "page": 52, "line": 24, "text": "A. That's correct. That was outside the"},
        {"global_id": 4, "page": 52, "line": 25, "text": "scope of my report."},
        {"global_id": 5, "page": 88, "line": 17, "text": "(Deposition concluded at 3:42 PM.)"}
    ]
    return pd.DataFrame(data)

def test_pillar_2_rejects_blank_line_start():
    blank_df = pd.DataFrame([{"global_id": 0, "page": 7, "line": 5, "text": "   ---   "}])
    validator = DepoIndexValidator(blank_df)
    is_valid, msg = validator.validate_pillar_2_boundary(0, 0)
    assert not is_valid
    assert "blank or non-substantive line" in msg

def test_pillar_2_detects_mid_sentence_split(sample_transcript_df):
    validator = DepoIndexValidator(sample_transcript_df)
    # GID 3 ends in "outside the", which is not a complete sentence
    is_valid, msg = validator.validate_pillar_2_boundary(3, 3)
    assert not is_valid
    assert "Mid-sentence break detected" in msg

def test_resolver_snaps_to_sentence_end(sample_transcript_df):
    resolver = ProvenanceResolver(sample_transcript_df)
    snapped_gid = resolver.snap_to_sentence_end(3)
    assert snapped_gid == 4
    assert sample_transcript_df.iloc[snapped_gid]["text"].endswith(".")

def test_pillar_4_entity_grounding_rejects_hallucination(sample_transcript_df):
    validator = DepoIndexValidator(sample_transcript_df)
    # Summary references entities not present in GID 0-2
    ungrounded_evidence = "Witness discusses President Biden's student debt forgiveness plan under TILA."
    is_valid, msg = validator.validate_pillar_4_evidence_grounding(ungrounded_evidence, 0, 2)
    assert not is_valid
    assert "not present in coordinate slice" in msg
def test_revalidation_gate_rejects_mutated_hallucination(sample_transcript_df):
    """The Revalidation Gate must reject a mutated entry if an invalid summary was merged in."""
    validator = DepoIndexValidator(sample_transcript_df)
    # Valid topic and coordinates (GID 0 to 2) but corrupted summary referencing absent agency "CFPB"
    mutated_bad_evidence = "Witness admits to violating CFPB regulations regarding loan forgiveness."
    s_res = {"global_id": 0, "score": 100.0}
    e_res = {"global_id": 2, "score": 100.0}
    
    is_valid, failures = validator.validate_all("Purcell Afternoon Greetings", mutated_bad_evidence, s_res, e_res)
    assert not is_valid
    assert any("Pillar 4" in f for f in failures)