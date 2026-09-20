import streamlit as st
import json
import os
import pandas as pd

# -------------------------------------------------------------
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# -------------------------------------------------------------
st.set_page_config(
    page_title="DepoIndex Workspace",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS matching the dark litigation console layout from the reference
st.markdown("""
<style>
    /* Dark theme background overrides */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
        padding-top: 1.5rem;
    }

    /* Deponent Metadata Card in Sidebar */
    .depo-meta-card {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 20px;
    }
    .depo-meta-label {
        font-size: 0.75rem;
        font-weight: 700;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .depo-meta-val {
        font-size: 1.05rem;
        font-weight: 600;
        color: #f0f6fc;
        margin-bottom: 12px;
    }
    .depo-stat-num {
        font-size: 1.75rem;
        font-weight: 700;
        color: #58a6ff;
        line-height: 1.2;
    }

    /* Provenance note in Sidebar footer */
    .provenance-card {
        font-size: 0.8rem;
        color: #8b949e;
        line-height: 1.4;
        padding-top: 15px;
        border-top: 1px solid #30363d;
        margin-top: 25px;
    }

    /* Table styling matching the formal 4-column index */
    .depo-table {
        width: 100%;
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        font-size: 0.9rem;
        margin-top: 15px;
    }
    .depo-table th {
        background-color: #161b22;
        color: #8b949e;
        font-weight: 600;
        text-align: left;
        padding: 12px 14px;
        border-bottom: 2px solid #30363d;
    }
    .depo-table td {
        padding: 12px 14px;
        border-bottom: 1px solid #21262d;
        color: #e6edf3;
        vertical-align: top;
    }
    .depo-table tr:hover td {
        background-color: #1c2128;
    }

    /* Transcript Viewer Container */
    .transcript-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 18px;
        max-height: 650px;
        overflow-y: auto;
        font-family: "Courier New", Courier, monospace;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    .line-number {
        color: #6e7681;
        user-select: none;
        display: inline-block;
        width: 120px;
    }
    .highlighted-line {
        background-color: #388bfd26;
        border-left: 3px solid #58a6ff;
        color: #ffffff;
        font-weight: 500;
        display: block;
        padding: 2px 4px;
        border-radius: 2px;
    }
    .regular-line {
        color: #c9d1d9;
        display: block;
        padding: 1px 4px;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# 2. DATA LOADERS
# -------------------------------------------------------------
@st.cache_data
def load_index_data():
    index_path = "output/topic_index.json"
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@st.cache_data
def load_transcript():
    transcript_path = "data/parsed_transcript.json"
    if os.path.exists(transcript_path):
        with open(transcript_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

topics = load_index_data()
transcript = load_transcript()


# -------------------------------------------------------------
# 3. SIDEBAR NAVIGATION & FILTERS
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚖️ **DepoIndex Workspace**")
    st.caption("Verifiable Deposition Topic Indexer")

    # Deponent & Metadata Overview Card
    total_count = len(topics)
    st.markdown(f"""
    <div class="depo-meta-card">
        <div class="depo-meta-label">DEPONENT</div>
        <div class="depo-meta-val">Persis S. Yu</div>
        <div class="depo-meta-label">TOTAL SUBSTANTIVE TOPICS</div>
        <div class="depo-stat-num">{total_count}</div>
    </div>
    """, unsafe_allow_html=True)

    # Keyword Search Filter
    filter_query = st.text_input(
        "🔍 Filter topics by keyword:",
        placeholder="e.g., Servicing, PEAKS, Rulemaking"
    ).strip().lower()

    filtered_topics = [
        t for t in topics
        if filter_query in t["topic"].lower()
        or filter_query in t.get("supporting_evidence", "").lower()
    ] if filter_query else topics

    # Topic Selector for Side-by-Side View
    topic_options = [f"{i+1:02d}. {t['topic']}" for i, t in enumerate(filtered_topics)]
    selected_idx = 0

    if topic_options:
        selected_option = st.selectbox("Select Topic Index Entry:", topic_options, index=0)
        selected_idx = topic_options.index(selected_option)
    else:
        st.warning("No matching topics found.")

    # Audit & Provenance Guarantee Footer
    st.markdown("""
    <div class="provenance-card">
        🔒 <b>Provenance Guarantee:</b> Line coordinates resolved deterministically via verbatim AST quote anchors.
    </div>
    """, unsafe_allow_html=True)


# -------------------------------------------------------------
# 4. MAIN WORKSPACE TABS
# -------------------------------------------------------------
tab_audit, tab_table = st.tabs(["🔍 Side-by-Side Audit", "📋 Complete Topic Index Table"])

# =============================================================
# TAB 1: SIDE-BY-SIDE AUDIT
# =============================================================
with tab_audit:
    if filtered_topics:
        active_topic = filtered_topics[selected_idx]
        col_meta, col_trans = st.columns([1, 1], gap="large")

        with col_meta:
            st.markdown(f"### {active_topic['topic']}")
            
            # Citation coordinates & validation status
            status_color = "#3fb950" if active_topic.get("validation_status") == "ALL_4_PILLARS_PASSED" else "#d29922"
            status_text = "ALL 4 PILLARS PASSED" if active_topic.get("validation_status") == "ALL_4_PILLARS_PASSED" else "FALLBACK LOGGED"

            st.markdown(f"""
            <div style="background-color: #161b22; padding: 14px; border-radius: 6px; border: 1px solid #30363d; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="color: #8b949e; font-size: 0.85rem;">COORDINATE SPAN</span>
                    <span style="background-color: {status_color}22; color: {status_color}; border: 1px solid {status_color}; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 12px;">
                        {status_text}
                    </span>
                </div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f0f6fc;">
                    {active_topic['start']} &nbsp;➔&nbsp; {active_topic['end']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### 📝 Supporting Evidence")
            st.info(active_topic.get("supporting_evidence", "No evidence summary provided."))

            # Verbatim Anchor Quotes with rapidfuzz scores
            anchors = active_topic.get("anchors", {})
            scores = active_topic.get("validation_scores", {})
            if anchors:
                st.markdown("#### 🎯 Verbatim AST Anchors")
                st.markdown(f"""
                * **Start Anchor** *(Match Score: `{scores.get('start_score', 'N/A')}%`)*:  
                  `"{anchors.get('start_quote', '')}"`
                * **End Anchor** *(Match Score: `{scores.get('end_score', 'N/A')}%`)*:  
                  `"{anchors.get('end_quote', '')}"`
                """)

        with col_trans:
            st.markdown("### 📜 Verified Deposition Transcript")
            
            start_gid = active_topic.get("start_gid", 0)
            end_gid = active_topic.get("end_gid", len(transcript))

            # Provide window padding context around the inquiry
            context_start = max(0, start_gid - 4)
            context_end = min(len(transcript), end_gid + 5)

            transcript_html = ['<div class="transcript-box">']
            for gid in range(context_start, context_end):
                row = transcript[gid]
                line_tag = f"Page {row['page']}, Line {row['line']:02d}"
                is_target = (start_gid <= gid <= end_gid)

                if is_target:
                    transcript_html.append(
                        f'<div class="highlighted-line"><span class="line-number">{line_tag}</span> {row["text"]}</div>'
                    )
                else:
                    transcript_html.append(
                        f'<div class="regular-line"><span class="line-number">{line_tag}</span> {row["text"]}</div>'
                    )
            transcript_html.append('</div>')

            st.markdown("".join(transcript_html), unsafe_allow_html=True)
    else:
        st.info("No topic index records to audit.")


# # =============================================================
# TAB 2: COMPLETE TOPIC INDEX TABLE
# =============================================================
with tab_table:
    st.markdown("## 📋 Complete Chronological Deposition Topic Index")
    st.caption("Formal 4-column index matching court production requirements.")

    if filtered_topics:
        # Build pandas DataFrame for robust native rendering
        table_records = []
        for entry in filtered_topics:
            table_records.append({
                "Topic": entry.get("topic", ""),
                "Start": entry.get("start", ""),
                "End": entry.get("end", ""),
                "Supporting Evidence": entry.get("supporting_evidence", "")
            })

        df_display = pd.DataFrame(table_records)

        # Render clean, interactive table matching column widths
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Topic": st.column_config.TextColumn("Topic", width="medium"),
                "Start": st.column_config.TextColumn("Start", width="small"),
                "End": st.column_config.TextColumn("End", width="small"),
                "Supporting Evidence": st.column_config.TextColumn("Supporting Evidence", width="large"),
            }
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # CSV Export Button
        csv_data = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Topic Index as CSV",
            data=csv_data,
            file_name="Persis_Yu_Topic_Index.csv",
            mime="text/csv"
        )
    else:
        st.info("No topic index records found. Run the pipeline first.")