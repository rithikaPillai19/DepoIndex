import json
import os
import pandas as pd
from src.segmenter import process_chunk, TopicSpan
from src.resolver import ProvenanceResolver

def run_pipeline(transcript_path="data/parsed_transcript.json", output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    cache_path = os.path.join(output_dir, "chunks_cache.json")
    
    with open(transcript_path, "r") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    resolver = ProvenanceResolver(df)
    
    chunk_size = 80
    overlap = 15
    total_lines = len(df)
    
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)
            print(f"Loaded {len(cache)} cached chunk results from {cache_path}")
        except Exception:
            cache = {}

    current_idx = 0
    raw_topics = []

    print(f"Starting pipeline on {total_lines} transcript lines...")

    while current_idx < total_lines:
        end_idx = min(current_idx + chunk_size, total_lines)
        chunk_key = f"{current_idx}_{end_idx}"

        if chunk_key in cache:
            print(f"Using cache for lines {current_idx} to {end_idx}...")
            detected_raw = cache[chunk_key]
            detected_topics = [TopicSpan(**t) for t in detected_raw]
        else:
            chunk_slice = df.iloc[current_idx:end_idx]
            chunk_text = "\n".join([
                f"Page {row['page']} Line {row['line']}: {row['text']}"
                for _, row in chunk_slice.iterrows()
            ])
            
            print(f"Processing lines {current_idx} to {end_idx}...")
            detected_topics = process_chunk(chunk_text)
            
            if detected_topics is not None:
                cache[chunk_key] = [t.model_dump() for t in detected_topics]
                with open(cache_path, "w") as f:
                    json.dump(cache, f, indent=2)
            else:
                detected_topics = []  # <--- SAFEGUARD: Never None

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
                "evidence": t.evidence_summary,
                "start_quote": t.start_quote,
                "end_quote": t.end_quote
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

    cleaned_index = []
    for t in final_topics:
        cleaned_index.append({
            "topic": t["topic"],
            "start": f"Page {t['start_page']}, Line {t['start_line']}",
            "end": f"Page {t['end_page']}, Line {t['end_line']}",
            "supporting_evidence": t["evidence"],
            "anchors": {
                "start_quote": t["start_quote"],
                "end_quote": t["end_quote"]
            }
        })

    # Save JSON with UTF-8
    json_path = os.path.join(output_dir, "topic_index.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_index, f, indent=2, ensure_ascii=False)
    print(f"Saved: {json_path}")

    # Save Markdown with UTF-8
    md_path = os.path.join(output_dir, "topic_index.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Deposition Topic Index: Persis Yu\n\n")
        f.write("| Topic | Start | End | Supporting Evidence |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for t in cleaned_index:
            # Strip internal newlines so Markdown tables stay clean
            clean_evidence = t['supporting_evidence'].replace("\n", " ").strip()
            f.write(f"| **{t['topic']}** | {t['start']} | {t['end']} | {clean_evidence} |\n")
    print(f"Saved: {md_path}")
    
if __name__ == "__main__":
    run_pipeline()