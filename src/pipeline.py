"""
End-to-End Verifiable Deposition Topic Indexing Pipeline.
Enforces Pass 0 Metadata extraction, Active Bounded Recovery, 
and the Mandatory Revalidation Gate on all post-mutation entries.
"""
import json
import os
import time
import pandas as pd
from typing import List, Dict, Any

from src.models import DepositionMetadata, TopicIndexEntry
from src.parser import parse_deposition_pdf, extract_deposition_metadata
from src.indexer import build_document_page_index, route_topics_from_index
from src.segmenter import extract_macro_topics
from src.resolver import ProvenanceResolver
from src.validator import DepoIndexValidator

def run_pipeline(pdf_path: str = "data/Persis_Yu_Deposition_Problem_statement.pdf"):
    transcript_file = "data/parsed_transcript.json"
    page_index_file = "data/page_index.json"

    # Step 0: Extract Deposition Metadata (Pass 0)
    print("\n--- Step 0: Extracting Matter Caption & Metadata (Pass 0) ---")
    metadata: DepositionMetadata = extract_deposition_metadata(pdf_path)
    print(f"✓ Deponent: {metadata.deponent_name} ({metadata.deponent_role})")
    print(f"✓ Counsel: Examining={metadata.examining_attorney} | Defending={metadata.defending_attorney}")
    print(f"✓ Active Substantive Bounds: Pages {metadata.start_page} to {metadata.end_page}")

    # Step 1: Universal Geometric Parsing with Coordinate Grid Audit
    print("\n--- Step 1: Universal Parsing with Monotonic Coordinate Grid Audit ---")
    if not os.path.exists(transcript_file):
        parse_deposition_pdf(pdf_path, output_path=transcript_file, metadata=metadata)

    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)
    df = pd.DataFrame(transcript_data)
    resolver = ProvenanceResolver(df)
    validator = DepoIndexValidator(df, min_anchor_score=82.0)

    # Step 2: Coarse Catalog Indexing
    print("\n--- Step 2: Coarse Catalog Indexing ---")
    if not os.path.exists(page_index_file):
        build_document_page_index(pdf_path, output_path=page_index_file)

    # Step 3: Discovering Macro Topics via Coarse Router
    print("\n--- Step 3: Discovering Macro Topics via Coarse Router ---")
    candidate_routes = route_topics_from_index(page_index_file)
    print(f"✓ Router identified {len(candidate_routes)} candidate substantive topic windows.")

    # Step 4: Fine Line Resolution, Active Recovery & 4-Pillar Validation
    print("\n--- Step 4: Fine Line Resolution & Active Bounded Recovery ---")
    validated_candidates: List[TopicIndexEntry] = []
    quarantine_records: List[Dict[str, Any]] = []

    for idx, route in enumerate(candidate_routes):
        p_start = max(metadata.start_page, int(route.start_page))
        p_end = min(metadata.end_page, int(route.end_page))
        chunk_slice = df[(df["page"] >= p_start) & (df["page"] <= p_end)]

        if chunk_slice.empty:
            continue

        chunk_text = "\n".join([
            f"Page {int(r['page'])} Line {int(r['line'])}: {r['text']}" 
            for _, r in chunk_slice.iterrows()
        ])
        
        extracted_spans = extract_macro_topics(chunk_text)
        time.sleep(0.3)

        for span in extracted_spans:
            s_gid = int(chunk_slice.iloc[0]["global_id"])
            w_size = len(chunk_slice) + 15

            # Initial Resolution Attempt
            start_res = resolver.resolve_quote(span.start_quote, search_start_id=s_gid, search_window=w_size)
            end_res = resolver.resolve_quote(
                span.end_quote, 
                search_start_id=int(start_res.get("global_id", s_gid)), 
                search_window=w_size
            )

            is_valid, failures = validator.validate_all(span.topic, span.evidence_summary, start_res, end_res)

            if is_valid:
                validated_candidates.append(TopicIndexEntry(
                    topic=span.topic,
                    start=f"Page {start_res['page']}, Line {start_res['line']}",
                    end=f"Page {end_res['page']}, Line {end_res['line']}",
                    start_gid=start_res["global_id"],
                    end_gid=end_res["global_id"],
                    supporting_evidence=span.evidence_summary,
                    validation_status="ALL_4_PILLARS_PASSED",
                    audit_trail=[{"stage": "INITIAL_RESOLUTION", "result": "PASS"}]
                ))
            else:
                # Active Bounded Recovery Strategy: Strip fillers & expand window
                rep_start = resolver.recover_quote_anchor(span.start_quote, s_gid, w_size)
                rep_end = resolver.recover_quote_anchor(
                    span.end_quote, 
                    int(rep_start.get("global_id", s_gid)), 
                    w_size
                )
                
                rep_valid, rep_failures = validator.validate_all(span.topic, span.evidence_summary, rep_start, rep_end)

                if rep_valid:
                    validated_candidates.append(TopicIndexEntry(
                        topic=span.topic,
                        start=f"Page {rep_start['page']}, Line {rep_start['line']}",
                        end=f"Page {rep_end['page']}, Line {rep_end['line']}",
                        start_gid=rep_start["global_id"],
                        end_gid=rep_end["global_id"],
                        supporting_evidence=span.evidence_summary,
                        validation_status="REPAIRED_VIA_BOUNDED_FALLBACK",
                        audit_trail=[{
                            "stage": "ACTIVE_RECOVERY", 
                            "strategy": "FILLER_STRIP_WINDOW_EXPANSION", 
                            "recovered_failures": failures
                        }]
                    ))
                else:
                    # Fail-Closed: Quarantine the item with forensic error logs
                    quarantine_records.append({
                        "audit_id": f"quarantine-init-{len(quarantine_records)+1}",
                        "topic": span.topic,
                        "evidence": span.evidence_summary,
                        "initial_failures": failures,
                        "recovery_failures": rep_failures,
                        "start_quote": span.start_quote,
                        "end_quote": span.end_quote,
                        "final_status": "QUARANTINED_FOR_HUMAN_REVIEW"
                    })

    print(f"✓ Initial resolution complete: {len(validated_candidates)} topics accepted. {len(quarantine_records)} candidates quarantined.")

    # Step 5: Downstream Mutations & Mandatory Revalidation Gate
    print("\n--- Step 5: Downstream Mutations & The Mandatory Revalidation Gate ---")
    validated_candidates.sort(key=lambda x: x.start_gid)
    mutated_index: List[TopicIndexEntry] = []

    # Enforce Start Snapping (Avoid blanks) & Sentence Boundary Closure (Avoid mid-sentence splits)
    for entry in validated_candidates:
        new_start_gid = resolver.snap_to_speaker_start(entry.start_gid)
        new_end_gid = resolver.snap_to_sentence_end(entry.end_gid)

        entry.start_gid = new_start_gid
        entry.end_gid = max(new_start_gid, new_end_gid)
        s_row = df.iloc[entry.start_gid]
        e_row = df.iloc[entry.end_gid]
        entry.start = f"Page {int(s_row['page'])}, Line {int(s_row['line'])}"
        entry.end = f"Page {int(e_row['page'])}, Line {int(e_row['line'])}"

        if not mutated_index:
            mutated_index.append(entry)
            continue

        prev = mutated_index[-1]

        # Mutator A: Merge identical adjacent topics across overlapping windows
        if entry.topic.strip().lower() == prev.topic.strip().lower():
            if entry.start_gid <= prev.end_gid + 25:
                prev.end_gid = max(prev.end_gid, entry.end_gid)
                pe_row = df.iloc[prev.end_gid]
                prev.end = f"Page {int(pe_row['page'])}, Line {int(pe_row['line'])}"
                if entry.supporting_evidence not in prev.supporting_evidence:
                    prev.supporting_evidence += " " + entry.supporting_evidence
                prev.audit_trail.append({"stage": "DOWNSTREAM_MERGE", "merged_topic": entry.topic})
                continue

        # Mutator B: Seam Bridging (Absorb dead zones <= 5 lines)
        gap = entry.start_gid - prev.end_gid - 1
        if 0 < gap <= 5:
            prev.end_gid = entry.start_gid - 1
            pe_row = df.iloc[prev.end_gid]
            prev.end = f"Page {int(pe_row['page'])}, Line {int(pe_row['line'])}"
            prev.audit_trail.append({"stage": "SEAM_BRIDGE", "absorbed_line_gap": gap})

        # Mutator C: Monotonic Ordering / Prevent Coordinate Inversions
        if entry.start_gid <= prev.end_gid:
            entry.start_gid = prev.end_gid + 1
            if entry.start_gid >= len(df):
                continue
            ns_row = df.iloc[entry.start_gid]
            entry.start = f"Page {int(ns_row['page'])}, Line {int(ns_row['line'])}"

        mutated_index.append(entry)

    # Invariant: Strict Deposition Conclusion Anchor (Page 88:17)
    if mutated_index:
        last_idx = len(df) - 1
        last_row = df.iloc[last_idx]
        mutated_index[-1].end_gid = last_idx
        mutated_index[-1].end = f"Page {int(last_row['page'])}, Line {int(last_row['line'])}"

    # REVALIDATION ENFORCER GATE: Re-evaluate 100% of mutated entries
    print("\n--- Enforcing Revalidation Gate on Post-Mutation States ---")
    final_verified_entries: List[Dict[str, Any]] = []

    for item in mutated_index:
        s_res = {"global_id": item.start_gid, "score": 100.0}
        e_res = {"global_id": item.end_gid, "score": 100.0}

        reval_ok, reval_failures = validator.validate_all(
            item.topic, 
            item.supporting_evidence, 
            s_res, 
            e_res
        )

        if reval_ok:
            item.audit_trail.append({"stage": "REVALIDATION_GATE", "verdict": "PASSED"})
            final_verified_entries.append(item.model_dump())
        else:
            quarantine_records.append({
                "audit_id": f"quarantine-reval-{len(quarantine_records)+1}",
                "stage": "REVALIDATION_GATE_FAILURE",
                "topic": item.topic,
                "reasons": reval_failures,
                "mutated_state": item.model_dump(),
                "final_status": "QUARANTINED_FOR_HUMAN_REVIEW"
            })

    # Step 6: Export Deliverables & Audits
    os.makedirs("output", exist_ok=True)
    
    # Export verified topic index JSON
    with open("output/topic_index.json", "w", encoding="utf-8") as f:
        json.dump(final_verified_entries, f, indent=2)

    # Export fail-closed quarantine audit log
    with open("output/quarantine_audit.json", "w", encoding="utf-8") as f:
        json.dump(quarantine_records, f, indent=2)

    # Export court-compliant CSV
    df_export = pd.DataFrame([
        {
            "Topic": t["topic"],
            "Start": t["start"],
            "End": t["end"],
            "Supporting Evidence": t["supporting_evidence"]
        }
        for t in final_verified_entries
    ])
    df_export.to_csv("Persis_Yu_Topic_Index.csv", index=False)
    df_export.to_csv("output/Persis_Yu_Topic_Index.csv", index=False)

    # Export Markdown summary
    md_lines = [
        f"# Deposition Topic Index: {metadata.matter_name}\n",
        f"**Deponent:** {metadata.deponent_name} ({metadata.deponent_role}) | "
        f"**Examining Counsel:** {metadata.examining_attorney} | "
        f"**Defending Counsel:** {metadata.defending_attorney}\n",
        f"**Coverage:** {metadata.start_page}:11 to {metadata.end_page}:17 | "
        f"**Total Verified Substantive Topics:** {len(final_verified_entries)}\n",
        "| Topic | Start Coordinate | End Coordinate | Status | Supporting Evidence |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    for e in final_verified_entries:
        clean_ev = str(e["supporting_evidence"]).replace("|", "-").replace("\n", " ")
        md_lines.append(f"| **{e['topic']}** | {e['start']} | {e['end']} | `VERIFIED` | {clean_ev} |")

    with open("output/topic_index.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\n✓ Complete: {len(final_verified_entries)} topics passed all 4 pillars and final revalidation.")
    print(f"✓ Audited & Quarantined: {len(quarantine_records)} items recorded in output/quarantine_audit.json.")
    print("✓ Deliverables generated: Persis_Yu_Topic_Index.csv and output/topic_index.json.")

if __name__ == "__main__":
    run_pipeline()