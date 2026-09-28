"""
Data contracts for legal transcript indexing, metadata capture, and audit logs.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DepositionMetadata(BaseModel):
    matter_name: str = Field(default="Unknown Matter")
    deponent_name: str = Field(default="Persis S. Yu")
    deponent_role: str = Field(default="Fact/Expert Witness")
    examining_attorney: str = Field(default="Mr. Purcell")
    defending_attorney: str = Field(default="Mr. Blood")
    deposition_date: str = Field(default="Unknown Date")
    start_page: int = Field(default=7)
    end_page: int = Field(default=88)

class TopicCandidate(BaseModel):
    topic: str
    start_quote: str
    end_quote: str
    evidence_summary: str

class TopicIndexEntry(BaseModel):
    topic: str
    start: str
    end: str
    start_gid: int
    end_gid: int
    supporting_evidence: str
    validation_status: str
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)

class CalibrationMetrics(BaseModel):
    parameter_name: str
    tested_range: List[float]
    optimal_value: float
    metric_name: str
    metric_score: float