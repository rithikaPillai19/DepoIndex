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

def sanitize_start_line(df: pd.DataFrame, gid: int) -> int:
    """Ensures the start coordinate lands on actual dialogue, not whitespace or noise."""
    max_idx = len(df) - 1
    current = min(gid, max_idx)
    while current < max_idx:
        text = str(df.iloc[current]["text"]).strip()
        if len(text) > 3 and text.replace("-", "").strip() != "":
            return current
        current += 1
    return current

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
    validator = DepoIndexValidator(df, min_score=65.0)

    # Step 4: Fine Line Resolution & 4-Pillar Validation
    print("\n--- Step 4: Fine Line Resolution & 4-Pillar Validation ---")
    final_topics = []

    admin_markers = [
        "ERRATA", "WORD INDEX", "CONCORDANCE", "TRANSCRIPT INDEX", 
        "RULES OF CIVIL PROCEDURE", "CERTIFICATE"
    ]

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

        # Prevent 413: Split wide spans into sub-windows of 130 lines max
        max_lines_per_call = 130
        step_size = 100
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
            time.sleep(0.4)

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
                    # Guard against coordinate inversion
                    if int(end_res["global_id"]) < int(start_res["global_id"]):
                        end_res = start_res.copy()

                    # Guarantee start does not anchor to a blank/redacted line
                    cleaned_s_gid = sanitize_start_line(df, int(start_res["global_id"]))
                    if cleaned_s_gid != int(start_res["global_id"]):
                        start_res["global_id"] = cleaned_s_gid
                        s_row = df.iloc[cleaned_s_gid]
                        start_res["page"] = int(s_row["page"])
                        start_res["line"] = int(s_row["line"])

                    # 4-Pillar Validation Check
                    failures = []
                    p1_ok, p1_msg = validator.validate_coordinates(start_res, end_res)
                    if not p1_ok: failures.append(f"Pillar 1: {p1_msg}")

                    p2_ok, p2_msg = validator.validate_boundary(int(start_res["global_id"]), int(end_res["global_id"]))
                    if not p2_ok: failures.append(f"Pillar 2: {p2_msg}")

                    p3_ok, p3_msg = validator.validate_semantic(span.topic)
                    if not p3_ok: failures.append(f"Pillar 3: {p3_msg}")

                    p4_ok, p4_msg = validator.validate_evidence(span.evidence_summary)
                    if not p4_ok: failures.append(f"Pillar 4: {p4_msg}")

                    if not failures:
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
                    else:
                        fallback = validator.execute_fallback(
                            {"topic": span.topic, "evidence": span.evidence_summary},
                            start_res, end_res, failures
                        )
                        final_topics.append(fallback)

    # Step 5: Chronological Deduplication & Contiguous Seam Snapping
    print("\n--- Step 5: Deduplicating and Eliminating Seam Gaps ---")
    final_topics.sort(key=lambda x: int(x.get("start_gid", 0)))

    cleaned_topics = []
    for entry in final_topics:
        if not cleaned_topics:
            cleaned_topics.append(entry)
            continue

        prev = cleaned_topics[-1]
        same_topic = (entry["topic"].strip().lower() == prev["topic"].strip().lower())

        if same_topic:
            # Merge identical topics bridging chunk seams
            if int(entry["start_gid"]) <= int(prev["end_gid"]) + 25:
                prev["end_gid"] = int(max(prev["end_gid"], entry["end_gid"]))
                e_row = df.iloc[prev["end_gid"]]
                prev["end"] = f"Page {int(e_row['page'])}, Line {int(e_row['line'])}"
                if entry["supporting_evidence"] not in prev["supporting_evidence"]:
                    prev["supporting_evidence"] += " " + entry["supporting_evidence"]
                continue

        # Prevent start coordinate collisions / inversions
        if int(entry["start_gid"]) <= int(prev["end_gid"]):
            entry["start_gid"] = int(prev["end_gid"]) + 1
            if int(entry["start_gid"]) >= len(df):
                continue
            s_row = df.iloc[int(entry["start_gid"])]
            entry["start"] = f"Page {int(s_row['page'])}, Line {int(s_row['line'])}"

        # Bridge orphaned colloquy gaps (1 to 5 lines) so referenced evidence is not lost
        gap = int(entry["start_gid"]) - int(prev["end_gid"]) - 1
        if 0 < gap <= 5:
            prev["end_gid"] = int(entry["start_gid"]) - 1
            e_row = df.iloc[prev["end_gid"]]
            prev["end"] = f"Page {int(e_row['page'])}, Line {int(e_row['line'])}"

        cleaned_topics.append(entry)

    # Snap the final topic boundary to the true conclusion of substantive examination
    if cleaned_topics and int(cleaned_topics[-1]["end_gid"]) < (len(df) - 1):
        last_topic = cleaned_topics[-1]
        last_topic["end_gid"] = int(len(df) - 1)
        last_row = df.iloc[-1]
        last_topic["end"] = f"Page {int(last_row['page'])}, Line {int(last_row['line'])}"

    # Step 6: Export Deliverables
    os.makedirs("output", exist_ok=True)
    with open("output/topic_index.json", "w", encoding="utf-8") as f:
        json.dump(cleaned_topics, f, indent=2)

    md_lines = [
        "# Deposition Topic Index\n",
        "| Topic | Start Coordinate | End Coordinate | Status | Supporting Evidence |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    for e in cleaned_topics:
        badge = "✅ PASSED" if e.get("validation_status") == "ALL_4_PILLARS_PASSED" else "⚠️ FALLBACK"
        clean_ev = str(e["supporting_evidence"]).replace("|", "-").replace("\n", " ")
        md_lines.append(f"| **{e['topic']}** | {e['start']} | {e['end']} | `{badge}` | {clean_ev} |")

    with open("output/topic_index.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"✓ Success: {len(cleaned_topics)} topics successfully indexed across entire document.\n")

if __name__ == "__main__":
    run_pipeline()