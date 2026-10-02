"""
Adversarial Test Suite.
Verifies that hallucinated entities, mid-sentence cuts, unsupported topics,
and unverified post-mutation states FAIL CLOSED.
"""
import pytest
import pandas as pd
from src.validator import DepoIndexValidator

@pytest.fixture
def mock_transcript():
    data = [
        {"global_id": 0, "page": 7, "line": 11, "text": "Q. Good afternoon, Ms. Yu."},
        {"global_id": 1, "page": 7, "line": 12, "text": "A. Good afternoon."},
        {"global_id": 2, "page": 7, "line": 13, "text": "Q. Are you an attorney?"},
        {"global_id": 3, "page": 7, "line": 14, "text": "A. Yes, I am admitted to practice in Massachusetts."},
        {"global_id": 4, "page": 7, "line": 15, "text": "Q. Did you review the loan disclosures?"},
        {"global_id": 5, "page": 7, "line": 16, "text": "A. I reviewed the CFPB materials and PEAKS notes."},
        {"global_id": 6, "page": 7, "line": 17, "text": "Q. Did you review anything regarding"}  # mid-sentence cut
    ]
    return pd.DataFrame(data)

def test_adversarial_hallucinated_entity_fails_closed(mock_transcript):
    """Pillar 4 must reject entities not present in the coordinate slice."""
    validator = DepoIndexValidator(mock_transcript)
    topic = "Review of Loan Disclosures and Legal Qualifications"
    fake_evidence = "The witness testifies regarding investigations conducted by the SEC and DOJ."
    
    is_valid, failures = validator.validate_all(
        topic, fake_evidence,
        {"global_id": 0, "score": 95.0},
        {"global_id": 5, "score": 95.0}
    )
    assert not is_valid
    assert any("Hallucinated entity detected" in f for f in failures)

def test_adversarial_mid_sentence_boundary_fails_closed(mock_transcript):
    """Pillar 2 must reject bounds ending without terminal punctuation or speaker turn."""
    validator = DepoIndexValidator(mock_transcript)
    topic = "Review of Loan Disclosures and Legal Qualifications"
    evidence = "The witness confirms reviewing CFPB materials and PEAKS notes."
    
    is_valid, failures = validator.validate_all(
        topic, evidence,
        {"global_id": 0, "score": 95.0},
        {"global_id": 6, "score": 95.0}  # lands on non-terminal line
    )
    assert not is_valid
    assert any("Mid-sentence break detected" in f for f in failures)

def test_adversarial_unsupported_topic_fails_closed(mock_transcript):
    """Pillar 3 must reject topics with zero semantic grounding in cited coordinates."""
    validator = DepoIndexValidator(mock_transcript)
    topic = "Criminal Environmental Pollution and Maritime Violations"
    evidence = "The witness confirms reviewing CFPB materials and PEAKS notes."
    
    is_valid, failures = validator.validate_all(
        topic, evidence,
        {"global_id": 0, "score": 95.0},
        {"global_id": 5, "score": 95.0}
    )
    assert not is_valid
    assert any("lacks semantic grounding" in f for f in failures)

def test_stale_validation_fails_on_post_mutation_tampering(mock_transcript):
    """Mutating GID boundaries after initial check must fail the Revalidation Gate."""
    validator = DepoIndexValidator(mock_transcript)
    topic = "Review of Loan Disclosures and Legal Qualifications"
    evidence = "The witness confirms reviewing CFPB materials and PEAKS notes."
    
    # Passes initially on clean bounds [0, 5]
    ok, _ = validator.validate_all(topic, evidence, {"global_id": 0, "score": 95.0}, {"global_id": 5, "score": 95.0})
    assert ok
    
    # Tampered mutation to GID 6 (mid-sentence) must fail the Revalidation Gate
    reval_ok, reval_failures = validator.validate_all(topic, evidence, {"global_id": 0, "score": 95.0}, {"global_id": 6, "score": 95.0})
    assert not reval_ok
    assert any("Mid-sentence break detected" in f for f in reval_failures)