import json
import os
from rapidfuzz import fuzz
import pandas as pd
from src.segmenter import process_chunk, TopicSpan
from src.resolver import ProvenanceResolver

def run_single_pass(transcript_df, resolver, run_id):
    chunk_size = 80
    overlap = 15
    total_lines = len(transcript_df)
    current_idx = 0
    raw_topics = []

    print(f"--- Executing Run #{run_id} ---")

    while current_idx < total_lines:
        end_idx = min(current_idx + chunk_size, total_lines)
        chunk_slice = transcript_df.iloc[current_idx:end_idx]
        chunk_text = "\n".join([
            f"Page {row['page']} Line {row['line']}: {row['text']}"
            for _, row in chunk_slice.iterrows()
        ])
        
        detected_topics = process_chunk(chunk_text) or []

        for t in detected_topics:
            start_loc = resolver.find_line_for_quote(t.start_quote, search_start_id=current_idx, window=chunk_size + overlap)
            end_loc = resolver.find_line_for_quote(t.end_quote, search_start_id=start_loc["global_id"], window=chunk_size + overlap)
            
            if end_loc["global_id"] < start_loc["global_id"]:
                end_loc = start_loc
                
            raw_topics.append({
                "topic": t.topic_label,
                "start_page": start_loc["page"],
                "start_line": start_loc["line"],
                "end_page": end_loc["page"],
                "end_line": end_loc["line"],
                "start_global_id": start_loc["global_id"],
                "end_global_id": end_loc["global_id"],
                "evidence": t.evidence_summary
            })
            
        current_idx += (chunk_size - overlap)

    final_topics = []
    for topic in raw_topics:
        if not final_topics:
            final_topics.append(topic)
            continue
        prev = final_topics[-1]
        if (topic["topic"].strip().lower() == prev["topic"].strip().lower()) or (topic["start_global_id"] <= prev["end_global_id"]):
            prev["end_page"] = max(prev["end_page"], topic["end_page"])
            prev["end_line"] = topic["end_line"]
            prev["end_global_id"] = max(prev["end_global_id"], topic["end_global_id"])
            prev["evidence"] += " " + topic["evidence"]
        else:
            final_topics.append(topic)

    cleaned = [{
        "topic": t["topic"],
        "start": f"Page {t['start_page']}, Line {t['start_line']}",
        "end": f"Page {t['end_page']}, Line {t['end_line']}",
        "evidence": t["evidence"]
    } for t in final_topics]

    with open(f"output/run_{run_id}.json", "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)
    return cleaned

def main():
    with open("data/parsed_transcript.json", "r", encoding="utf-8") as f:
        df = pd.DataFrame(json.load(f))
    resolver = ProvenanceResolver(df)

    if os.path.exists("output/topic_index.json") and not os.path.exists("output/run_1.json"):
        with open("output/topic_index.json", "r", encoding="utf-8") as f:
            run1_data = json.load(f)
        with open("output/run_1.json", "w", encoding="utf-8") as f:
            json.dump(run1_data, f, indent=2)

    print("Executing stability comparison runs...")
    # Load run 1
    with open("output/run_1.json", "r", encoding="utf-8") as f:
        r1 = json.load(f)

    print(f"Run 1 Topic Count: {len(r1)}")

if __name__ == "__main__":
    main()