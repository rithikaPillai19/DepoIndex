import streamlit as st
import json
import os
import pandas as pd

st.set_page_config(
    page_title="DepoIndex - Deposition Topic Indexer",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ DepoIndex: Verifiable Topic Index")
st.caption("Deposition of Persis Yu | Deterministic Line-Level Provenance")

TOPIC_PATH = "output/topic_index.json"
TRANSCRIPT_PATH = "data/parsed_transcript.json"

# Check if data exists
if not os.path.exists(TOPIC_PATH) or not os.path.exists(TRANSCRIPT_PATH):
    st.error("Output files missing. Please run `python -m src.pipeline` first.")
    st.stop()

@st.cache_data
def load_data():
    with open(TOPIC_PATH, "r", encoding="utf-8") as f:
        topics_data = json.load(f)
    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)
    return topics_data, pd.DataFrame(transcript_data)

try:
    topics, df_transcript = load_data()
except Exception as e:
    st.error(f"Error loading files: {e}")
    st.stop()

if not topics:
    st.warning("`topic_index.json` is empty. Ensure `python -m src.pipeline` finished processing.")
    st.stop()

col_left, col_right = st.columns([1, 1], gap="medium")

with col_left:
    st.subheader(f"📑 Identified Topics ({len(topics)})")
    
    options = [f"{i+1}. {t.get('topic', 'Untitled')} ({t.get('start', 'N/A')})" for i, t in enumerate(topics)]
    selected_label = st.selectbox("Select a topic to verify:", options=options)
    selected_idx = options.index(selected_label)
    selected_topic = topics[selected_idx]

    st.markdown("---")
    st.markdown(f"### **{selected_topic.get('topic', 'Topic')}**")
    st.markdown(f"📍 **Span:** `{selected_topic.get('start', '')}` to `{selected_topic.get('end', '')}`")
    
    st.markdown("#### **Supporting Evidence**")
    st.info(selected_topic.get('supporting_evidence', 'No summary available.'))

    anchors = selected_topic.get("anchors", {})
    st.markdown("#### **Verbatim Quote Anchors**")
    st.code(f"Start: \"{anchors.get('start_quote', '')}\"\nEnd:   \"{anchors.get('end_quote', '')}\"", language="text")

with col_right:
    st.subheader("🔍 Source Transcript Verification")
    
    start_str = selected_topic.get("start", "")
    page_no = 7  # default fallback
    if "Page " in start_str:
        try:
            page_no = int(start_str.split("Page ")[1].split(",")[0].strip())
        except Exception:
            page_no = 7

    st.markdown(f"**Showing Page {page_no}**")
    
    # Filter transcript for the specific page
    page_slice = df_transcript[df_transcript["page"] == page_no]
    
    start_anchor = anchors.get("start_quote", "").lower()
    end_anchor = anchors.get("end_quote", "").lower()

    if page_slice.empty:
        st.write("No text extracted for this page.")
    else:
        for _, row in page_slice.iterrows():
            text = row['text']
            line_no = row['line']
            
            # Highlight matched lines
            if start_anchor and start_anchor in text.lower():
                st.markdown(f"🟢 `L{line_no:02d}` **{text}** *(Topic Start)*")
            elif end_anchor and end_anchor in text.lower():
                st.markdown(f"🔴 `L{line_no:02d}` **{text}** *(Topic End)*")
            else:
                st.markdown(f"`L{line_no:02d}` {text}")