import streamlit as st
import json
import os
import pandas as pd

# ---------------------------------------------------------
# Page Config & Custom Legal-Tech Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="DepoIndex — Verifiable Legal Transcription Indexer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Metric & Card Styling */
    .metric-box {
        background-color: #1a1e24;
        border: 1px solid #2d333b;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 15px;
    }
    .badge-pill {
        display: inline-block;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 12px;
        background-color: #238636;
        color: #ffffff;
        margin-right: 6px;
    }
    .badge-secondary {
        background-color: #30363d;
        color: #c9d1d9;
    }
    /* Transcript viewer scroll container */
    .transcript-container {
        font-family: "SF Mono", "Fira Code", "Courier New", monospace;
        font-size: 13.5px;
        line-height: 1.6;
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        height: 620px;
        overflow-y: auto;
    }
    .line-row {
        display: flex;
        padding: 2px 6px;
        border-radius: 4px;
        margin-bottom: 1px;
    }
    .line-num {
        color: #8b949e;
        width: 48px;
        font-weight: 600;
        user-select: none;
        flex-shrink: 0;
    }
    .line-text {
        color: #e6edf3;
        word-break: break-word;
    }
    .active-line {
        background-color: rgba(46, 160, 67, 0.22);
        border-left: 3px solid #2ea043;
    }
    .active-line .line-num {
        color: #3fb950;
        font-weight: bold;
    }
    .active-line .line-text {
        color: #ffffff;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Data Ingestion
# ---------------------------------------------------------
TOPIC_PATH = "output/topic_index.json"
TRANSCRIPT_PATH = "data/parsed_transcript.json"

if not os.path.exists(TOPIC_PATH) or not os.path.exists(TRANSCRIPT_PATH):
    st.error("Missing input files. Please run `python -m src.pipeline` first.")
    st.stop()

@st.cache_data
def load_data():
    with open(TOPIC_PATH, "r", encoding="utf-8") as f:
        topics_data = json.load(f)
    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)
    return topics_data, pd.DataFrame(transcript_data)

topics, df_transcript = load_data()

# ---------------------------------------------------------
# Sidebar Controls & Case Meta
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚖️ **DepoIndex Workspace**")
    st.caption("Verifiable Deposition Topic Indexer")
    
    st.markdown(f"""
    <div class="metric-box">
        <small style="color:#8b949e;">DEPONENT</small><br>
        <strong>Persis S. Yu</strong><br>
        <small style="color:#8b949e;">TOTAL SUBSTANTIVE TOPICS</small><br>
        <span style="font-size:22px; font-weight:700; color:#58a6ff;">{len(topics)}</span>
    </div>
    """, unsafe_allow_html=True)
    
    search_query = st.text_input("🔍 Filter topics by keyword:", placeholder="e.g., Servicing, PEAKS, Rulemaking")
    
    filtered_indices = [
        i for i, t in enumerate(topics)
        if not search_query or search_query.lower() in t.get("topic", "").lower() or search_query.lower() in t.get("supporting_evidence", "").lower()
    ]
    
    if not filtered_indices:
        st.warning("No matching topics found.")
        st.stop()
        
    topic_labels = [f"{i+1:02d}. {topics[i].get('topic')} ({topics[i].get('start')})" for i in filtered_indices]
    selected_display = st.selectbox("Select Topic Index Entry:", options=topic_labels)
    selected_idx = filtered_indices[topic_labels.index(selected_display)]
    selected_topic = topics[selected_idx]
    
    st.markdown("---")
    st.caption("🔒 **Provenance Guarantee**: Line coordinates resolved deterministically via verbatim AST quote anchors.")

# ---------------------------------------------------------
# Main Panel: Multi-Tab Interface
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["🔍 Side-by-Side Audit", "📋 Complete Topic Index Table"])

