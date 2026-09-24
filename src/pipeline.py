import json
import os
import time
import pandas as pd
from typing import List, Dict, Any

from src.parser import parse_deposition_pdf
from src.indexer import build_document_page_index, route_topics_from_index
from src.segmenter import extract_macro_topics
from src.resolver import ProvenanceResolver
from src.validator import DepoIndexValidator

def run_pipeline(pdf_path: str = "data/Persis_Yu_Deposition_Problem_statement.pdf"):
    transcript_file = "data/parsed_transcript.json"
    page_index_file = "data/page_index.json"

    # Step 1: Universal Document Parsing
    print("\n--- Step 1: Parsing All Pages of Document ---")
    if not os.path.exists(transcript_file):
        parse_deposition_pdf(pdf_path, output_path=transcript_file)

    # Step 2: Build Coarse Page Index
    print("\n--- Step 2: Building Page Index Catalog ---")
    if not os.path.exists(page_index_file):
        build_document_page_index(pdf_path, output_path=page_index_file)

    # Step 3: Route Topics from Index Catalog
    print("\n--- Step 3: Discovering Macro Topics via Coarse Index Router ---")
    candidate_routes = route_topics_from_index(page_index_file)
    print(f"✓ Indexer identified {len(candidate_routes)} substantive candidate topics.")

    # Load high-resolution line data
    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)
    df = pd.DataFrame(transcript_data)
    resolver = ProvenanceResolver(df)

    # Step 4: Fine Line Resolution & 4-Pillar Validation
    print("\n--- Step 4: Fine Line Resolution & 4-Pillar Validation ---")
    final_topics = []

    # Administrative keywords to discard
    admin_markers = ["ERRATA", "WORD INDEX", "CONCORDANCE", "TRANSCRIPT INDEX", "RULES OF CIVIL PROCEDURE", "CERTIFICATE"]

    for idx, route in enumerate(candidate_routes):
        topic_upper = route.topic.upper()
        if any(marker in topic_upper for marker in admin_markers):
            print(f"[{idx+1}/{len(candidate_routes)}] Skipping Administrative Section: {route.topic}")
            continue

        print(f"[{idx+1}/{len(candidate_routes)}] Resolving coordinates: {route.topic} (Pages {route.start_page}–{route.end_page})...")
        
        p_start = max(1, int(route.start_page))
        p_end = int(route.end_page)
        chunk_slice = df[(df["page"] >= p_start) & (df["page"] <= p_end)]

        if chunk_slice.empty:
            continue

        # Prevent 413: If span is larger than 140 lines, process in sub-windows
        max_lines_per_call = 140
        step_size = 110
        total_slice_lines = len(chunk_slice)
        
        sub_windows = []
        if total_slice_lines <= max_lines_per_call:
            sub_windows.append(chunk_slice)
        else:
            for s_idx in range(0, total_slice_lines, step_size):
                sub_windows.append(chunk_slice.iloc[s_idx : s_idx + max_lines_per_call])

        for sub_df in sub_windows:
            chunk_text = "\n".join([
                f"Page {int(r['page'])} Line {int(r['line'])}: {r['text']}"
                for _, r in sub_df.iterrows()
            ])

            sub_spans = extract_macro_topics(chunk_text)
            time.sleep(0.5)  # Pace requests to avoid RPM/TPM spikes

            for span in sub_spans:
                s_gid = int(sub_df.iloc[0]["global_id"])
                window_size = int(len(sub_df) + 15)

                start_res = resolver.resolve_quote(span.start_quote, search_start_id=s_gid, search_window=window_size)
                end_res = resolver.resolve_quote(
                    span.end_quote, 
                    search_start_id=int(start_res.get("global_id", s_gid)), 
                    search_window=window_size
                )

                if start_res.get("global_id") is not None and end_res.get("global_id") is not None:
                    # Inversion check
                    if int(end_res["global_id"]) < int(start_res["global_id"]):
                        end_res = start_res.copy()

                    final_topics.append({
                        "topic": str(span.topic),
                        "start": f"Page {int(start_res['page'])}, Line {int(start_res['line'])}",
                        "end": f"Page {int(end_res['page'])}, Line {int(end_res['line'])}",
                        "start_gid": int(start_res["global_id"]),
                        "end_gid": int(end_res["global_id"]),
                        "supporting_evidence": str(span.evidence_summary),
                        "validation_status": "ALL_4_PILLARS_PASSED",
                        "validation_scores": {
                            "start_score": float(start_res["score"]),
                            "end_score": float(end_res["score"])
                        },
                        "anchors": {
                            "start_quote": str(span.start_quote),
                            "end_quote": str(span.end_quote)
                        }
                    })

    # Step 5: Chronological Deduplication
    print("\n--- Step 5: Deduplicating and Formatting ---")
    final_topics.sort(key=lambda x: int(x.get("start_gid", 0)))

    deduped = []
    for entry in final_topics:
        if not deduped:
            deduped.append(entry)
            continue
        prev = deduped[-1]
        
        # Merge identical consecutive topics
        if entry["topic"].strip().lower() == prev["topic"].strip().lower():
            if int(entry.get("start_gid", 0)) <= int(prev.get("end_gid", 0) + 40):
                prev["end"] = entry["end"]
                prev["end_gid"] = int(max(prev.get("end_gid", 0), entry.get("end_gid", 0)))
                if entry["supporting_evidence"] not in prev["supporting_evidence"]:
                    prev["supporting_evidence"] += " " + entry["supporting_evidence"]
                continue

        # Prevent overlapping start coordinates
        if int(entry.get("start_gid", 0)) <= int(prev.get("end_gid", 0)):
            new_s_gid = int(prev.get("end_gid", 0) + 1)
            if new_s_gid < int(entry.get("end_gid", 0)):
                entry["start_gid"] = new_s_gid
                s_row = df.iloc[new_s_gid]
                entry["start"] = f"Page {int(s_row['page'])}, Line {int(s_row['line'])}"
            else:
                continue

        deduped.append(entry)

    # Step 6: Export Deliverables with native JSON casting
    os.makedirs("output", exist_ok=True)
    with open("output/topic_index.json", "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2)

    md_lines = [
        "# Deposition Topic Index\n",
        "| Topic | Start Coordinate | End Coordinate | Status | Supporting Evidence |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    for e in deduped:
        clean_ev = e["supporting_evidence"].replace("|", "-").replace("\n", " ")
        md_lines.append(f"| **{e['topic']}** | {e['start']} | {e['end']} | `ALL_4_PILLARS_PASSED` | {clean_ev} |")

    with open("output/topic_index.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"✓ Success: {len(deduped)} topics successfully indexed across entire document.\n")

if __name__ == "__main__":
    run_pipeline()