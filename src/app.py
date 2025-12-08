import streamlit as st
import os
from datetime import datetime
from workflow import WorkflowManager
from streamlit_quill import st_quill
import markdown
from markdownify import markdownify as md
from utils import clean_markdown_text, time_since, format_views
import html
import textwrap


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
    st.session_state.quill_key = 0
if "last_saved_path" not in st.session_state:
    st.session_state.last_saved_path = None


# Sidebar Configuration
st.sidebar.title("Configuration")
device = st.sidebar.selectbox("Device", ["cpu", "cuda"], index=0)
model = st.sidebar.selectbox("Whisper Model", ["tiny", "base", "small", "medium", "large"], index=0)
ollama_model = st.sidebar.text_input("Ollama Model", value="gemma3:4b")

summary_type = st.sidebar.selectbox("Summary Type", ["short", "medium", "long", "news"], index=2)

# Initialize Workflow Manager
# Initialize Workflow Manager
@st.cache_resource
def get_workflow(device, model, ollama_model, summary_type, version=1):
    from downloader import YouTubeAudioProcessor
    from transcriber import WhisperTranscriber
    from summarizer import Summarizer
    from exporter import Exporter
    from prompts import PromptManager
    from ollama import Client
    
    # OUTPUT_DIR is defined in constants at top of file or we can default it
    output_dir = "./summaries" 
    
    # 1. Initialize Dependencies
    processor = YouTubeAudioProcessor(output_dir="./audio_segments")
    transcriber = WhisperTranscriber(model_size=model, device=device)
    
    client = Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    prompt_manager = PromptManager()
    summarizer = Summarizer(client=client, model=ollama_model, prompt_manager=prompt_manager, summary_type=summary_type)
    
    exporter = Exporter(output_dir=output_dir)
    
    # 2. Inject into WorkflowManager
    return WorkflowManager(processor, transcriber, summarizer, exporter)

