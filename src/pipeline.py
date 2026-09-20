import json
import os
import pandas as pd
from src.parser import parse_deposition_pdf
from src.segmenter import extract_macro_topics, CANONICAL_TAXONOMY
from src.resolver import ProvenanceResolver
from src.validator import DepoIndexValidator

def run_pipeline():
    transcript_file = "data/parsed_transcript.json"
    if not os.path.exists(transcript_file):
        parse_deposition_pdf("data/Persis_Yu_Deposition_Problem_statement.pdf")

    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    df = pd.DataFrame(transcript_data)
    resolver = ProvenanceResolver(df)
    validator = DepoIndexValidator(df, CANONICAL_TAXONOMY, min_score=70.0)

    chunk_size = 180
    overlap = 30
    total_lines = len(df)
    current_idx = 0
    validated_index = []

    print(f"--- Running 4-Pillar Validated DepoIndex on {total_lines} Lines ---")

    while current_idx < total_lines:
        end_idx = min(current_idx + chunk_size, total_lines)
        chunk_slice = df.iloc[current_idx:end_idx]
        chunk_text = "\n".join([
            f"Page {r['page']} Line {r['line']}: {r['text']}"
            for _, r in chunk_slice.iterrows()
        ])

        candidates = extract_macro_topics(chunk_text)

        for item in candidates:
            # 1. Resolve Coordinates
            start_res = resolver.resolve_quote(item.start_quote, search_start_id=current_idx, search_window=chunk_size + overlap)
            search_start_for_end = (start_res["global_id"] + 1) if start_res.get("global_id") is not None else current_idx
            end_res = resolver.resolve_quote(item.end_quote, search_start_id=search_start_for_end, search_window=chunk_size + overlap)
            # 2. Run the 4 Validation Pillars
            failures = []
            
            p1_ok, p1_msg = validator.validate_coordinates(start_res, end_res)
            if not p1_ok: failures.append(f"Pillar 1 (Coordinate): {p1_msg}")

            p2_ok, p2_msg = validator.validate_boundary(start_res.get("global_id", 0), end_res.get("global_id", 0))
            if not p2_ok: failures.append(f"Pillar 2 (Boundary): {p2_msg}")

            p3_ok, p3_msg = validator.validate_semantic(item.topic)
            if not p3_ok: failures.append(f"Pillar 3 (Semantic): {p3_msg}")

            p4_ok, p4_msg = validator.validate_evidence(item.evidence_summary)
            if not p4_ok: failures.append(f"Pillar 4 (Evidence): {p4_msg}")

            # 3. Handle Passed vs Failed Entries
            if not failures:
                validated_index.append({
                    "topic": item.topic,
                    "start": f"Page {start_res['page']}, Line {start_res['line']}",
                    "end": f"Page {end_res['page']}, Line {end_res['line']}",
                    "start_gid": start_res["global_id"],
                    "end_gid": end_res["global_id"],
                    "supporting_evidence": item.evidence_summary,
                    "validation_status": "ALL_4_PILLARS_PASSED",
                    "validation_scores": {
                        "start_score": start_res["score"],
                        "end_score": end_res["score"]
                    },
                    "anchors": {
                        "start_quote": item.start_quote,
                        "end_quote": item.end_quote
                    }
                })
            else:
                # 4. Pillar 5: Trigger Fallback Mechanism
                fallback_entry = validator.execute_fallback(
                    {"topic": item.topic, "evidence": item.evidence_summary},
                    start_res, end_res, failures
                )
                print(f"  [Fallback Triggered]: {item.topic} -> {failures}")
                validated_index.append(fallback_entry)

        current_idx += (chunk_size - overlap)

    # Monotonic Ordering & Adjacent Merging
    validated_index.sort(key=lambda x: x.get("start_gid", 0))

    final_cleaned = []
    for entry in validated_index:
        if not final_cleaned:
            final_cleaned.append(entry)
            continue
        prev = final_cleaned[-1]
        
        # Merge consecutive identical topics
        if (entry["topic"].strip().lower() == prev["topic"].strip().lower()) or \
           (entry.get("start_gid", 0) <= prev.get("end_gid", -1)):
            prev["end"] = entry["end"]
            prev["end_gid"] = max(prev.get("end_gid", 0), entry.get("end_gid", 0))
            if entry["supporting_evidence"] not in prev["supporting_evidence"]:
                prev["supporting_evidence"] += " " + entry["supporting_evidence"]
        else:
            final_cleaned.append(entry)

    # Save to disk
    os.makedirs("output", exist_ok=True)
    with open("output/topic_index.json", "w", encoding="utf-8") as f:
        json.dump(final_cleaned, f, indent=2)

    # Generate Markdown Table
    md_lines = [
        "# Deposition Topic Index: Persis S. Yu\n",
        "| Topic | Start Coordinate | End Coordinate | Validation Status | Supporting Testimony Evidence |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    for e in final_cleaned:
        status_badge = "✅ PASSED" if e.get("validation_status") == "ALL_4_PILLARS_PASSED" else "⚠️ FALLBACK"
        clean_ev = e["supporting_evidence"].replace("|", "-").replace("\n", " ")
        md_lines.append(f"| **{e['topic']}** | {e['start']} | {e['end']} | `{status_badge}` | {clean_ev} |")

    with open("output/topic_index.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\n✓ Completed: {len(final_cleaned)} topics processed through 4-Pillar Validation + Fallback.")

if __name__ == "__main__":
    run_pipeline()