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
# Unified selection basket
if "selection_basket" not in st.session_state:
    # storing Video objects
    st.session_state.selection_basket = []


# Sidebar Configuration
st.sidebar.title("Configuration")
device = st.sidebar.selectbox("Device", ["cpu", "cuda"], index=0)
model = st.sidebar.selectbox("Whisper Model", ["tiny", "base", "small", "medium", "large"], index=0)
ollama_model = st.sidebar.text_input("Ollama Model", value="gemma3:4b")

summary_type = st.sidebar.selectbox("Summary Type", ["short", "medium", "long", "news"], index=2)

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
    st.session_state.nav_selection = "🔍 Sourcing"

# Navigation Menu
nav_options = ["🔍 Sourcing", "⚙️ Synthèse", "📝 Résultat"]
# Handle simple migration if user was on old tab name
if st.session_state.nav_selection not in nav_options:
    st.session_state.nav_selection = "🔍 Sourcing"

nav_selection = st.radio("Navigation", nav_options, index=nav_options.index(st.session_state.nav_selection), horizontal=True, label_visibility="collapsed", key="nav_radio")

# Sync session state if changed by user
if nav_selection != st.session_state.nav_selection:
    st.session_state.nav_selection = nav_selection
    st.rerun()

# --- Tab 1: Sourcing (Search + Manual) ---
if st.session_state.nav_selection == "🔍 Sourcing":
    # --- Top Section: Basket Preview ---
    n_items = len(st.session_state.selection_basket)
    
    col_basket_text, col_basket_btn = st.columns([3, 1])
    with col_basket_text:
        st.info(f"💾 **Mon Panier : {n_items} vidéos**")
    with col_basket_btn:
        if n_items > 0:
            def _go_synth():
                st.session_state.nav_selection = "⚙️ Synthèse"
                st.session_state["nav_radio"] = "⚙️ Synthèse"

            st.button("Aller à la Synthèse 👉", on_click=_go_synth, type="primary")

    st.header("Sourcing Vidéos")
    
    # --- Manual Input ---
    with st.expander("➕ Ajouter via URL (Youtube / Local)", expanded=False):
        tab_yt, tab_local = st.tabs(["YouTube URL", "Fichier Local"])
        
        with tab_yt:
            c_url, c_btn = st.columns([4, 1])
            with c_url:
                manual_url = st.text_input("YouTube URL", placeholder="https://youtube.com/...", label_visibility="collapsed")
            with c_btn:
                if st.button("Ajouter", key="btn_add_manual"):
                    if manual_url:
                        # Check if already in basket
                        existing_urls = {v.watch_url for v in st.session_state.selection_basket}
                        if manual_url in existing_urls:
                            st.warning("Cette vidéo est déjà dans votre sélection.")
                        else:
                            with st.spinner("Récupération des infos..."):
                                try:
                                    video = workflow.get_video_info(manual_url)
                                    if video:
                                        st.session_state.selection_basket.append(video)
                                        st.success(f"Ajouté : {video.title}")
                                        st.rerun() # Rerun to update basket count at top
                                    else:
                                        st.error("Impossible de récupérer les infos.")
                                except Exception as e:
                                    st.error(f"Erreur : {e}")
        
        with tab_local:
            local_path = st.text_input("Chemin absolu du fichier MP4/MP3")
            if st.button("Ajouter Fichier", key="btn_add_local"):
                    if local_path and os.path.exists(local_path):
                    # Create a dummy video object for local file
                    # We need a structure compatible with the rest
                        class LocalVideo:
                            def __init__(self, path):
                                self.title = os.path.basename(path)
                                self.author = "Local File"
                                self.watch_url = path # Use path as ID
                                self.thumbnail_url = "https://via.placeholder.com/320x180?text=Fichier+Local"
                                self.publish_date = datetime.now()
                                self.views = 0
                                self.length = 0
                                self.description = f"Fichier local : {path}"
                        
                        v = LocalVideo(local_path)
                        st.session_state.selection_basket.append(v)
                        st.success(f"Fichier ajouté : {v.title}")
                        st.rerun() # Rerun to update basket count
                    else:
                        st.error("Fichier introuvable.")

    st.divider()

    # --- Search Section ---
    st.subheader("🔍 Rechercher")
    
    # Wrap search input and button
    col_search_inner, col_btn_inner = st.columns([4, 1])
    
    # Callback for Enter key
    def submit_search():
        st.session_state.trigger_search = True

    with col_search_inner:
        query = st.text_input("Search Query", label_visibility="collapsed", placeholder="Sujet, mots-clés...", on_change=submit_search, key="search_query_input")
    with col_btn_inner:
        if st.button("Rechercher", type="primary"):
            st.session_state.trigger_search = True
            
    # Check trigger
    do_search = st.session_state.get("trigger_search", False)
    
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

    # Sort mapping
    sort_map = {"Relevance": "relevance", "Date": "date", "Views": "views"}
    date_map = {"Any": None, "Today": "today", "Week": "week", "Month": "month", "Year": "year"}
    dur_map = {"Any": "any", "Short (<5m)": "short", "Medium (5-20m)": "medium", "Long (>20m)": "long"}
    
    days_map = {"Any": None, "Today": 1, "Week": 7, "Month": 30, "Year": 365}
    days_limit = days_map[st.session_state.filter_date]
    final_sort = sort_map[st.session_state.filter_sort]
    final_date = date_map[st.session_state.filter_date]
    final_dur = dur_map[st.session_state.filter_dur]

    # Advisory Note
    st.caption("Conseil : Sélectionnez des vidéos pour les ajouter à votre panier de synthèse.")

    if "search_object" not in st.session_state:
        st.session_state.search_object = None
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    
    if do_search:
        st.session_state.trigger_search = False

        if query:
            with st.spinner("Searching..."):
                final_query = query
                if type_options:
                    final_query += " " + " ".join(type_options)
                
                st.session_state.search_object = workflow.init_search(final_query, sort_by=final_sort, upload_date=final_date, exclude_terms=exclude_terms)
                st.session_state.filter_duration = final_dur
                st.session_state.active_categories = type_options
                st.session_state.use_boost = use_trusted_boost
                st.session_state.days_limit = days_limit
                
                st.session_state.search_results = workflow.get_search_results(st.session_state.search_object, duration_mode=final_dur, active_categories=type_options, enable_boost=use_trusted_boost, days_limit=days_limit)
                st.session_state.visible_count = 9
                
        else:
            st.warning("Please enter a query.")

    if st.session_state.search_results:
        # Action Bar & Local Sort
        col_count, col_sort = st.columns([2, 2])
        
        with col_count:
             st.write(f"Résultats trouvés : {len(st.session_state.search_results)}")
             
        with col_sort:
            local_sort = st.selectbox("Trier par:", ["(Défaut)", "Date (Récent)", "Vues (Top)", "Durée (Long)"], label_visibility="collapsed")
            if local_sort == "Date (Récent)":
                st.session_state.search_results.sort(key=lambda x: x.publish_date or datetime.min, reverse=True)
            elif local_sort == "Vues (Top)":
                st.session_state.search_results.sort(key=lambda x: x.views if hasattr(x, 'views') else 0, reverse=True)
            elif local_sort == "Durée (Long)":
                st.session_state.search_results.sort(key=lambda x: x.length, reverse=True)
        
        # Display videos in a grid
        cols = st.columns(3) 
        
        # Identify what's already in basket for UI feedback
        basket_ids = {v.watch_url for v in st.session_state.selection_basket}
        
        for idx, v in enumerate(st.session_state.search_results):
            col = cols[idx % 3]
            with col:
                with st.container():
                    # --- Card Rendering (Simplified reuse) ---
                    try:
                        # Prioritize explicit attributes (pre-fetched), fall back to properties (might trigger lazy load)
                        title = getattr(v, 'title_attr', None) or getattr(v, 'title', 'Titre Inconnu')
                        author = getattr(v, 'author_attr', None) or getattr(v, 'author', 'Chaîne Inconnue')
                        thumb_url = getattr(v, 'thumb_attr', None) or getattr(v, 'thumbnail_url', '') or "https://via.placeholder.com/320x180?text=No+Image"
                        pub_date = getattr(v, 'publish_date_attr', None) or getattr(v, 'publish_date', None)
                        views = getattr(v, 'views_attr', None) or getattr(v, 'views', 0)
                        length = getattr(v, 'length_attr', None) or getattr(v, 'length', 0)
                        description = getattr(v, 'description_attr', None) or getattr(v, 'description', '')
                        
                        try: rel_time = time_since(pub_date) if pub_date else "Date inconnue"
                        except: rel_time = "Date inconnue"
                        try: views_str = format_views(views)
                        except: views_str = "N/A"
                        try:
                            if length and isinstance(length, (int, float)):
                                duration_str = f"{int(length // 60)}:{int(length % 60):02d}"
                            else: duration_str = "??:??"
                        except: duration_str = "??:??"

                        safe_title = html.escape(str(title))
                        safe_author = html.escape(str(author))
                        safe_thumb = html.escape(str(thumb_url))
                        safe_url = html.escape(str(v.watch_url))
                        safe_desc = html.escape(str(description))
                        
                        # Badge logic
                        badge_html = ""
                        # Check persistent boosted status
                        is_boosted_attr = getattr(v, 'is_boosted', False)
                        # Re-check preference if needed (redundant but safe)
                        is_boosted_check = workflow.is_channel_preferred(author, st.session_state.get("active_categories", []))
                        
                        if is_boosted_attr or (is_boosted_check and st.session_state.get("use_boost", True)):
                            badge_html = '<div style="position: absolute; top: 8px; right: 8px; background-color: #FFD700; color: black; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.7em; z-index: 10;">Recommandé</div>'

                        # Render Card HTML
                        # Using distinct class for debugging if needed
                        card_html = f"""<div style="background: #262730; border-radius: 8px; overflow: hidden; margin-bottom: 20px; border: 1px solid #444; display: flex; flex-direction: column; height: 100%;">
<div style="position: relative; width: 100%; padding-top: 56.25%;">
{badge_html}
<a href="{safe_url}" target="_blank" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: block;">
<img src="{safe_thumb}" style="width: 100%; height: 100%; object-fit: cover; border: none;" alt="{safe_title}" />
</a>
<span style="position: absolute; bottom: 5px; right: 5px; background: rgba(0,0,0,0.8); color: white; padding: 2px 4px; border-radius: 4px; font-size: 0.75em; pointer-events: none;">{duration_str}</span>
</div>
<div style="padding: 12px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between;">
<div style="margin-bottom: 8px;">
<a href="{safe_url}" target="_blank" style="text-decoration:none; color: inherit; font-weight: 600; font-size: 1em; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
{safe_title}
</a>
</div>
<div style="font-size: 0.85em; color: #b0b0b0;">
<div>{safe_author}</div>
<div>{views_str} • {rel_time}</div>
<div style="margin-top: 8px; font-size: 0.95em; color: #ddd; max-height: 80px; overflow-y: auto; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 4px;">
{safe_desc}
</div>
</div>
</div>
</div>"""
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Render error: {e}")
                        continue

                    # Action Button
                    is_in_basket = v.watch_url in basket_ids
                    
                    if is_in_basket:
                        st.button("✅ Ajouté", key=f"btn_added_{v.watch_url}_{idx}", disabled=True)
                    else:
                        if st.button("Ajouter au panier", key=f"btn_add_{v.watch_url}_{idx}"):
                            st.session_state.selection_basket.append(v)
                            st.rerun()

        # Load More
        col_load_more, _ = st.columns([1, 2])
        with col_load_more:
            if st.session_state.search_object and st.button("Charger plus (+20)", key="btn_load_more"):
                with st.spinner("Récupération..."):
                    dur_mode = st.session_state.get("filter_duration", "any")
                    act_cats = st.session_state.get("active_categories", [])
                    use_boost = st.session_state.get("use_boost", True)
                    days_limit = st.session_state.get("days_limit", None)
                    new_results = workflow.load_more_videos(st.session_state.search_object, duration_mode=dur_mode, active_categories=act_cats, enable_boost=use_boost, days_limit=days_limit)
                    
                    if new_results:
                         current_urls = {v.watch_url for v in st.session_state.search_results}
                         for v in new_results:
                             if v.watch_url not in current_urls:
                                 st.session_state.search_results.append(v)
                         st.rerun()
                    else:
                        st.warning("Plus de résultats.")

