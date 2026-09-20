import streamlit as st
import json
import os
import re
import pandas as pd

st.set_page_config(
    page_title="DepoIndex — 4-Pillar Validated Indexer", 
    page_icon="⚖️", 
    layout="wide"
)

TOPIC_PATH = "output/topic_index.json"
TRANSCRIPT_PATH = "data/parsed_transcript.json"

if not os.path.exists(TOPIC_PATH) or not os.path.exists(TRANSCRIPT_PATH):
    st.error("Missing index files. Please execute `python -m src.pipeline` first.")
    st.stop()

@st.cache_data
def load_data():
    with open(TOPIC_PATH, "r", encoding="utf-8") as f:
        t_data = json.load(f)
    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        trans_data = json.load(f)
    return t_data, pd.DataFrame(trans_data)

topics, df_transcript = load_data()

if not topics:
    st.warning("No topics currently present in `topic_index.json`. Please rerun the pipeline.")
    st.stop()

st.sidebar.markdown("### ⚖️ **DepoIndex Verifier**")
st.sidebar.caption("4-Pillar Validation + Fallback Layer")

# Robust selector formatting
selected_idx = st.sidebar.selectbox(
    "Select Topic to Audit:", 
    range(len(topics)), 
    format_func=lambda i: f"{i+1:02d}. {topics[i].get('topic', 'Untitled')}"
)
selected_topic = topics[selected_idx]

# Robust coordinate parsing with regex (immune to formatting variations)
def parse_coords(coord_str: str, default_page=7, default_line=1):
    try:
        page_match = re.search(r"Page\s+(\d+)", coord_str, re.IGNORECASE)
        line_match = re.search(r"Line\s+(\d+)", coord_str, re.IGNORECASE)
        page = int(page_match.group(1)) if page_match else default_page
        line = int(line_match.group(1)) if line_match else default_line
        return page, line
    except Exception:
        return default_page, default_line

start_page, start_line = parse_coords(selected_topic.get("start", ""), default_page=7, default_line=1)
end_page, end_line = parse_coords(selected_topic.get("end", ""), default_page=start_page, default_line=25)

# Ensure end_page is at least start_page
if end_page < start_page:
    end_page = start_page

col1, col2 = st.columns([6, 6], gap="large")

with col1:
    # Full Topic Header
    st.subheader(selected_topic.get("topic", "Unassigned Topic"))

    # Validation Status Banner
    status = selected_topic.get("validation_status", "UNKNOWN")
    if status == "ALL_4_PILLARS_PASSED":
        scores = selected_topic.get("validation_scores", {})
        st.success(f"✅ **4-Pillar Validation Passed** | Start: {scores.get('start_score', 100)}% | End: {scores.get('end_score', 100)}%")
    else:
        st.warning("⚠️ **Pillar 5 Fallback Triggered**")
        st.markdown("**Diagnostics:**")
        diagnostics = selected_topic.get("fallback_diagnostics", ["Boundary or span expansion adjusted."])
        for diag in diagnostics:
            st.write(f"- `{diag}`")

    st.markdown(f"**Physical Coordinates:** `{selected_topic.get('start')}` to `{selected_topic.get('end')}`")

    st.markdown("#### 💡 Supporting Testimony Evidence")
    st.info(selected_topic.get("supporting_evidence", "No evidence summary provided."))

    # Quote Anchors with Fallback Safety
    anchors = selected_topic.get("anchors", {})
    if anchors:
        st.markdown("#### ⚓ Verbatim Quote Anchors")
        st.caption("**Opening Sentence Anchor:**")
        st.code(anchors.get("start_quote", "Not captured in raw output"), language="text")
        st.caption("**Closing Sentence Anchor:**")
        st.code(anchors.get("end_quote", "Not captured in raw output"), language="text")

with col2:
    pages = list(range(start_page, end_page + 1))
    view_page = st.selectbox("View Source Page in Range:", pages) if len(pages) > 1 else start_page

    st.markdown(f"### 🔍 Transcript Viewer — Page {view_page}")
    page_rows = df_transcript[df_transcript["page"] == view_page]

    if not page_rows.empty:
        rendered = []
        for _, r in page_rows.iterrows():
            l_no = int(r["line"])
            txt = str(r["text"])

            is_active = False
            if view_page == start_page == end_page:
                is_active = (start_line <= l_no <= end_line)
            elif view_page == start_page:
                is_active = (l_no >= start_line)
            elif view_page == end_page:
                is_active = (l_no <= end_line)
            elif start_page < view_page < end_page:
                is_active = True

            prefix = "🟢 " if is_active else "   "
            rendered.append(f"{prefix}L{l_no:02d}: {txt}")

        st.text_area("Source Text", value="\n".join(rendered), height=580)
    else:
        st.info(f"Page {view_page} has no substantive dialogue lines.")