workflow = get_workflow(device, model, ollama_model, summary_type, version=6)

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
    # Wrap search input and button
    col_search_inner, col_btn_inner = st.columns([4, 1])
    
    # Callback for Enter key
    def submit_search():
        st.session_state.trigger_search = True

    with col_search_inner:
        query = st.text_input("Search Query", label_visibility="collapsed", placeholder="Search for videos...", on_change=submit_search, key="search_query_input")
    with col_btn_inner:
        if st.button("Search", type="primary"):
            st.session_state.trigger_search = True
            
    # Check trigger
    do_search = st.session_state.get("trigger_search", False)
    if do_search:
        # Reset immediately to avoid loops, but we need the query first
        # We'll handle the search execution later in the logic
        pass

    
    # --- Filters Session State Logic ---
    if "filter_sort" not in st.session_state:
        st.session_state.filter_sort = "Relevance"
    if "filter_date" not in st.session_state:
        st.session_state.filter_date = "Any"
    if "filter_dur" not in st.session_state:
        st.session_state.filter_dur = "Any"

    # Quick Filters (Actu Semaine / Actu Mois)
    st.markdown("##### ⚡ Filtres Rapides")
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        if st.button("📅 Actu Semaine", help="Trie par date et filtre sur cette semaine"):
            st.session_state.filter_sort = "Date"
            st.session_state.filter_date = "Week"
            st.session_state.trigger_search = True
            st.rerun()
    with col_q2:
        if st.button("📅 Actu Mois", help="Trie par date et filtre sur ce mois"):
            st.session_state.filter_sort = "Date"
            st.session_state.filter_date = "Month"
            st.session_state.trigger_search = True
            st.rerun()

    # Advanced Filters
    with st.expander("🛠️ Advanced Filters", expanded=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            sort_option = st.selectbox("Sort By", ["Relevance", "Date", "Views"], key="filter_sort")
        with col_f2:
            date_option = st.selectbox("Upload Date", ["Any", "Today", "Week", "Month", "Year"], key="filter_date")
        with col_f3:
            dur_option = st.selectbox("Duration", ["Any", "Short (<5m)", "Medium (5-20m)", "Long (>20m)"], key="filter_dur")
        with col_f4:
            type_options = st.multiselect("Type", ["Documentary", "Tutorial", "Conference", "Review", "News", "Tech"])
        
        exclude_terms = st.text_input("Mots à exclure (séparés par des espaces)", placeholder="Ex: shorts gaming")
        
        use_trusted_boost = st.checkbox("⭐ Prioriser les sources fiables (Arte, TED...)", value=True, help="Si coché, remonte les vidéos des chaînes de confiance en haut de la liste.")

    # Sort mapping must be done before we might need it for local sort
    sort_map = {"Relevance": "relevance", "Date": "date", "Views": "views"}
    date_map = {"Any": None, "Today": "today", "Week": "week", "Month": "month", "Year": "year"}
    dur_map = {"Any": "any", "Short (<5m)": "short", "Medium (5-20m)": "medium", "Long (>20m)": "long"}
    
    days_map = {"Any": None, "Today": 1, "Week": 7, "Month": 30, "Year": 365}
    days_limit = days_map[st.session_state.filter_date]
    final_sort = sort_map[st.session_state.filter_sort]
    final_date = date_map[st.session_state.filter_date]
    final_dur = dur_map[st.session_state.filter_dur]


    # Advisory Note
    st.info("💡 **Conseil :** Sélectionnez le nombre de vidéos en fonction du type de résumé souhaité :\n"
            "- **Short** : articles court 7 à 10 vidéos\n"
            "- **Medium** : articles moyen 4 à 6 vidéos\n"
            "- **Long** : articles long 1 à 3 vidéos (Attention, le traitement sera plus long)")

    if "search_object" not in st.session_state:
        st.session_state.search_object = None
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    # I can put the form *around* the columns? No, `st.columns` inside `st.form` is fine.
    # So I should start the form before line 80.
    
    pass
    if do_search:
        st.session_state.trigger_search = False

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
                st.session_state.active_categories = type_options
                st.session_state.use_boost = use_trusted_boost
                st.session_state.days_limit = days_limit
                
                st.session_state.search_results = workflow.get_search_results(st.session_state.search_object, duration_mode=final_dur, active_categories=type_options, enable_boost=use_trusted_boost, days_limit=days_limit)
                st.session_state.visible_count = 9
                # Reset selection on new search
                st.session_state.selected_video_urls = set()
        else:
            st.warning("Please enter a query.")

    if st.session_state.search_results:
        # Show all loaded results directly
        
        # Action Bar & Local Sort & Filters
        col_count, col_sort, col_actions = st.columns([2, 2, 4])
        
        with col_count:
             st.write(f"Résultats : {len(st.session_state.search_results)}")
             
        with col_sort:
            # Local sorting
            local_sort = st.selectbox("Trier par:", ["(Défaut)", "Date (Récent)", "Vues (Top)", "Durée (Long)"], label_visibility="collapsed")
            if local_sort == "Date (Récent)":
                st.session_state.search_results.sort(key=lambda x: x.publish_date or datetime.min, reverse=True)
            elif local_sort == "Vues (Top)":
                st.session_state.search_results.sort(key=lambda x: x.views if hasattr(x, 'views') else 0, reverse=True)
            elif local_sort == "Durée (Long)":
                st.session_state.search_results.sort(key=lambda x: x.length, reverse=True)
        
        # Initialize selection state if not present
        if "selected_video_urls" not in st.session_state:
            st.session_state.selected_video_urls = set()

        with col_actions:
            # Quick Select Buttons using columns for compact layout
            c_sel_3, c_sel_5, c_sel_all, c_desel_all = st.columns([1, 1, 1, 1])
            
            def select_top(n):
                top_n = st.session_state.search_results[:n]
                st.session_state.selected_video_urls.update(v.watch_url for v in top_n)
            
            with c_sel_3:
                if st.button("Top 3"):
                    select_top(3)
                    st.rerun()
            with c_sel_5:
                if st.button("Top 5"):
                    select_top(5)
                    st.rerun()
            with c_sel_all:
                if st.button("Tout"):
                    st.session_state.selected_video_urls = {v.watch_url for v in st.session_state.search_results}
                    st.rerun()
            with c_desel_all:
                if st.button("Aucun"):
                    st.session_state.selected_video_urls = set()
                    st.rerun()

        # Display videos in a grid
        cols = st.columns(3) # 3 cards per row
        
        for idx, v in enumerate(st.session_state.search_results):
            col = cols[idx % 3]
            with col:
                # Card Container
                with st.container():
                    # Data extraction with safe defaults
                    try:
                        # 1. Basic Info
                        title = getattr(v, 'title', 'Titre Inconnu') or 'Titre Inconnu'
                        author = getattr(v, 'author', 'Chaîne Inconnue') or 'Chaîne Inconnue'
                        
                        # 2. Description
                        desc = getattr(v, 'description', '')
                        if not desc: 
                            desc = "Pas de description disponible."
                        
                        # 3. Thumbnail
                        thumb_url = getattr(v, 'thumbnail_url', '')
                        if not thumb_url:
                            thumb_url = "https://via.placeholder.com/320x180?text=Pas+d'image"
                        
                        # 4. Metrics & Date
                        # OPTIMIZATION: Use _publish_date instead of publish_date to avoid blocking network call
                        # on every single video card.
                        pub_date = getattr(v, '_publish_date', None)
                        views = getattr(v, 'views', 0)
                        length = getattr(v, 'length', 0)
                        
                        # Safe Formatting
                        try:
                            rel_time = time_since(pub_date) if pub_date else "Date inconnue"
                        except Exception:
                            rel_time = "Date inconnue"
                            
                        try:
                            views_str = format_views(views)
                        except Exception:
                            views_str = "N/A"
                        
                        try:
                            if length and isinstance(length, (int, float)):
                                minutes = int(length // 60)
                                seconds = int(length % 60)
                                duration_str = f"{minutes}:{seconds:02d}"
                            else:
                                duration_str = "??:??"
                        except Exception:
                            duration_str = "??:??"

                        # HTML Safety
                        safe_title = html.escape(str(title))
                        safe_author = html.escape(str(author))
                        safe_desc = html.escape(str(desc))
                        
                        # Badge
                        badge_html = ""
                        # Robust check: use attribute OR re-verify with workflow (handles persistence issues)
                        is_boosted_attr = getattr(v, 'is_boosted', False)
                        is_boosted_check = workflow.is_channel_preferred(author, st.session_state.get("active_categories", []))
                        
                        if is_boosted_attr or (is_boosted_check and st.session_state.get("use_boost", True)):

                            badge_html = (
                                '<div style="position: absolute; top: 8px; right: 8px; '
                                'background-color: #FFD700; color: #000000; padding: 4px 8px; '
                                'border-radius: 4px; font-weight: bold; font-size: 0.75rem; '
                                'z-index: 10; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">'
                                '⭐ Recommandé</div>'
                            )

                        # Render Card
                        card_html = (
                            f'<div class="video-card" style="position: relative; border: 1px solid #444; border-radius: 8px; '
                            f'padding: 0; overflow: hidden; margin-bottom: 10px; background: #262730;">'
                            f'<div class="thumbnail-container" style="position: relative; width: 100%; height: 0; padding-bottom: 56.25%; background-color: #000;">'
                            f'{badge_html}'
                            f'<a href="{v.watch_url}" target="_blank" style="text-decoration:none;">'
                            f'<img src="{thumb_url}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; transition: opacity 0.3s;" alt="{safe_title}" title="Regarder sur YouTube" onerror="this.onerror=null; this.src=\'https://via.placeholder.com/320x180?text=Erreur+Image\';">'
                            f'</a>'
                            f'<span style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8); color: white; '
                            f'padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">{duration_str}</span>'
                            f'</div>'
                            f'<div style="padding: 10px;">'
                            f'<div style="font-weight: 600; font-size: 1rem; margin-bottom: 4px; line-height: 1.2; height: 1.2em; '
                            f'overflow: hidden; white-space: nowrap; text-overflow: ellipsis;" title="{safe_title}">'
                            f'<a href="{v.watch_url}" target="_blank" style="text-decoration:none; color: inherit;">{safe_title}</a></div>'
                            f'<div style="font-size: 0.8rem; color: #aaa; margin-bottom: 8px;">{safe_author} • {rel_time} • {views_str} vues</div>'
                            f'<div style="font-size: 0.85rem; color: #ddd; height: 3em; overflow: hidden; line-height: 1.5; '
                            f'display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">{safe_desc}</div>'
                            f'</div></div>'
                        )
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                    except Exception:
                        continue

                    
                    # Checkbox logic
                    is_selected = v.watch_url in st.session_state.selected_video_urls
                    if st.checkbox(f"Select", key=v.watch_url, value=is_selected):
                        st.session_state.selected_video_urls.add(v.watch_url)
                    else:
                        st.session_state.selected_video_urls.discard(v.watch_url)
        
        col_synth, col_load = st.columns([1, 1])
        
        # Collect selected video objects
        selected_videos = [v for v in st.session_state.search_results if v.watch_url in st.session_state.selected_video_urls]
        
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
                                st.session_state.nav_radio = "📝 Result"
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
                    act_cats = st.session_state.get("active_categories", [])
                    use_boost = st.session_state.get("use_boost", True)
                    days_limit = st.session_state.get("days_limit", None)
                    new_results = workflow.load_more_videos(st.session_state.search_object, duration_mode=dur_mode, active_categories=act_cats, enable_boost=use_boost, days_limit=days_limit)
                    
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
    st.header("Mode Manuel")
    
    tab_add, tab_list = st.tabs(["Ajouter des vidéos", "Liste de sélection"])
    
    with tab_add:
        st.subheader("Import")
        col_single, col_bulk = st.columns(2)
        
        with col_single:
            st.markdown("#### URL Unique")
            manual_url = st.text_input("YouTube URL", placeholder="https://youtube.com/...")
            if st.button("Ajouter", key="btn_add_manual"):
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

        with col_bulk:
            st.markdown("#### Import en masse")
            bulk_urls = st.text_area("URLs (une par ligne)", height=100, placeholder="https://...\nhttps://...")
            if st.button("Importer Tout", key="btn_bulk_manual"):
                if bulk_urls:
                    urls = [u.strip() for u in bulk_urls.split('\n') if u.strip()]
                    count_ok = 0
                    with st.status("Importing videos...") as status:
                        for u in urls:
                            status.write(f"Fetching {u}...")
                            try:
                                video = workflow.get_video_info(u)
                                if video:
                                    st.session_state.manual_videos.append(video)
                                    count_ok += 1
                            except:
                                status.write(f"Failed: {u}")
                        status.update(label=f"Import finished! {count_ok}/{len(urls)} videos added.", state="complete")
                    if count_ok > 0:
                        st.success(f"{count_ok} videos added!")

    with tab_list:
        st.subheader(f"Vidéos Sélectionnées ({len(st.session_state.manual_videos)})")
        
        if st.session_state.manual_videos:
             # Actions
            c_clear, c_title = st.columns([1, 3])
            with c_clear:
                 if st.button("🗑️ Tout effacer", key="btn_clear_manual", type="secondary"):
                    st.session_state.manual_videos = []
                    st.rerun()
            with c_title:
                manual_title = st.text_input("Titre de la synthèse", value="Synthèse Manuelle")

            st.divider()

            # Display as Cards (Grid)
            if st.session_state.manual_videos:
                cols_m = st.columns(3)
                videos_to_remove = []
                
                for idx, v in enumerate(st.session_state.manual_videos):
                    col = cols_m[idx % 3]
                    with col:
                         # Card Container
                        with st.container():
                            # Calculate relative time
                            rel_time = time_since(v.publish_date)
                            
                            # Format duration
                            duration_min = v.length // 60
                            duration_sec = v.length % 60
                            duration_str = f"{duration_min}:{duration_sec:02d}"

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
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("Retirer", key=f"rm_m_{idx}"):
                                videos_to_remove.append(idx)

                if videos_to_remove:
                    for idx in sorted(videos_to_remove, reverse=True):
                        st.session_state.manual_videos.pop(idx)
                    st.rerun()

                st.divider()
                if st.button("Lancer la Synthèse", key="btn_synth_manual_main", type="primary"):
                    with st.spinner("Synthesizing..."):
                        try:
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
                            st.session_state.nav_radio = "📝 Result"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("Aucune vidéo dans la liste. Ajoutez-en depuis l'onglet 'Ajouter des vidéos'.")

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
                    st.session_state.nav_radio = "📝 Result"
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

        with col_res_main:
            st.divider()
            
            # Preview / Editor Toggle
            view_mode = st.radio("Vue", ["Éditeur", "Aperçu (Lecture Seule)"], horizontal=True)

            if view_mode == "Éditeur":
                st.subheader("Éditeur de Résumé")
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
            else:
                 st.subheader("Aperçu du Résumé")
                 st.markdown(st.session_state.summary, unsafe_allow_html=True)

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
                    st.session_state.last_saved_path = saved_path
                    st.success(f"Saved to: {saved_path}")
                except Exception as e:
                    st.error(f"Error saving: {e}")

            # Show download button if a file has been saved
            if "last_saved_path" in st.session_state and st.session_state.last_saved_path:
                if os.path.exists(st.session_state.last_saved_path):
                    try:
                        with open(st.session_state.last_saved_path, "rb") as f:
                            file_bytes = f.read()
                        
                        file_ext = st.session_state.last_saved_path.split('.')[-1].lower()
                        mime_types = {
                            "md": "text/markdown",
                            "txt": "text/plain",
                            "html": "text/html", 
                            "pdf": "application/pdf"
                        }
                        
                        st.download_button(
                            label=f"⬇️ Télécharger {os.path.basename(st.session_state.last_saved_path)}",
                            data=file_bytes,
                            file_name=os.path.basename(st.session_state.last_saved_path),
                            mime=mime_types.get(file_ext, "application/octet-stream")
                        )
                    except Exception as e:
                        st.error(f"Error preparing download: {e}")

            
            # Direct PDF Download
            st.divider()
            if st.button("📥 Télécharger PDF Directement"):
                try:
                    pdf_bytes = workflow.get_pdf_bytes(st.session_state.summary, st.session_state.title, st.session_state.source_info)
                    
                    # Prepare file name
                    from utils import slugify
                    slug = slugify(st.session_state.title)
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    filename = f"{slug}_{date_str}.pdf"
                    
                    st.download_button(
                        label="Cliquez pour sauvegarder le PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")

            # Copy Code Section
            st.divider()
            with st.expander("📋 Copy Raw Markdown"):
                raw_md = md(st.session_state.summary, heading_style="ATX")
                st.code(raw_md, language="markdown")
    else:
        st.info("No summary generated yet. Please use one of the other tabs to generate a summary.")
