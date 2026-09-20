import os
import json
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field
from typing import List

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CANONICAL_TAXONOMY = [
    "Deposition Protocol, Ground Rules & Perjury Warning",
    "Expert Witness Retention & Scope of Assignment",
    "Marking Expert Report as Exhibit 1",
    "Witness Educational and Professional Background at SBPC",
    "Department of Education Negotiated Rulemaking",
    "Public Comments on Loan Servicer Solicitation RFIs",
    "Personal Work Experience as Loan Servicer",
    "Analysis Scope and Review of PEAKS Loan Documents",
    "Proprietary School 90/10 Rule and Compliance",
    "Cohort Default Rate Standards and Incentives",
    "Underwriting Standards and Failure Modes",
    "Role of Vervent in Private Student Lending",
    "Servicing vs. Origination Legal Distinction",
    "Borrower Complaints and Servicing Transfer Risks",
    "Statutory and Regulatory Data Transfer Requirements",
    "Criminal Law Background and RICO Familiarity",
    "ITT For-Profit Educational Quality and Degree Value",
    "Outlier Graduate Earnings Hypotheticals",
    "Vervent Knowledge of ITT Misrepresentations",
    "Enforceability and Material Defects in PEAKS Loan Documents",
    "Truth in Lending Act (TILA) Required Disclosures",
    "California Student Loan Servicing Law Compliance Scope",
    "Consumer Financial Protection Bureau (CFPB) Settlement and Findings",
    "SEC Inquiries and Investigations into ITT and PEAKS",
    "Department of Education Enforcement Actions and Closure of ITT",
    "Fiduciary Duty and Standard of Care in Loan Servicing",
    "Conclusion of Substantive Examination"
]

class MacroTopicSpan(BaseModel):
    topic: str = Field(..., description="The macro-topic name selected from the Canonical Taxonomy.")
    start_quote: str = Field(..., description="Exact opening sentence of the examination.")
    end_quote: str = Field(..., description="Exact concluding sentence of the examination.")
    evidence_summary: str = Field(..., description="Substantive 1-3 sentence factual synthesis of testimony.")

def extract_macro_topics(chunk_text: str) -> List[MacroTopicSpan]:
    system_prompt = f"""
You are a senior litigation analyst. Identify ONLY broad, overarching macro-examination topics from this canonical list:
{json.dumps(CANONICAL_TAXONOMY, indent=2)}

CRITICAL BOUNDARY INSTRUCTIONS:
1. SPAN THE ENTIRE DISCUSSION: A macro topic represents an entire section of examination, usually spanning 15 to 60+ lines.
2. 'start_quote' must be the FIRST question where the attorney introduces the subject.
3. 'end_quote' must be the FINAL answer where the witness finishes testifying on this subject before a new topic begins.
4. DO NOT quote the same sentence or adjacent lines for start and end. If a topic is discussed across multiple pages, capture the full range.
5. Combine all follow-up questions, objections, and answers into one continuous parent span.

OUTPUT FORMAT:
Respond exclusively with a valid json object matching this schema:
{{
  "topics": [
    {{
      "topic": "<Exact topic title from taxonomy>",
      "start_quote": "<Exact verbatim opening question>",
      "end_quote": "<Exact verbatim final concluding answer>",
      "evidence_summary": "<Factual 1-3 sentence summary of testimony>"
    }}
  ]
}}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Return a json object analyzing this deposition segment:\n{chunk_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        payload = json.loads(completion.choices[0].message.content)
        raw_topics = payload.get("topics", payload if isinstance(payload, list) else [])
        return [MacroTopicSpan(**t) for t in raw_topics if t.get("topic") in CANONICAL_TAXONOMY]
    except Exception as e:
        print(f"[Extraction Warning]: {e}")
        return []