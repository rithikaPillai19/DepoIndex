import os
import json
import re
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field
from typing import List

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)

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
    topic: str = Field(..., description="The macro-topic name from the taxonomy.")
    start_quote: str = Field(..., description="Exact verbatim opening sentence.")
    end_quote: str = Field(..., description="Exact verbatim closing sentence.")
    evidence_summary: str = Field(..., description="Substantive factual synthesis.")

def _robust_json_extract(text: str) -> dict:
    if not text:
        return {"topics": []}
    text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```$", "", text.strip(), flags=re.MULTILINE).strip()
    
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return json.loads(text[first_brace:last_brace + 1])
    return json.loads(text)

def extract_macro_topics(chunk_text: str) -> List[MacroTopicSpan]:
    prompt = f"""You are a legal indexer. Inspect this transcript chunk and identify which of these topics are actively examined:
{json.dumps(CANONICAL_TAXONOMY, indent=2)}

Rules:
1. Return ONLY topics from the list that appear in the chunk.
2. If none appear, return: {{"topics": []}}
3. 'start_quote': Verbatim sentence where inquiry starts.
4. 'end_quote': Verbatim sentence where inquiry concludes.
5. Provide a concise evidence_summary.

Transcript:
{chunk_text}

Respond STRICTLY with raw valid JSON:
{{"topics": [{{"topic": "Name", "start_quote": "...", "end_quote": "...", "evidence_summary": "..."}}]}}"""

    try:
        completion = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1500
        )
        raw_content = completion.choices[0].message.content or ""
        payload = _robust_json_extract(raw_content)
        raw_topics = payload.get("topics", [])
        
        valid = []
        for t in raw_topics:
            if isinstance(t, dict) and t.get("topic") in CANONICAL_TAXONOMY:
                valid.append(MacroTopicSpan(**t))
        return valid

    except Exception as e:
        print(f"[Extraction Warning]: {e}")
        return []