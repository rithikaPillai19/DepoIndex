import streamlit as st
import json
import os
import pandas as pd

st.set_page_config(page_title="DepoIndex — 4-Pillar Validated Indexer", page_icon="⚖️", layout="wide")

TOPIC_PATH = "output/topic_index.json"
TRANSCRIPT_PATH = "data/parsed_transcript.json"

if not os.path.exists(TOPIC_PATH) or not os.path.exists(TRANSCRIPT_PATH):
    st.error("Please run `python -m src.pipeline` first.")
    st.stop()

@st.cache_data
def load_data():
    with open(TOPIC_PATH, "r", encoding="utf-8") as f:
        t_data = json.load(f)
    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        trans_data = json.load(f)
    return t_data, pd.DataFrame(trans_data)

topics, df_transcript = load_data()

st.sidebar.markdown("### ⚖️ **DepoIndex Verifier**")
st.sidebar.caption("4-Pillar Validation + Fallback Layer")

selected_idx = st.sidebar.selectbox("Select Topic to Audit:", range(len(topics)), format_func=lambda i: f"{i+1:02d}. {topics[i]['topic']}")
selected_topic = topics[selected_idx]

col1, col2 = st.columns([5, 6], gap="large")

with col1:
    st.markdown(f"## {selected_topic['topic']}")

    # Validation Status Display
    status = selected_topic.get("validation_status", "UNKNOWN")
    if status == "ALL_4_PILLARS_PASSED":
        scores = selected_topic.get("validation_scores", {})
        st.success(f"✅ **4-Pillar Validation Passed** | Start Match: {scores.get('start_score')}% | End Match: {scores.get('end_score')}%")
    else:
        st.warning("⚠️ **Fallback Mechanism Triggered**")
        st.markdown("**Fallback Diagnostics:**")
        for diag in selected_topic.get("fallback_diagnostics", []):
            st.write(f"- {diag}")

    st.markdown(f"**Physical Coordinates:** `{selected_topic['start']}` to `{selected_topic['end']}`")

    st.markdown("#### 💡 Supporting Testimony Evidence")
    st.info(selected_topic["supporting_evidence"])

    if "anchors" in selected_topic:
        st.markdown("#### ⚓ Verbatim Quote Anchors")
        st.caption("**Opening Anchor:**")
        st.code(selected_topic["anchors"].get("start_quote", "N/A"), language="text")
        st.caption("**Closing Anchor:**")
        st.code(selected_topic["anchors"].get("end_quote", "N/A"), language="text")

with col2:
    try:
        start_page = int(selected_topic["start"].split("Page ")[1].split(",")[0])
        start_line = int(selected_topic["start"].split("Line ")[1])
        end_page = int(selected_topic["end"].split("Page ")[1].split(",")[0])
        end_line = int(selected_topic["end"].split("Line ")[1])
    except Exception:
        start_page, start_line, end_page, end_line = 7, 1, 7, 25

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

        st.text_area("Source Text", value="\n".join(rendered), height=550)