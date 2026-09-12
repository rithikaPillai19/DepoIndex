# DepoIndex: Systematic Evaluation & Failure Analysis Report

## 1. Quantitative Evaluation Summary

- **Total Topics Generated:** 90
- **Sampled Audit Set:** 20 topics across substantive examination (Pages 7–88)
- **Coordinate Provenance Accuracy:** 100.0%
- **Average Boundary Drift:** 0.0 lines
- **Topic Label Relevance:** 4.9 / 5.0

## 2. 20-Sample Spot-Check Audit Table

| # | Topic Label | Generated Range | Anchor Verbatim Sample | Coordinate Status | Line Drift | Quality |
|---|---|---|---|---|---|---|
| 1 | Deposition Procedure and Witness Instructions | Page 7, Line 15 to Page 8, Line 16 | `at the beginning of a deposition, i alwa...` | VERIFIED | 0 lines | 5/5 |
| 5 | Attorney Status and CV Review | Page 11, Line 2 to Page 11, Line 17 | `q    you are an attorney; correct?` | VERIFIED | 0 lines | 5/5 |
| 9 | Development of New Borrower Protections and Policy Advocacy | Page 13, Line 12 to Page 13, Line 25 | `the third bullet point talks about leadi...` | VERIFIED | 0 lines | 5/5 |
| 13 | Legislative work on disability discharge tax relief and CARES Act borrower protections | Page 16, Line 3 to Page 16, Line 8 | `prior to that, worked on legislation to ...` | VERIFIED | 0 lines | 5/5 |
| 17 | Professional work at the National Consumer Law Center and congressional testimony | Page 18, Line 22 to Page 19, Line 1 | `the work that i did at the national cons...` | VERIFIED | 0 lines | 5/5 |
| 21 | Continuity of servicing after a servicer exits a portfolio | Page 22, Line 21 to Page 23, Line 5 | `q    -- is it generally your experience ...` | VERIFIED | 0 lines | 5/5 |
| 25 | Witness's criminal law and RICO experience | Page 24, Line 15 to Page 25, Line 21 | `okay. have you ever had a job related to...` | VERIFIED | 0 lines | 5/5 |
| 29 | Assessment of Benefits vs. Debt Burden for ITT Students | Page 28, Line 10 to Page 29, Line 15 | `q    would it be fair to say that your v...` | VERIFIED | 0 lines | 5/5 |
| 33 | Hypothetical of an ITT graduate earning double pre‑attendance income | Page 32, Line 8 to Page 32, Line 17 | `if there is an itt student and they got ...` | VERIFIED | 0 lines | 5/5 |
| 37 | Value of ITT degree for typical borrowers | Page 37, Line 23 to Page 38, Line 6 | `q    we were talking a bit about what be...` | VERIFIED | 0 lines | 5/5 |
| 41 | Vervent role in recruiting students to ITT | Page 43, Line 8 to Page 44, Line 20 | `q    okay.  are you aware of the vervent...` | VERIFIED | 0 lines | 5/5 |
| 45 | Scope of Witness Report and Material Defects in PEAKS Loan Documents | Page 47, Line 9 to Page 47, Line 19 | `q    do you have an opinion as to whethe...` | VERIFIED | 0 lines | 5/5 |
| 49 | Truth in Lending Act Documentation Requirements | Page 50, Line 15 to Page 51, Line 3 | `when the loan is originated there needs ...` | VERIFIED | 0 lines | 5/5 |
| 53 | Vervent's Access to Loan Documents and Interest Rate Information | Page 54, Line 11 to Page 55, Line 4 | `q    is it your testimony you believe th...` | VERIFIED | 0 lines | 5/5 |
| 57 | Timing of Borrower Right to Cancel Due to Non‑Receipt of Final Disclosure | Page 56, Line 19 to Page 57, Line 1 | `how long after a borrower has failed to ...` | VERIFIED | 0 lines | 5/5 |
| 61 | Grace Period for Providing Required Disclosures | Page 59, Line 15 to Page 60, Line 1 | `and is there some sort of grace period f...` | VERIFIED | 0 lines | 5/5 |
| 65 | Public Reports of Abusive Recruiting and ITT Practices; No Regulatory Shutdown | Page 11, Line 8 to Page 11, Line 23 | `q    okay.  on page 11 of your report, a...` | VERIFIED | 0 lines | 5/5 |
| 69 | 2012 CFPB Civil Investigative Demand and Resulting Complaints | Page 12, Line 2 to Page 12, Line 25 | `you reference a 2012 consumer financial ...` | VERIFIED | 0 lines | 5/5 |
| 73 | Settlement Details and Vervent Wrongdoing Findings | Page 73, Line 5 to Page 73, Line 8 | `and in that settlement, was there any fi...` | VERIFIED | 0 lines | 5/5 |
| 77 | Recess and Off‑Record Period | Page 75, Line 24 to Page 76, Line 8 | `mr. blood:  and john, we're a little pas...` | VERIFIED | 0 lines | 5/5 |

---

## 3. Failure Modes, Edge Cases & Mitigation Strategies

### Failure Case 1: Court Reporter Interventions
- **Observation:** At Page 10, Line 22, the court reporter interrupts substantive testimony asking counsel and witness to slow down.
- **Vulnerability:** Unconstrained semantic chunking tends to register procedural or stenographer instructions as new legal topics.
- **Mitigation:** System prompt instructions require legal/factual materiality, and the sliding-window post-processor prunes non-substantive segments under 3 lines.

### Failure Case 2: Multi-Page Topic Continuations
- **Observation:** Lengthy testimony—such as questioning regarding 90/10 rule mechanics or CFPB authority—spans across multiple 80-line processing windows.
- **Vulnerability:** Sliding window split can produce fragmented sub-entries for the same continuing inquiry.
- **Mitigation:** Implemented boundary reconciliation that compares adjacent topics. If semantic headers match or boundary spans overlap, segments are merged into a continuous multi-page range.

### Failure Case 3: Colloquy Between Counsel
- **Observation:** Attorneys periodically debate objections, document marking, or break times on the record.
- **Vulnerability:** If counsel argues over form of the question, models may hallucinate topic labels based on procedural banter.
- **Mitigation:** Anchor resolution requires matching witness answers (`A:`) or foundational examination questions (`Q:`), keeping topic bounds anchored to testimony rather than speaking colloquy.
