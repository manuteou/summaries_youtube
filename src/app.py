import streamlit as st
import os
from workflow import WorkflowManager
from streamlit_quill import st_quill
import markdown
from markdownify import markdownify as md

# Page config
st.set_page_config(page_title="YouTube Summarizer", page_icon="📝", layout="wide")

# Load Custom CSS
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

css_path = os.path.join(os.path.dirname(__file__), "assets", "streamlit_app.css")
if os.path.exists(css_path):
    load_css(css_path)

# Initialize session state
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "title" not in st.session_state:
    st.session_state.title = ""
if "source_info" not in st.session_state:
    st.session_state.source_info = []
if "generated" not in st.session_state:
    st.session_state.generated = False
if "manual_videos" not in st.session_state:
    st.session_state.manual_videos = []
if "search_object" not in st.session_state:
    st.session_state.search_object = None
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "visible_count" not in st.session_state:
    st.session_state.visible_count = 10
if "quill_key" not in st.session_state:
    st.session_state.quill_key = 0

# Sidebar Configuration
st.sidebar.title("Configuration")
device = st.sidebar.selectbox("Device", ["cpu", "cuda"], index=0 if os.getenv("DEVICE") == "cpu" else 1)
model = st.sidebar.selectbox("Whisper Model", ["tiny", "base", "small", "medium", "large"], index=3) # Default medium
ollama_model = st.sidebar.text_input("Ollama Model", value=os.getenv("OLLAMA_MODEL", "mistral"))
output_format = st.sidebar.selectbox("Output Format", ["md", "txt", "html", "pdf"], index=2)
summary_type = st.sidebar.selectbox("Summary Type", ["short", "medium", "long"], index=0)

# Initialize Workflow Manager
@st.cache_resource
def get_workflow(device, model, ollama_model, summary_type, version=1):
    return WorkflowManager(device=device, model=model, ollama_model=ollama_model, summary_type=summary_type)

workflow = get_workflow(device, model, ollama_model, summary_type, version=2)

st.title("📝 YouTube Video Summarizer")

# Tabs
tab_search, tab_manual, tab_local, tab_result = st.tabs(["🔍 Search", "✍️ Manual", "📁 Local File", "📝 Résultat"])

