import streamlit as st
import os
from workflow import WorkflowManager

# Page config
st.set_page_config(page_title="YouTube Summarizer", page_icon="📝", layout="wide")

# Initialize session state
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "title" not in st.session_state:
    st.session_state.title = ""
if "source_info" not in st.session_state:
    st.session_state.source_info = []
if "generated" not in st.session_state:
    st.session_state.generated = False

# Sidebar Configuration
st.sidebar.title("Configuration")
device = st.sidebar.selectbox("Device", ["cpu", "cuda"], index=0 if os.getenv("DEVICE") == "cpu" else 1)
model = st.sidebar.selectbox("Whisper Model", ["tiny", "base", "small", "medium", "large"], index=3) # Default medium
ollama_model = st.sidebar.text_input("Ollama Model", value=os.getenv("OLLAMA_MODEL", "mistral"))
output_format = st.sidebar.selectbox("Output Format", ["md", "txt", "pdf"], index=0)
summary_type = st.sidebar.selectbox("Summary Type", ["short", "medium", "long"], index=0)

# Initialize Workflow Manager
@st.cache_resource
def get_workflow(device, model, ollama_model, summary_type):
    return WorkflowManager(device=device, model=model, ollama_model=ollama_model, summary_type=summary_type)

workflow = get_workflow(device, model, ollama_model, summary_type)

st.title("📝 YouTube Video Summarizer")

# Tabs
tab_search, tab_manual, tab_local, tab_result = st.tabs(["🔍 Search", "✍️ Manual", "📁 Local File", "📝 Résultat"])

# --- Tab 2: Search ---
with tab_search:
    st.header("Search and Summarize")
    query = st.text_input("Search Query")
    
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

    if st.button("Search", key="btn_search"):
        if query:
            with st.spinner("Searching..."):
                # Init search session
                st.session_state.search_object = workflow.init_search(query)
                st.session_state.search_results = workflow.get_search_results(st.session_state.search_object)
                st.session_state.visible_count = 10
        else:
            st.warning("Please enter a query.")

    if st.session_state.search_results:
        # Slice results based on visible_count
        visible_results = st.session_state.search_results[:st.session_state.visible_count]
        st.write(f"Showing {len(visible_results)} videos (Total loaded: {len(st.session_state.search_results)}):")
        selected_videos = []
        
        # Display videos in a grid or list with details
        for v in visible_results:
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(v.thumbnail_url, width="stretch")
                with col2:
                    st.subheader(v.title)
                    duration_min = v.length // 60
                    duration_sec = v.length % 60
                    st.caption(f"Author: {v.author} | Duration: {duration_min}m{duration_sec:02d}s")
                    
                    # Try to get description safely
                    desc = getattr(v, "description", "No description available.")
                    if not desc: desc = "No description available."
                    # Truncate description for display
                    short_desc = (desc[:200] + '...') if len(desc) > 200 else desc
                    st.write(short_desc)
                    
                    if st.checkbox(f"Select this video", key=v.watch_url):
                        selected_videos.append(v)
                st.divider()
        
        col_synth, col_load = st.columns([1, 1])
        
        with col_synth:
            if st.button(f"Synthesize Selected Videos ({len(selected_videos)})", key="btn_synth_search"):
                if selected_videos:
                    with st.spinner("Synthesizing..."):
                        try:
                            summary, title, source_info = workflow.synthesize_videos(selected_videos, query)
                            st.session_state.summary = summary
                            st.session_state.title = title
                            st.session_state.source_info = source_info
                            st.session_state.generated = True
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
                        new_results = workflow.load_more_videos(st.session_state.search_object)
                        # Append new results avoiding duplicates if any (though pytube handles this usually)
                        current_urls = {v.watch_url for v in st.session_state.search_results}
                        for v in new_results:
                            if v.watch_url not in current_urls:
                                st.session_state.search_results.append(v)
                    st.rerun()

# --- Tab 3: Manual ---
with tab_manual:
    st.header("Manual Video Entry")
    manual_title = st.text_input("Title for the Synthesis", value="Synthèse Manuelle")
    
    if "manual_videos" not in st.session_state:
        st.session_state.manual_videos = []
        
    manual_url = st.text_input("Add YouTube URL")
    if st.button("Add Video", key="btn_add_manual"):
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

    if st.session_state.manual_videos:
        st.write("Selected Videos:")
        for v in st.session_state.manual_videos:
            st.write(f"- {v.title} ({v.author})")
            
        if st.button("Synthesize Manual List", key="btn_synth_manual"):
            with st.spinner("Synthesizing..."):
                try:
                    summary, title, source_info = workflow.synthesize_videos(st.session_state.manual_videos, manual_title)
                    st.session_state.summary = summary
                    st.session_state.title = title
                    st.session_state.source_info = source_info
                    st.session_state.generated = True
                    st.success("Synthesis complete! Go to the '📝 Résultat' tab to view it.")
                except Exception as e:
                    st.error(f"Error: {e}")
        
        if st.button("Clear List", key="btn_clear_manual"):
            st.session_state.manual_videos = []
            st.rerun()

# --- Tab 4: Local File ---
with tab_local:
    st.header("Local MP4 File")
    file_path = st.text_input("Absolute Path to MP4 file")
    if st.button("Process File", key="btn_file"):
        if file_path and os.path.exists(file_path):
            with st.spinner("Processing file..."):
                try:
                    summary, title, source_info = workflow.process_video_path(file_path, summary_type)
                    st.session_state.summary = summary
                    st.session_state.title = title
                    st.session_state.source_info = source_info
                    st.session_state.generated = True
                    st.success("Processing complete! Go to the '📝 Résultat' tab to view it.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.error("File not found.")

# --- Tab 5: Result (Moved from bottom) ---
with tab_result:
    if st.session_state.generated:
        st.header("📝 Result (Editable)")
        
        # Editable Text Area
        edited_summary = st.text_area("Edit your summary here before saving:", value=st.session_state.summary, height=600)
        
        # Update session state if edited
        if edited_summary != st.session_state.summary:
            st.session_state.summary = edited_summary

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"Title: {st.session_state.title}")
        with col2:
            if st.button("💾 Save Summary", type="primary"):
                try:
                    saved_path = workflow.save_summary(st.session_state.summary, st.session_state.title, output_format, st.session_state.source_info)
                    st.success(f"Saved to: {saved_path}")
                except Exception as e:
                    st.error(f"Error saving: {e}")
    else:
        st.info("No summary generated yet. Please use one of the other tabs to generate a summary.")