# --- Tab 2: Synthèse (Review) ---
if st.session_state.nav_selection == "⚙️ Synthèse":
    st.header("⚙️ Synthèse et Enrichissement")
    
    n_basket = len(st.session_state.selection_basket)
    
    col_list, col_ctx = st.columns([2, 1])
    
    with col_list:
        st.subheader(f"Vidéos sélectionnées ({n_basket})")
        if n_basket > 0:
            # Action de suppression globale
            if st.button("Tout vider", key="btn_clear_basket", type="secondary"):
                st.session_state.selection_basket = []
                st.rerun()
            
            # List videos
            videos_to_remove = []
            for idx, v in enumerate(st.session_state.selection_basket):
                with st.container():
                     c_thumb, c_info, c_del = st.columns([1, 3, 0.5])
                     with c_thumb:
                         st.image(v.thumbnail_url, use_column_width=True)
                     with c_info:
                         st.markdown(f"**{v.title}**")
                         st.caption(f"{v.author} • {time_since(v.publish_date)}")
                     with c_del:
                         if st.button("❌", key=f"del_bsk_{idx}_{v.watch_url}"):
                             videos_to_remove.append(idx)
                st.divider()
             
            if videos_to_remove:
                for idx in sorted(videos_to_remove, reverse=True):
                    st.session_state.selection_basket.pop(idx)
                st.rerun()
        else:
            st.info("Votre panier est vide. Allez dans l'onglet 'Sourcing' pour ajouter des vidéos.")
            if st.button("Aller au Sourcing"):
                st.session_state.nav_selection = "🔍 Sourcing"
                st.rerun()

    with col_ctx:
        st.subheader("Configuration de la Synthèse")
        
        with st.form("form_synthesis"):
            st.markdown("#### 1. Contexte")
            context_input = st.text_area(
                "Sujet ou Angle de synthèse",
                placeholder="Ex: Fais une synthèse focalisée sur les impacts économiques de cette technologie...",
                height=150,
                help="Donnez une direction au modèle pour la synthèse."
            )
            
            st.markdown("#### 2. Options")
            custom_title = st.text_input("Titre du document final", value="Synthèse Vidéo")
            
            submitted = st.form_submit_button("🚀 Lancer la Synthèse", type="primary")
            
            if submitted:
                if n_basket == 0:
                    st.error("Veuillez sélectionner au moins une vidéo.")
                elif not context_input.strip():
                    st.error("Veuillez définir un sujet ou un contexte pour guider la synthèse.")
                else:
                    with st.spinner("Génération de la synthèse en cours..."):
                        try:
                            # Use the unified synthesize_videos method
                            # It expects (videos, subject_or_title)
                            # But here we have both a Subject (context) AND a Title.
                            # The current `synthesize_videos` implementation takes `search_query` as the second arg if it's from search, 
                            # or `manual_title` if from manual.
                            # We should probably pass the context as the 'query' so the LLM knows what to focus on.
                            # And we set the title explicitly afterwards.
                            
                            summary, title, source_info = workflow.synthesize_videos(
                                st.session_state.selection_basket, 
                                context_input 
                            )
                            
                            # Post-process
                            summary = clean_markdown_text(summary)
                            html_summary = markdown.markdown(summary, extensions=['extra'])
                            
                            # Update State
                            st.session_state.summary = html_summary
                            st.session_state.title = custom_title if custom_title else title
                            st.session_state.source_info = source_info
                            st.session_state.generated = True
                            st.session_state.quill_key += 1
                            
                            st.success("Synthèse terminée !")
                            st.session_state.nav_selection = "📝 Résultat"
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Une erreur est survenue : {e}")

if st.session_state.nav_selection == "📝 Résultat" or st.session_state.nav_selection == "📝 Result":
    if st.session_state.generated:
        st.header("📝 Result (Editable)")
        
        col_res_main, col_res_side = st.columns([3, 1])
        
        with col_res_main:
            # Refine / Regenerate Section
            st.divider()
            with st.expander("✨ Refine / Regenerate", expanded=False):
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
