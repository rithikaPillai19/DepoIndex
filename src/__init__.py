"""
DepoIndex: Production Legal Transcript Indexing Package.
"""
from src.models import DepositionMetadata, TopicCandidate, TopicIndexEntry
from src.parser import parse_deposition_pdf, extract_deposition_metadata
from src.validator import DepoIndexValidator
from src.resolver import ProvenanceResolver

__version__ = "1.0.0"
__all__ = [
    "DepositionMetadata",
    "TopicCandidate",
    "TopicIndexEntry",
    "parse_deposition_pdf",
    "extract_deposition_metadata",
    "DepoIndexValidator",
    "ProvenanceResolver"
]