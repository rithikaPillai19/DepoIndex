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
You are a senior litigation analyst. Identify ONLY high-level macro-examination topics from this taxonomy:
{json.dumps(CANONICAL_TAXONOMY, indent=2)}

STRICT OPERATING CONSTRAINTS:
1. ONLY extract topics that strictly match the Canonical Taxonomy above.
2. ZERO SUB-TOPICS: Combine sub-questions, follow-ups, and answers into one single parent topic.
3. DO NOT create topics for:
   - Court reporter interruptions or speed warnings.
   - Individual objections by counsel.
   - Brief digressions lasting fewer than 8 lines.
4. Extract exact, verbatim text for start_quote and end_quote.
5. Provide a detailed, factual evidence_summary.
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Deposition Transcript Segment:\n{chunk_text}"}
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