with tab1:
    col_left, col_right = st.columns([5, 6], gap="large")

    start_str = selected_topic.get("start", "")
    end_str = selected_topic.get("end", "")

    try:
        start_page = int(start_str.split("Page ")[1].split(",")[0].strip())
        start_line = int(start_str.split("Line ")[1].strip())
    except Exception:
        start_page, start_line = 7, 1

    try:
        end_page = int(end_str.split("Page ")[1].split(",")[0].strip())
        end_line = int(end_str.split("Line ")[1].strip())
    except Exception:
        end_page, end_line = start_page, start_line

    anchors = selected_topic.get("anchors", {})

    with col_left:
        st.markdown("### 📑 Substantive Topic Record")
        st.markdown(f"## **{selected_topic.get('topic')}**")
        
        st.markdown(
            f'<span class="badge-pill">Start: Page {start_page}, Line {start_line}</span>'
            f'<span class="badge-pill badge-secondary">End: Page {end_page}, Line {end_line}</span>',
            unsafe_allow_html=True
        )
        
        st.markdown("#### 💡 Supporting Testimony Evidence")
        st.info(selected_topic.get("supporting_evidence", "No evidence summary provided."))
        
        st.markdown("#### ⚓ Verbatim Quote Anchors")
        st.markdown("**Opening Anchor:**")
        st.code(f'"{anchors.get("start_quote", "N/A")}"', language="text")
        st.markdown("**Closing Anchor:**")
        st.code(f'"{anchors.get("end_quote", "N/A")}"', language="text")

    with col_right:
        available_pages = list(range(start_page, end_page + 1))
        if len(available_pages) > 1:
            chosen_page = st.segmented_control("Viewing Page in Topic Range:", options=available_pages, default=start_page)
        else:
            chosen_page = start_page
            
        st.markdown(f"### 🔍 Transcript Viewer — Page {chosen_page}")
        
        page_rows = df_transcript[df_transcript["page"] == chosen_page]
        
        if page_rows.empty:
            st.write("No transcript lines recorded on this page.")
        else:
            html_lines = ['<div class="transcript-container">']
            
            for _, row in page_rows.iterrows():
                l_no = int(row["line"])
                raw_text = str(row["text"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                in_range = False
                if chosen_page == start_page == end_page:
                    in_range = (start_line <= l_no <= end_line)
                elif chosen_page == start_page:
                    in_range = (l_no >= start_line)
                elif chosen_page == end_page:
                    in_range = (l_no <= end_line)
                elif start_page < chosen_page < end_page:
                    in_range = True
                    
                line_class = "line-row active-line" if in_range else "line-row"
                indicator = " ◄" if in_range else ""
                
                html_lines.append(
                    f'<div class="{line_class}">'
                    f'<span class="line-num">L{l_no:02d}</span>'
                    f'<span class="line-text">{raw_text}{indicator}</span>'
                    f'</div>'
                )
                
            html_lines.append("</div>")
            st.markdown("".join(html_lines), unsafe_allow_html=True)
            st.caption("🟢 Green background indicates the active topic line span as resolved by DepoIndex.")

with tab2:
    st.markdown("### 📋 Complete Chronological Deposition Topic Index")
    st.caption("Formal 4-column index matching court production requirements.")

    table_records = [
        {
            "Topic": t.get("topic"),
            "Start": t.get("start"),
            "End": t.get("end"),
            "Supporting Evidence": t.get("supporting_evidence")
        }
        for t in topics
    ]
    
    df_index = pd.DataFrame(table_records)

    st.dataframe(
        df_index,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Topic": st.column_config.TextColumn("Topic", width="medium"),
            "Start": st.column_config.TextColumn("Start", width="small"),
            "End": st.column_config.TextColumn("End", width="small"),
            "Supporting Evidence": st.column_config.TextColumn("Supporting Evidence", width="large"),
        }
    )

    csv_data = df_index.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Topic Index as CSV",
        data=csv_data,
        file_name="persis_yu_topic_index.csv",
        mime="text/csv"
    )
