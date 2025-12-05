import streamlit as st
import os
from workflow import WorkflowManager
from streamlit_quill import st_quill
import markdown
from markdownify import markdownify as md
from utils import clean_markdown_text, time_since


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
    st.session_state.visible_count = 9
if "quill_key" not in st.session_state:
    st.session_state.quill_key = 0

# Sidebar Configuration
st.sidebar.title("Configuration")
device = st.sidebar.selectbox("Device", ["cpu", "cuda"], index=0 if os.getenv("DEVICE") == "cpu" else 1)
model = st.sidebar.selectbox("Whisper Model", ["tiny", "base", "small", "medium", "large"], index=3) # Default medium
ollama_model = st.sidebar.text_input("Ollama Model", value=os.getenv("OLLAMA_MODEL", "mistral"))

summary_type = st.sidebar.selectbox("Summary Type", ["short", "medium", "long"], index=0)

# Initialize Workflow Manager
@st.cache_resource
def get_workflow(device, model, ollama_model, summary_type, version=1):
    return WorkflowManager(device=device, model=model, ollama_model=ollama_model, summary_type=summary_type)

workflow = get_workflow(device, model, ollama_model, summary_type, version=4)

st.title("📝 YouTube Video Summarizer")

# Tabs
# Navigation
if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "🔍 Search"

# Navigation Menu (replacing st.tabs)
nav_options = ["🔍 Search", "✍️ Manual", "📁 Local File", "📝 Result"]
nav_selection = st.radio("Navigation", nav_options, index=nav_options.index(st.session_state.nav_selection), horizontal=True, label_visibility="collapsed", key="nav_radio")

# Sync session state if changed by user
if nav_selection != st.session_state.nav_selection:
    st.session_state.nav_selection = nav_selection
    st.rerun()

