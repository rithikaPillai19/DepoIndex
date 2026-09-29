"""
Data contracts for legal transcript indexing, metadata capture, and audit logs.
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class DepositionMetadata(BaseModel):
    matter_name: str = Field(default="Heather Turrey vs. Vervent, Inc.")
    deponent_name: str = Field(default="Persis S. Yu")
    deponent_role: str = Field(default="Fact / Expert Witness")
    examining_attorney: str = Field(default="Mr. Purcell")
    defending_attorney: str = Field(default="Mr. Blood")
    start_page: int = Field(default=7)
    end_page: int = Field(default=88)

class TopicCandidate(BaseModel):
    topic: str = Field(..., description="Substantive legal or factual examination topic in Title Case.")
    start_quote: str = Field(..., description="Exact verbatim opening sentence from the text.")
    end_quote: str = Field(..., description="Exact verbatim closing sentence from the text.")
    evidence_summary: str = Field(..., description="Substantive 1-2 sentence factual synthesis.")

class TopicIndexEntry(BaseModel):
    topic: str
    start: str
    end: str
    start_gid: int
    end_gid: int
    supporting_evidence: str
    validation_status: str
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)