# --- Tab 2: Search ---
with tab_search:
    st.header("Search and Summarize")
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        query = st.text_input("Search Query", label_visibility="collapsed", placeholder="Search for videos...")
    
    # Advanced Filters
    with st.expander("🛠️ Advanced Filters"):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            sort_option = st.selectbox("Sort By", ["Relevance", "Date", "Views"], index=0)
        with col_f2:
            date_option = st.selectbox("Upload Date", ["Any", "Today", "Week", "Month", "Year"], index=0)
        with col_f3:
            dur_option = st.selectbox("Duration", ["Any", "Short (<5m)", "Medium (5-20m)", "Long (>20m)"], index=0)
        with col_f4:
            type_options = st.multiselect("Type", ["Documentary", "Tutorial", "Conference", "Review"])

    # Mapping for backend
    sort_map = {"Relevance": "relevance", "Date": "date", "Views": "views"}
    date_map = {"Any": None, "Today": "today", "Week": "week", "Month": "month", "Year": "year"}
    dur_map = {"Any": "any", "Short (<5m)": "short", "Medium (5-20m)": "medium", "Long (>20m)": "long"}
    
    final_sort = sort_map[sort_option]
    final_date = date_map[date_option]
    final_dur = dur_map[dur_option]

    # Advisory Note
    st.info("💡 **Conseil :** Sélectionnez le nombre de vidéos en fonction du type de résumé souhaité :\n"
            "- **Short** : articles court 7 à 10 vidéos\n"
            "- **Medium** : articles moyen 4 à 6 vidéos\n"
            "- **Long** : articles long 1 à 3 vidéos (Attention, le traitement sera plus long)")

    if "search_object" not in st.session_state:
        st.session_state.search_object = None
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    if "visible_count" not in st.session_state:
        st.session_state.visible_count = 10

    if st.session_state.visible_count not in st.session_state:
        st.session_state.visible_count = 10

    # Search Button Logic
    do_search = False
    with col_btn:
        if st.button("Search", key="btn_search", type="primary"):
            do_search = True

    if do_search:
        if query:
            with st.spinner("Searching..."):
                # Append keywords to query
                final_query = query
                if type_options:
                    final_query += " " + " ".join(type_options)
                
                # Init search session
                st.session_state.search_object = workflow.init_search(final_query, sort_by=final_sort, upload_date=final_date)
                # Store duration preference in session state to use during load more
                st.session_state.filter_duration = final_dur
                
                st.session_state.search_results = workflow.get_search_results(st.session_state.search_object, duration_mode=final_dur)
                st.session_state.visible_count = 10
        else:
            st.warning("Please enter a query.")

    if st.session_state.search_results:
        # Slice results based on visible_count
        visible_results = st.session_state.search_results[:st.session_state.visible_count]
        st.write(f"Showing {len(visible_results)} videos (Total loaded: {len(st.session_state.search_results)}):")
        selected_videos = []
        
        # Display videos in a grid or list with details
        # Display videos in a grid
        cols = st.columns(3) # 3 cards per row
        
        for idx, v in enumerate(visible_results):
            col = cols[idx % 3]
            with col:
                # Card Container
                with st.container():
                    st.markdown(f"""
                    <div class="video-card">
                        <img src="{v.thumbnail_url}" style="width:100%; border-radius: 5px; margin-bottom: 10px;">
                        <div class="video-title">{v.title}</div>
                        <div class="video-meta">Author: {v.author}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    duration_min = v.length // 60
                    duration_sec = v.length % 60
                    st.caption(f"⏱️ {duration_min}m{duration_sec:02d}s")
                    
                    # Try to get description safely
                    try:
                        desc = v.description
                    except Exception:
                        desc = "No description available."
                    
                    if not desc: desc = "No description available."
                    short_desc = (desc[:100] + '...') if len(desc) > 100 else desc
                    st.markdown(f'<div class="video-desc">{short_desc}</div>', unsafe_allow_html=True)
                    
                    if st.checkbox(f"Select", key=v.watch_url):
                        selected_videos.append(v)
        
        col_synth, col_load = st.columns([1, 1])
        
        with col_synth:
            if st.button(f"Synthesize Selected Videos ({len(selected_videos)})", key="btn_synth_search"):
                if selected_videos:
                    with st.spinner("Synthesizing..."):
                        try:
                            summary, title, source_info = workflow.synthesize_videos(selected_videos, query)
                            # Convert to HTML for the editor
                            html_summary = markdown.markdown(summary, extensions=['extra'])
                            st.session_state.summary = html_summary
                            st.session_state.title = title
                            st.session_state.source_info = source_info
                            st.session_state.generated = True
                            st.session_state.quill_key += 1
                            st.success("Synthesis complete! Go to the '📝 Résultat' tab to view it.")
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Please select at least one video.")

        with col_load:
            if st.session_state.search_object and st.button("Load More (+5)", key="btn_load_more"):
                with st.spinner("Loading more..."):
                    st.session_state.visible_count += 5
                    # Check if we need to fetch more from YouTube
                    if st.session_state.visible_count > len(st.session_state.search_results):
                        # Use stored duration filter
                        dur_mode = st.session_state.get("filter_duration", "any")
                        new_results = workflow.load_more_videos(st.session_state.search_object, duration_mode=dur_mode)
                        # Append new results avoiding duplicates if any (though pytube handles this usually)
                        current_urls = {v.watch_url for v in st.session_state.search_results}
                        for v in new_results:
                            if v.watch_url not in current_urls:
                                st.session_state.search_results.append(v)
                    st.rerun()

# --- Tab 3: Manual ---
with tab_manual:
    col_man_input, col_man_list = st.columns([1, 1])
    
    with col_man_input:
        st.subheader("Add Video")
        manual_url = st.text_input("YouTube URL", placeholder="https://youtube.com/...")
        if st.button("Add to List", key="btn_add_manual"):
            if manual_url:
                with st.spinner("Fetching info..."):
                    try:
                        video = workflow.get_video_info(manual_url)
                        if video:
                            st.session_state.manual_videos.append(video)
                            st.success(f"Added: {video.title}")
                        else:
                            st.error("Could not fetch video info.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with col_man_list:
        st.subheader("Selected Videos")
        if st.session_state.manual_videos:
            for i, v in enumerate(st.session_state.manual_videos):
                st.markdown(f"**{i+1}. {v.title}** ({v.author})")
            
            st.divider()
            manual_title = st.text_input("Title for the Synthesis", value="Synthèse Manuelle")
        else:
            st.info("No videos added yet.")

# --- Tab 4: Local File ---
with tab_local:
    st.header("Local MP4 File")
    file_path = st.text_input("Absolute Path to MP4 file")
    if st.button("Process File", key="btn_file"):
        if file_path and os.path.exists(file_path):
            with st.spinner("Processing file..."):
                try:
                    summary, title, source_info = workflow.process_video_path(file_path, summary_type)
                    # Convert to HTML for the editor
                    html_summary = markdown.markdown(summary, extensions=['extra'])
                    st.session_state.summary = html_summary
                    st.session_state.title = title
                    st.session_state.source_info = source_info
                    st.session_state.generated = True
                    st.session_state.quill_key += 1
                    st.success("Processing complete! Go to the '📝 Résultat' tab to view it.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.error("File not found.")
with tab_result:
    if st.session_state.generated:
        st.header("📝 Result (Editable)")
        
        col_res_main, col_res_side = st.columns([3, 1])
        
        with col_res_main:
            st.subheader("Edit Summary")
            # Quill Editor
            content = st_quill(
                value=st.session_state.summary,
                placeholder="Write your summary here...",
                html=True,
                key=f"quill_editor_{st.session_state.quill_key}",
                toolbar=[
                    ["bold", "italic", "underline", "strike"],
                    [{"header": [1, 2, 3, False]}],
                    [{"list": "ordered"}, {"list": "bullet"}],
                    [{"indent": "-1"}, {"indent": "+1"}],
                    [{"color": []}, {"background": []}],
                    ["clean"]
                ]
            )
            
            # Update session state if edited (Quill returns HTML)
            if content and content != st.session_state.summary:
                st.session_state.summary = content

        with col_res_side:
            st.subheader("Actions")
            st.info(f"**Title:**\n{st.session_state.title}")
            
            st.warning("⚠️ Editor content is HTML.")
            
            if st.button("💾 Save Summary", type="primary"):
                try:
                    content_to_save = st.session_state.summary
                    
                    # Convert back to Markdown/Text if needed
                    if output_format in ["md", "txt"]:
                        content_to_save = md(content_to_save, heading_style="ATX")
                    
                    saved_path = workflow.save_summary(content_to_save, st.session_state.title, output_format, st.session_state.source_info)
                    st.success(f"Saved to: {saved_path}")
                except Exception as e:
                    st.error(f"Error saving: {e}")
    else:
        st.info("No summary generated yet. Please use one of the other tabs to generate a summary.")