# --- Tab 1: Search ---
if st.session_state.nav_selection == "🔍 Search":
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
        
        exclude_terms = st.text_input("Mots à exclure (séparés par des espaces)", placeholder="Ex: shorts gaming")

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
        st.session_state.visible_count = 9

    if st.session_state.visible_count not in st.session_state:
        st.session_state.visible_count = 9

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
                st.session_state.search_object = workflow.init_search(final_query, sort_by=final_sort, upload_date=final_date, exclude_terms=exclude_terms)
                # Store duration preference in session state to use during load more
                st.session_state.filter_duration = final_dur
                
                st.session_state.search_results = workflow.get_search_results(st.session_state.search_object, duration_mode=final_dur)
                st.session_state.visible_count = 9
        else:
            st.warning("Please enter a query.")

    if st.session_state.search_results:
        # Show all loaded results directly
        st.write(f"Résultats trouvés : {len(st.session_state.search_results)}")
        selected_videos = []
        
        # Display videos in a grid
        cols = st.columns(3) # 3 cards per row
        
        for idx, v in enumerate(st.session_state.search_results):
            col = cols[idx % 3]
            with col:
                # Card Container
                with st.container():
                    # Calculate relative time
                    rel_time = time_since(v.publish_date)
                    
                    # Format duration
                    duration_min = v.length // 60
                    duration_sec = v.length % 60
                    duration_str = f"{duration_min}:{duration_sec:02d}"

                    # Description handling
                    try:
                        desc = v.description
                    except Exception:
                        desc = "No description available."
                    
                    if not desc: desc = "No description available."

                    st.markdown(f"""
                    <div class="video-card">
                        <div class="thumbnail-container">
                            <img src="{v.thumbnail_url}">
                            <span class="duration-badge">{duration_str}</span>
                        </div>
                        <div class="video-title">{v.title}</div>
                        <div class="video-meta">
                            Author: {v.author}<br>
                            <span style="color: #888; font-size: 0.9em;">{rel_time}</span>
                        </div>
                        <div class="video-desc">{desc}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.checkbox(f"Select", key=v.watch_url):
                        selected_videos.append(v)
        
        col_synth, col_load = st.columns([1, 1])
        
        with col_synth:
            if st.button(f"Synthesize Selected Videos ({len(selected_videos)})", key="btn_synth_search"):
                if selected_videos:
                    if not query:
                        st.error("Veuillez entrer un terme de recherche pour donner un contexte à la synthèse.")
                    else:
                        with st.spinner("Synthesizing..."):
                            try:
                                summary, title, source_info = workflow.synthesize_videos(selected_videos, query)
                                # Clean markdown code blocks from LLM
                                summary = clean_markdown_text(summary)
                                # Convert to HTML for the editor
                                html_summary = markdown.markdown(summary, extensions=['extra'])
                                st.session_state.summary = html_summary
                                st.session_state.title = title
                                st.session_state.source_info = source_info
                                st.session_state.generated = True
                                st.session_state.quill_key += 1
                                st.success("Synthesis complete! Switching to Result...")
                                st.session_state.nav_selection = "📝 Result"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                else:
                    st.warning("Please select at least one video.")

        with col_load:
            if st.session_state.search_object and st.button("Charger plus de résultats (+20)", key="btn_load_more"):
                with st.spinner("Récupération depuis YouTube..."):
                    # Use stored duration filter
                    dur_mode = st.session_state.get("filter_duration", "any")
                    new_results = workflow.load_more_videos(st.session_state.search_object, duration_mode=dur_mode)
                    
                    if not new_results:
                        st.warning("Plus aucun résultat trouvé.")
                    else:
                        # Append new results avoiding duplicates
                        current_urls = {v.watch_url for v in st.session_state.search_results}
                        count_added = 0
                        for v in new_results:
                            if v.watch_url not in current_urls:
                                st.session_state.search_results.append(v)
                                count_added += 1
                        
                        if count_added > 0:
                            st.success(f"{count_added} nouvelles vidéos chargées !")
                            st.rerun()
                        else:
                            st.info("Aucune nouvelle vidéo unique trouvée.")

# --- Tab 2: Manual ---
if st.session_state.nav_selection == "✍️ Manual":
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
            # Create a copy to iterate safely if modifying
            videos_to_remove = []
            
            for i, v in enumerate(st.session_state.manual_videos):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"**{i+1}. {v.title}**")
                    st.caption(f"{v.author}")
                with c2:
                    if st.button("🗑️", key=f"rm_v_{i}"):
                        videos_to_remove.append(i)
            
            # Process removal
            if videos_to_remove:
                # Remove in reverse order to maintain indices
                for idx in sorted(videos_to_remove, reverse=True):
                    st.session_state.manual_videos.pop(idx)
                st.rerun()
            
            if st.session_state.manual_videos:
                st.divider()
                if st.button("Clear List", key="btn_clear_manual", type="secondary"):
                    st.session_state.manual_videos = []
                    st.rerun()
                
                manual_title = st.text_input("Title for the Synthesis", value="Synthèse Manuelle")
                
                if st.button("Synthesize Manual List", key="btn_synth_manual", type="primary"):
                    with st.spinner("Synthesizing..."):
                        try:
                            # Construct a fake search object context if needed or just pass list
                            # reusing logic from search tab but for manual list
                            # We create a combined prompt for all videos
                            
                            # Note: The original code didn't actually have the synthesis button logic implemented 
                            # in this tab in the snippet provided! It just had the title input.
                            # I will implementing the call to workflow.synthesize_videos here.
                            
                            summary, title, source_info = workflow.synthesize_videos(st.session_state.manual_videos, manual_title)
                            
                            summary = clean_markdown_text(summary)
                            html_summary = markdown.markdown(summary, extensions=['extra'])
                            st.session_state.summary = html_summary
                            st.session_state.title = title
                            st.session_state.source_info = source_info
                            st.session_state.generated = True
                            st.session_state.quill_key += 1
                            st.success("Synthesis complete! Switching to Result...")
                            st.session_state.nav_selection = "📝 Result"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                 st.info("List is empty.")
        else:
            st.info("No videos added yet.")

# --- Tab 3: Local File ---
if st.session_state.nav_selection == "📁 Local File":
    st.header("Local MP4 File")
    file_path = st.text_input("Absolute Path to MP4 file")
    if st.button("Process File", key="btn_file"):
        if file_path and os.path.exists(file_path):
            with st.spinner("Processing file..."):
                try:
                    summary, title, source_info = workflow.process_video_path(file_path, summary_type)
                    # Clean markdown code blocks from LLM
                    summary = clean_markdown_text(summary)
                    # Convert to HTML for the editor
                    html_summary = markdown.markdown(summary, extensions=['extra'])
                    st.session_state.summary = html_summary
                    st.session_state.title = title
                    st.session_state.source_info = source_info
                    st.session_state.generated = True
                    st.session_state.quill_key += 1
                    st.session_state.quill_key += 1
                    st.success("Processing complete! Switching to Result...")
                    st.session_state.nav_selection = "📝 Result"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.error("File not found.")
if st.session_state.nav_selection == "📝 Result":
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
                    [{"align": []}],
                    [{"color": []}, {"background": []}],
                    ["clean"]
                ]
            )
            
            # Update session state if edited (Quill returns HTML)
            if content and content != st.session_state.summary:
                st.session_state.summary = content
            
            # Refine / Regenerate Section
            st.divider()
            with st.expander("✨ Refine / Regenerate", expanded=False):
                st.write("Modify the summary with AI.")
                
                st.write("Modify the summary with AI using these options:")
                
                c_size, c_tone = st.columns(2)
                c_fmt, c_lang = st.columns(2)
                
                with c_size:
                    opt_size = st.selectbox("Taille", ["(Maintener)", "Plus court", "Plus long"])
                with c_tone:
                    opt_tone = st.selectbox("Ton", ["(Maintener)", "Professionnel", "Formel", "Familier"])
                with c_fmt:
                    opt_fmt = st.selectbox("Format", ["(Maintener)", "Rapport Structuré", "Dissertation", "Article de Blog", "Liste à puces"])
                with c_lang:
                    opt_lang = st.selectbox("Langue", ["(Maintener)", "Anglais", "Espagnol", "Allemand", "Italien"])
                
                custom_instr = st.text_input("Instructions supplémentaires (Optionnel)", placeholder="Ex: Insiste sur les chiffres...")

                # Construct composite instruction
                instructions_list = []
                
                # Size mapping
                if opt_size == "Plus court": instructions_list.append("Rédige une version plus courte et concise.")
                elif opt_size == "Plus long": instructions_list.append("Développe davantage le texte avec plus de détails.")
                
                # Tone mapping
                if opt_tone == "Professionnel": instructions_list.append("Adopte un ton strictement professionnel et objectif.")
                elif opt_tone == "Formel": instructions_list.append("Utilise un style très formel et académique.")
                elif opt_tone == "Familier": instructions_list.append("Utilise un ton décontracté et accessible (vulgarisation).")
                
                # Format mapping
                if opt_fmt == "Rapport Structuré": instructions_list.append("Structure le texte comme un rapport professionnel (Intro, Analyse, Conclusion).")
                elif opt_fmt == "Dissertation": instructions_list.append("Adopte une structure de dissertation (Thèse, Antithèse, Synthèse).")
                elif opt_fmt == "Article de Blog": instructions_list.append("Transforme le texte en article de blog engageant (Titre accrocheur, paragraphes courts).")
                elif opt_fmt == "Liste à puces": instructions_list.append("Reformate le contenu principal sous forme de liste à puces.")
                
                # Lang mapping
                if opt_lang != "(Maintener)": instructions_list.append(f"Traduis le résultat final en {opt_lang}.")
                
                if custom_instr:
                    instructions_list.append(f"Consigne spécifique : {custom_instr}")
                
                refine_instructions = " ".join(instructions_list)
                
                if refine_instructions:
                    st.info(f"Consignes combinées : {refine_instructions}")

                if st.button("Refine Summary", key="btn_refine"):
                    if refine_instructions:
                        with st.spinner("Refining summary..."):
                            try:
                                # Convert current HTML back to text for the LLM context if needed, 
                                # but using the raw summary might be safer if we stored it separately.
                                # Here we use the current session state content (which is HTML from Quill)
                                # So we convert it to MD first for the LLM
                                current_md = md(st.session_state.summary, heading_style="ATX")
                                
                                new_summary_md = workflow.refine_summary(current_md, refine_instructions)
                                
                                # Clean and convert back to HTML for editor
                                new_summary_md = clean_markdown_text(new_summary_md)
                                new_summary_html = markdown.markdown(new_summary_md, extensions=['extra'])
                                
                                st.session_state.summary = new_summary_html
                                st.session_state.quill_key += 1
                                st.success("Summary refined!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error refining: {e}")
                    else:
                        st.warning("Please enter instructions.")

        with col_res_side:
            st.subheader("Actions")
            
            # Editable Title
            new_title = st.text_input("Document Title", value=st.session_state.title)
            if new_title != st.session_state.title:
                st.session_state.title = new_title
            
            st.divider()
            
            st.warning("⚠️ Editor content is HTML.")
            
            output_format = st.selectbox("Format d'export", ["md", "txt", "html", "pdf"], index=2)
            
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
            
            # Copy Code Section
            st.divider()
            with st.expander("📋 Copy Raw Markdown"):
                raw_md = md(st.session_state.summary, heading_style="ATX")
                st.code(raw_md, language="markdown")
    else:
        st.info("No summary generated yet. Please use one of the other tabs to generate a summary.")
