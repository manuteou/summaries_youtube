import streamlit as st
import os
from datetime import datetime
from workflow import WorkflowManager
from streamlit_quill import st_quill
import markdown
from markdownify import markdownify as md
from utils import clean_markdown_text, time_since, format_views
from database import get_database, Project, Tag, Synthesis
from analyzer import get_analyzer, ExtractedFact, Contradiction
from scheduler import get_scheduler, get_alert_manager, ScheduledTask, Alert
from analytics import get_analytics
import html
import textwrap

# Page config
st.set_page_config(page_title="SynthetIA", page_icon="📝", layout="wide")

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

# UX Improvements: History
if "synthesis_history" not in st.session_state:
    st.session_state.synthesis_history = []  # List of {title, summary, timestamp, source_info}

# UX Improvements: Accessibility settings
if "theme_light" not in st.session_state:
    st.session_state.theme_light = False
if "font_size" not in st.session_state:
    st.session_state.font_size = "Normal"

# UX Improvements: Progress tracking
if "synthesis_step" not in st.session_state:
    st.session_state.synthesis_step = 0  # 0=idle, 1=download, 2=transcribe, 3=analyze, 4=write
if "synthesis_progress" not in st.session_state:
    st.session_state.synthesis_progress = 0.0


# Sidebar Configuration
st.sidebar.title("Configuration")
device = st.sidebar.selectbox("Device", ["cpu", "cuda"], index=0)
model = st.sidebar.selectbox("Whisper Model", ["tiny", "base", "small", "medium", "large"], index=0)

# --- Accessibility Controls ---
st.sidebar.divider()
st.sidebar.subheader("♿ Accessibilité")
st.session_state.theme_light = st.sidebar.toggle("☀️ Mode Clair", value=st.session_state.theme_light)
st.session_state.font_size = st.sidebar.select_slider(
    "Taille police", 
    ["Petit", "Normal", "Grand"], 
    value=st.session_state.font_size
)

# Apply theme/font classes via CSS injection
theme_class = "light-mode" if st.session_state.theme_light else ""
font_class = {"Petit": "font-small", "Normal": "", "Grand": "font-large"}.get(st.session_state.font_size, "")
if theme_class or font_class:
    st.markdown(f'<script>document.body.classList.add("{theme_class}", "{font_class}");</script>', unsafe_allow_html=True)

# --- Synthesis History ---
st.sidebar.divider()
st.sidebar.subheader("📚 Historique")
if st.session_state.synthesis_history:
    for idx, item in enumerate(st.session_state.synthesis_history[-5:][::-1]):
        with st.sidebar.container():
            st.markdown(f'''
            <div class="history-item" onclick="">
                <div class="history-item-title">{item.get("title", "Sans titre")[:30]}...</div>
                <div class="history-item-meta">{item.get("timestamp", "")}</div>
            </div>
            ''', unsafe_allow_html=True)
            if st.sidebar.button(f"↩️ Recharger", key=f"reload_hist_{idx}", use_container_width=True):
                st.session_state.summary = item.get("summary", "")
                st.session_state.title = item.get("title", "")
                st.session_state.source_info = item.get("source_info", [])
                st.session_state.generated = True
                st.session_state.nav_selection = "📝 Résultat"
                st.rerun()
else:
    st.sidebar.caption("Aucune synthèse récente")

# Récupérer la liste des modèles Ollama disponibles
@st.cache_data(ttl=60)  # Cache pendant 60 secondes
def get_ollama_models():
    """Récupère la liste des modèles Ollama installés localement."""
    import requests
    try:
        response = requests.get(
            f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/tags",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return sorted(models) if models else ["gemma3:4b"]
        return ["gemma3:4b"]
    except Exception:
        return ["gemma3:4b"]

ollama_models = get_ollama_models()
# Trouver l'index du modèle par défaut
default_model = "gemma3:4b"
default_index = ollama_models.index(default_model) if default_model in ollama_models else 0
ollama_model = st.sidebar.selectbox("Ollama Model", ollama_models, index=default_index)

# Le type de document est maintenant défini dans l'onglet Synthèse
type_map = {
    "Synthèse Courte": "short", 
    "Synthèse Moyenne": "medium", 
    "Synthèse Longue": "long", 
    "Actualité/News": "news",
    "Compte-Rendu (Meeting)": "meeting"
}
# Valeur par défaut pour initialiser le workflow
default_summary_type = "long"

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

workflow = get_workflow(device, model, ollama_model, default_summary_type, version=11)

# Branding avec logo
logo_path = os.path.join(os.path.dirname(__file__), "images", "synthetIA_logo.png")
if os.path.exists(logo_path):
    import base64
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <img src="data:image/png;base64,{logo_base64}" style="max-width: 350px; width: 100%; height: auto;" />
        <p style="font-size: 1.2rem; color: #A3A8B8; margin-top: 5px;">L'essentiel de vos vidéos, synthétisé.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="font-size: 4rem; background: linear-gradient(90deg, #FF4B4B, #FF914D); background-clip: text; -webkit-background-clip: text; color: transparent; -webkit-text-fill-color: transparent; font-weight: 800; display: inline-block; margin-bottom: 0;">SynthetIA</h1>
        <p style="font-size: 1.2rem; color: #A3A8B8; margin-top: 0px;">L'essentiel de vos vidéos, synthétisé.</p>
    </div>
    """, unsafe_allow_html=True)

# Tabs
# Navigation
if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "🔍 Sourcing"

# Navigation Menu
nav_options = ["🔍 Sourcing", "⚙️ Synthèse", "📝 Résultat", "📂 Projets", "🔬 Analyse", "🤖 Automation", "📊 Stats"]
# Handle simple migration if user was on old tab name
if st.session_state.nav_selection not in nav_options:
    st.session_state.nav_selection = "🔍 Sourcing"

# Use session_state to control radio value (no index parameter to avoid conflict)
if "nav_radio" not in st.session_state:
    st.session_state.nav_radio = st.session_state.nav_selection

# --- Visual Navigation Stepper ---
def render_nav_stepper():
    """Render a visual stepper for navigation with completion status."""
    current_idx = nav_options.index(st.session_state.nav_selection) if st.session_state.nav_selection in nav_options else 0
    has_basket = len(st.session_state.selection_basket) > 0
    has_result = st.session_state.generated
    
    steps_html = '<div class="nav-stepper">'
    
    for idx, option in enumerate(nav_options):
        # Determine step status
        if idx < current_idx:
            status = "completed"
            icon = "✓"
        elif idx == current_idx:
            status = "active"
            icon = str(idx + 1)
        else:
            status = "pending"
            icon = str(idx + 1)
        
        # Special logic for completion indicators
        if idx == 0 and has_basket:
            status = "completed" if current_idx > 0 else status
        if idx == 1 and has_result:
            status = "completed" if current_idx > 1 else status
        
        label = option.split(" ", 1)[1] if " " in option else option
        steps_html += f'''
        <div class="nav-step {status}" data-nav="{idx}">
            <span class="nav-step-icon">{option.split()[0]}</span>
            <span>{label}</span>
        </div>
        '''
        if idx < len(nav_options) - 1:
            steps_html += '<span class="nav-step-arrow">→</span>'
    
    steps_html += '</div>'
    st.markdown(steps_html, unsafe_allow_html=True)

render_nav_stepper()

# Hidden radio for actual navigation (still functional)
nav_selection = st.radio("Navigation", nav_options, horizontal=True, label_visibility="collapsed", key="nav_radio")

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
                st.session_state.nav_radio = "⚙️ Synthèse"

            st.button("Aller à la Synthèse 👉", on_click=_go_synth, type="primary")

    st.markdown("""
    <div style="background: linear-gradient(90deg, rgba(255, 75, 75, 0.1), rgba(255, 145, 77, 0.1)); padding: 15px; border-radius: 10px; border-left: 5px solid #FF4B4B; margin-bottom: 20px;">
        <h2 style="margin: 0; padding: 0; font-weight: 700; color: #FAFAFA;">
            🔍 Sourcing De Vos Vidéos <span style="font-weight: 300; opacity: 0.8;">& Importation</span> 📥
        </h2>
        <p style="margin: 5px 0 0 0; color: #A3A8B8; font-size: 0.9em;">
            Recherchez du contenu pertinent sur YouTube 🎥 ou importez vos propres fichiers 📂 pour démarrer.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
            uploaded_file = st.file_uploader("Choisir un fichier vidéo (MP4, MP3, M4A)", type=["mp4", "mp3", "m4a", "mov", "avi"])
            
            if uploaded_file is not None:
                # Button to confirm adding to basket
                if st.button("Ajouter ce fichier", key="btn_add_local_upload"):
                    # Save file to temp dir
                    temp_dir = "./temp_videos"
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    file_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Create LocalVideo object
                    class LocalVideo:
                        def __init__(self, path, filename):
                            self.title = filename
                            self.author = "Fichier Local"
                            self.watch_url = os.path.abspath(path) # Use absolute path as ID/URL
                            self.thumbnail_url = "https://via.placeholder.com/320x180.png/333333/cccccc?text=Fichier+Local"
                            self.publish_date = datetime.now()
                            self.views = 0
                            self.length = 0
                            self.description = f"Fichier importé : {path}"
                            # UI attributes
                            self.title_attr = self.title
                            self.author_attr = self.author
                            self.thumb_attr = self.thumbnail_url
                            self.description_attr = self.description
                    
                    v = LocalVideo(file_path, uploaded_file.name)
                    
                    # Check if already in basket
                    if any(existing.watch_url == v.watch_url for existing in st.session_state.selection_basket):
                         st.warning("Ce fichier est déjà dans votre panier.")
                    else:
                        st.session_state.selection_basket.append(v)
                        st.success(f"Fichier ajouté : {v.title}")
                        st.rerun()

    st.divider()

    # --- Search Section ---
    st.subheader("🔍 Rechercher Sur YouTube")
    
    # Keyboard Shortcut: Ctrl+Enter for search
    st.markdown('''
    <script>
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            // Find and click the search button
            const searchBtn = document.querySelector('button[kind="primary"]');
            if (searchBtn) searchBtn.click();
        }
    });
    </script>
    <p style="font-size: 0.8rem; color: #666; margin-bottom: 10px;">💡 Astuce: Appuyez sur <kbd style="background: #333; padding: 2px 6px; border-radius: 4px;">Ctrl</kbd> + <kbd style="background: #333; padding: 2px 6px; border-radius: 4px;">Enter</kbd> pour lancer la recherche</p>
    ''', unsafe_allow_html=True)
    
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
                        # Render Card HTML (Premium Design)
                        # Render Card HTML (Premium Design)
                        card_html = f"""
<div class="video-card">
<div style="position: relative; width: 100%; aspect-ratio: 16/9; overflow: hidden;">
{badge_html}
<a href="{safe_url}" target="_blank">
<img src="{safe_thumb}" alt="{safe_title}" loading="lazy" />
</a>
<span style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8); color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; font-weight: 600;">{duration_str}</span>
</div>
<div class="card-content">
<a href="{safe_url}" target="_blank" class="card-title">
{safe_title}
</a>
<div style="font-size: 0.85em; color: #A3A8B8; margin-bottom: 8px;">
<span style="color: #FF914D; font-weight: 500;">{safe_author}</span> • {views_str} • {rel_time}
</div>
<div style="font-size: 0.9em; color: #D3D3D3; line-height: 1.4; overflow-y: auto; flex-grow: 1; mask-image: linear-gradient(to bottom, black 80%, transparent 100%);">
{safe_desc[:120]}...
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
                c_thumb, c_info, c_del = st.columns([1, 3, 0.5])
                with c_thumb:
                    st.image(v.thumbnail_url, width='stretch')
                with c_info:
                    st.markdown(f"**{v.title}**")
                    st.caption(f"{v.author} • {time_since(v.publish_date)}")
                    
                    description = getattr(v, 'description_attr', None) or getattr(v, 'description', '')
                    safe_desc = html.escape(str(description))
                    st.markdown(f"""
                    <div style="font-size: 0.9em; color: #D3D3D3; max-height: 120px; overflow-y: auto; background: rgba(255,255,255,0.05); padding: 8px; border-radius: 6px; margin-top: 8px; border: 1px solid rgba(255,255,255,0.1);">
                        {safe_desc}
                    </div>
                    """, unsafe_allow_html=True)
                with c_del:
                    if st.button("❌", key=f"del_bsk_{idx}_{v.watch_url}"):
                        videos_to_remove.append(idx)
                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
             
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
            
            # Type de document (déplacé depuis la sidebar)
            summary_type_disp = st.selectbox(
                "Type de document",
                ["Synthèse Courte", "Synthèse Moyenne", "Synthèse Longue", "Actualité/News", "Compte-Rendu (Meeting)"],
                index=2,
                help="Choisissez le format de synthèse adapté à vos besoins."
            )
            
            custom_title = st.text_input("Titre du document final", value="Synthèse Vidéo")
            
            submitted = st.form_submit_button("🚀 Lancer la Synthèse", type="primary")
            
            if submitted:
                if n_basket == 0:
                    st.error("Veuillez sélectionner au moins une vidéo.")
                elif not context_input.strip():
                    st.error("Veuillez définir un sujet ou un contexte pour guider la synthèse.")
                else:
                    # --- Visual Progress Component ---
                    progress_placeholder = st.empty()
                    status_placeholder = st.empty()
                    
                    def render_progress_steps(current_step, estimated_time=None):
                        """Render the synthesis progress UI."""
                        steps = [
                            ("📥", "Téléchargement"),
                            ("🎙️", "Transcription"),
                            ("🧠", "Analyse"),
                            ("✍️", "Rédaction")
                        ]
                        
                        html = '<div class="synthesis-progress">'
                        for idx, (icon, label) in enumerate(steps):
                            if idx < current_step:
                                status = "completed"
                                circle_content = "✓"
                            elif idx == current_step:
                                status = "active"
                                circle_content = icon
                            else:
                                status = "pending"
                                circle_content = str(idx + 1)
                            
                            html += f'''
                            <div class="step-item {status}">
                                <div class="step-circle {status}">{circle_content}</div>
                                <div class="step-label">{label}</div>
                            </div>
                            '''
                            if idx < len(steps) - 1:
                                connector_status = "completed" if idx < current_step else ("active" if idx == current_step - 1 else "")
                                html += f'<div class="step-connector {connector_status}"></div>'
                        
                        html += '</div>'
                        
                        # Progress bar
                        progress_pct = (current_step / 4) * 100
                        html += f'''
                        <div class="progress-bar-container">
                            <div class="progress-bar-fill" style="width: {progress_pct}%"></div>
                        </div>
                        '''
                        
                        if estimated_time:
                            html += f'<div class="estimated-time">⏱️ Temps estimé : <strong>{estimated_time}</strong></div>'
                        
                        return html
                    
                    # Calculate estimated time based on multiple factors
                    n_videos = len(st.session_state.selection_basket)
                    total_duration = sum(getattr(v, 'length', 300) for v in st.session_state.selection_basket)
                    
                    # Get summary type first (needed for time estimation)
                    selected_summary_type = type_map[summary_type_disp]
                    
                    # Base: transcription time (depends on whisper model and GPU)
                    # RTX 5070 with CUDA: ~0.1x realtime for "base", ~0.05x for "tiny"
                    # CPU: ~0.5x realtime for "base"
                    whisper_factors = {"tiny": 0.03, "base": 0.05, "small": 0.1, "medium": 0.2, "large": 0.4}
                    whisper_factor = whisper_factors.get(model, 0.1)
                    if device == "cpu":
                        whisper_factor *= 5  # CPU is ~5x slower
                    transcription_time = total_duration * whisper_factor
                    
                    # LLM processing time (depends on summary type and text length)
                    # Calibrated from real data: 3 videos medium = ~292s = ~90s/video
                    # short=fast, long=slow, meeting=medium
                    llm_factors = {"short": 0.5, "medium": 1.0, "long": 2.0, "news": 0.8, "meeting": 1.5}
                    llm_factor = llm_factors.get(selected_summary_type, 1.0)
                    # ~90s per video for LLM processing (base), adjusted by factor
                    llm_time = n_videos * 90 * llm_factor
                    
                    # Download time: ~5s per video
                    download_time = n_videos * 5
                    
                    # Total estimate
                    est_seconds = int(download_time + transcription_time + llm_time)
                    
                    # Format nicely
                    if est_seconds >= 60:
                        est_time = f"{est_seconds // 60}m {est_seconds % 60}s"
                    else:
                        est_time = f"{est_seconds}s"
                    
                    try:
                        # Step 1: Download
                        progress_placeholder.markdown(render_progress_steps(0, est_time), unsafe_allow_html=True)
                        status_placeholder.info("📥 Téléchargement des fichiers audio...")
                        
                        # Mettre à jour le type de synthèse du summarizer
                        workflow.summarizer.summary_type = selected_summary_type
                        
                        # Step 2: Transcription (in synthesize_videos)
                        progress_placeholder.markdown(render_progress_steps(1, est_time), unsafe_allow_html=True)
                        status_placeholder.info("🎙️ Transcription en cours...")
                        
                        # Step 3: Analysis 
                        progress_placeholder.markdown(render_progress_steps(2, est_time), unsafe_allow_html=True)
                        status_placeholder.info("🧠 Analyse du contenu...")
                        
                        summary, title, source_info = workflow.synthesize_videos(
                            st.session_state.selection_basket, 
                            context_input,
                            title_override=custom_title
                        )
                        
                        # Step 4: Writing
                        progress_placeholder.markdown(render_progress_steps(3, est_time), unsafe_allow_html=True)
                        status_placeholder.info("✍️ Rédaction finale...")
                        
                        # Post-process
                        summary = clean_markdown_text(summary)
                        html_summary = markdown.markdown(summary, extensions=['extra'])
                        
                        # Complete!
                        progress_placeholder.markdown(render_progress_steps(4), unsafe_allow_html=True)
                        status_placeholder.success("✅ Synthèse terminée !")
                        
                        # Update State
                        st.session_state.summary = html_summary
                        st.session_state.title = custom_title if custom_title else title
                        st.session_state.source_info = source_info
                        st.session_state.generated = True
                        st.session_state.quill_key += 1
                        
                        # Save to history (session)
                        st.session_state.synthesis_history.append({
                            "title": st.session_state.title,
                            "summary": html_summary,
                            "source_info": source_info,
                            "timestamp": datetime.now().strftime("%d/%m %H:%M")
                        })
                        
                        # Save to database (persistent)
                        try:
                            db = get_database()
                            project_id = st.session_state.get("selected_project_id", 1)
                            db.save_synthesis(
                                title=st.session_state.title,
                                summary=html_summary,
                                sources=source_info,
                                project_id=project_id,
                                summary_type=selected_summary_type
                            )
                        except Exception as db_error:
                            print(f"DB save error: {db_error}")
                        
                        # Track analytics
                        try:
                            analytics = get_analytics()
                            total_duration = sum(getattr(v, 'length', 300) for v in st.session_state.selection_basket)
                            word_count = len(html_summary.split())
                            analytics.track_synthesis(
                                num_videos=len(st.session_state.selection_basket),
                                video_duration_sec=total_duration,
                                word_count=word_count,
                                summary_type=selected_summary_type,
                                topic=context_input[:50] if context_input else None
                            )
                        except Exception as analytics_error:
                            print(f"Analytics error: {analytics_error}")
                        
                        # Small delay to show success message
                        import time
                        time.sleep(1)
                        
                        st.session_state.nav_selection = "📝 Résultat"
                        st.rerun()
                        
                    except Exception as e:
                        progress_placeholder.empty()
                        status_placeholder.error(f"Une erreur est survenue : {e}")
                        # Print to terminal for debugging
                        import traceback
                        print("=" * 50)
                        print("ERREUR SYNTHÈSE:")
                        print("=" * 50)
                        traceback.print_exc()
                        print("=" * 50)
                        st.code(traceback.format_exc(), language="text")

if st.session_state.nav_selection == "📝 Résultat" or st.session_state.nav_selection == "📝 Result":
    if st.session_state.generated:
        st.header("📝 Result (Editable)")
        
        col_res_main, col_res_side = st.columns([3, 1])
        
        with col_res_main:
            # Refine / Regenerate Section
            st.divider()
            with st.expander("✨ Refine / Regenerate", expanded=False):
                st.write("Modify the summary with AI using these options:")
                
                # --- Templates Prédéfinis ---
                st.markdown("##### 📄 Templates Rapides")
                template_options = {
                    "(Aucun)": "",
                    "📊 Rapport Structuré": "Structure le texte comme un rapport professionnel avec une introduction claire, une analyse détaillée par thèmes, et une conclusion avec recommandations.",
                    "📝 Note de Synthèse": "Reformate en note de synthèse interne, factuelle et concise. Commence par les points clés, développe les détails ensuite.",
                    "✍️ Article de Blog": "Transforme en article de blog engageant avec un titre accrocheur, des paragraphes courts, un ton accessible et des sous-titres dynamiques.",
                    "📧 Email Exécutif": "Condense en email pour décideurs : 3-5 points clés maximum, actions à prendre en gras, le tout en moins de 200 mots."
                }
                
                selected_template = st.selectbox(
                    "Choisir un template",
                    list(template_options.keys()),
                    help="Applique un format prédéfini à votre synthèse"
                )
                
                template_instruction = template_options.get(selected_template, "")
                if template_instruction:
                    st.caption(f"*{template_instruction[:80]}...*")
                
                st.markdown("##### ⚙️ Options Personnalisées")
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
                
                # Template takes priority
                if template_instruction:
                    instructions_list.append(template_instruction)
                
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
            
            output_format = st.selectbox("Format d'export", ["md", "txt", "html", "pdf", "docx", "pptx"], index=2)
            
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
                            "pdf": "application/pdf",
                            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
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

# --- Tab 4: Projects ---
if st.session_state.nav_selection == "📂 Projets":
    st.header("📂 Gestion des Projets")
    
    db = get_database()
    
    # Session state for project management
    if "selected_project_id" not in st.session_state:
        st.session_state.selected_project_id = 1  # Default project
    
    col_sidebar, col_main = st.columns([1, 3])
    
    with col_sidebar:
        st.subheader("📁 Dossiers")
        
        # Create new project
        with st.popover("➕ Nouveau Projet"):
            new_proj_name = st.text_input("Nom du projet", key="new_proj_name")
            new_proj_desc = st.text_area("Description", key="new_proj_desc", height=100)
            if st.button("Créer", key="btn_create_proj"):
                if new_proj_name:
                    db.create_project(new_proj_name, new_proj_desc)
                    st.success(f"Projet '{new_proj_name}' créé!")
                    st.rerun()
        
        # List projects
        projects = db.get_all_projects()
        for proj in projects:
            is_selected = st.session_state.selected_project_id == proj.id
            btn_style = "primary" if is_selected else "secondary"
            if st.button(f"📁 {proj.name}", key=f"proj_{proj.id}", type=btn_style, use_container_width=True):
                st.session_state.selected_project_id = proj.id
                st.rerun()
        
        st.divider()
        
        # Tags management
        st.subheader("🏷️ Tags")
        
        with st.popover("➕ Nouveau Tag"):
            new_tag_name = st.text_input("Nom du tag", key="new_tag_name")
            new_tag_color = st.color_picker("Couleur", "#FF4B4B", key="new_tag_color")
            if st.button("Créer Tag", key="btn_create_tag"):
                if new_tag_name:
                    db.create_tag(new_tag_name, new_tag_color)
                    st.success(f"Tag '{new_tag_name}' créé!")
                    st.rerun()
        
        tags = db.get_all_tags()
        for tag in tags:
            st.markdown(f'<span style="background:{tag.color}; padding:2px 8px; border-radius:12px; color:white; font-size:0.8em;">{tag.name}</span>', unsafe_allow_html=True)
    
    with col_main:
        # Current project info
        current_project = db.get_project(st.session_state.selected_project_id)
        if current_project:
            st.subheader(f"📂 {current_project.name}")
            st.caption(current_project.description or "Aucune description")
        
        # Search and filter
        col_search, col_filter = st.columns([3, 1])
        with col_search:
            search_term = st.text_input("🔍 Rechercher", placeholder="Titre, contenu...", key="proj_search")
        with col_filter:
            filter_tag = st.selectbox("Tag", ["Tous"] + [t.name for t in tags], key="proj_tag_filter")
        
        # Get syntheses
        tag_id = None
        if filter_tag != "Tous":
            tag_obj = next((t for t in tags if t.name == filter_tag), None)
            tag_id = tag_obj.id if tag_obj else None
        
        syntheses = db.get_all_syntheses(
            project_id=st.session_state.selected_project_id,
            tag_id=tag_id,
            search=search_term if search_term else None
        )
        
        st.divider()
        
        # Stats
        st.markdown(f"**{len(syntheses)} synthèse(s)** dans ce projet")
        
        # Synthesis list
        if syntheses:
            for syn in syntheses:
                with st.container():
                    col_info, col_actions = st.columns([4, 1])
                    
                    with col_info:
                        st.markdown(f"### {syn['title']}")
                        st.caption(f"📅 {syn['created_at'][:10]} | 📊 {syn['summary_type']}")
                        
                        # Tags
                        if syn.get('tags'):
                            tags_html = " ".join([
                                f'<span style="background:{t.color}; padding:2px 6px; border-radius:10px; color:white; font-size:0.7em; margin-right:4px;">{t.name}</span>'
                                for t in syn['tags']
                            ])
                            st.markdown(tags_html, unsafe_allow_html=True)
                        
                        # Preview (first 200 chars)
                        preview = syn['summary'][:200].replace('<', '&lt;').replace('>', '&gt;') + "..."
                        st.markdown(f"<p style='color:#888; font-size:0.9em;'>{preview}</p>", unsafe_allow_html=True)
                    
                    with col_actions:
                        if st.button("📖 Ouvrir", key=f"open_{syn['id']}"):
                            # Load synthesis into editor
                            st.session_state.summary = syn['summary']
                            st.session_state.title = syn['title']
                            st.session_state.source_info = syn['sources']
                            st.session_state.generated = True
                            st.session_state.nav_selection = "📝 Résultat"
                            st.rerun()
                        
                        if st.button("🗑️", key=f"del_{syn['id']}", help="Supprimer"):
                            db.delete_synthesis(syn['id'])
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("Aucune synthèse dans ce projet. Créez-en une depuis l'onglet Synthèse!")
        
        # Project actions
        st.divider()
        with st.expander("⚙️ Actions Projet"):
            if current_project and current_project.id != 1:  # Can't delete default
                if st.button("🗑️ Supprimer ce projet", type="secondary"):
                    db.delete_project(current_project.id)
                    st.session_state.selected_project_id = 1
                    st.rerun()

# --- Tab 5: Analysis ---
if st.session_state.nav_selection == "🔬 Analyse":
    st.header("🔬 Analyse & Comparaison")
    
    db = get_database()
    analyzer = get_analyzer()
    
    # Get all syntheses for selection
    all_syntheses = db.get_all_syntheses(limit=100)
    
    if len(all_syntheses) < 1:
        st.warning("Vous devez avoir au moins une synthèse pour utiliser l'analyse. Créez-en une depuis l'onglet Synthèse!")
    else:
        # Analysis mode selection
        analysis_mode = st.radio(
            "Mode d'analyse",
            ["📊 Extraction de Faits", "⚖️ Comparaison", "⚠️ Contradictions"],
            horizontal=True
        )
        
        st.divider()
        
        # --- Fact Extraction ---
        if analysis_mode == "📊 Extraction de Faits":
            st.subheader("📊 Extraction de Faits")
            
            # Select synthesis
            synth_options = {f"{s['title'][:50]}... ({s['created_at'][:10]})": s for s in all_syntheses}
            selected_synth_name = st.selectbox("Sélectionnez une synthèse", list(synth_options.keys()))
            
            if selected_synth_name and st.button("🔍 Extraire les faits", type="primary"):
                selected_synth = synth_options[selected_synth_name]
                
                with st.spinner("Extraction en cours..."):
                    facts = analyzer.extract_facts_regex(selected_synth['summary'])
                    stats = analyzer.get_text_stats(selected_synth['summary'])
                
                # Display stats
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                col_s1.metric("Mots", stats['word_count'])
                col_s2.metric("Phrases", stats['sentence_count'])
                col_s3.metric("Caractères", stats['char_count'])
                col_s4.metric("Faits extraits", len(facts))
                
                st.divider()
                
                # Display facts by type
                if facts:
                    # Group by type
                    facts_by_type = {}
                    for f in facts:
                        if f.fact_type not in facts_by_type:
                            facts_by_type[f.fact_type] = []
                        facts_by_type[f.fact_type].append(f)
                    
                    for fact_type, type_facts in facts_by_type.items():
                        icon = {"date": "📅", "number": "🔢", "name": "👤", "location": "📍", "quote": "💬"}.get(fact_type, "📌")
                        with st.expander(f"{icon} {fact_type.capitalize()} ({len(type_facts)})", expanded=True):
                            for f in type_facts[:15]:
                                st.markdown(f"**{f.value}**")
                                st.caption(f.context)
                else:
                    st.info("Aucun fait détecté. Essayez avec une synthèse plus riche en données.")
        
        # --- Comparison ---
        elif analysis_mode == "⚖️ Comparaison":
            st.subheader("⚖️ Comparaison de Synthèses")
            
            if len(all_syntheses) < 2:
                st.warning("Vous devez avoir au moins 2 synthèses pour la comparaison.")
            else:
                col_sel1, col_sel2 = st.columns(2)
                
                synth_options = {f"{s['title'][:40]}...": s for s in all_syntheses}
                synth_names = list(synth_options.keys())
                
                with col_sel1:
                    sel1 = st.selectbox("Synthèse 1", synth_names, key="comp_sel1")
                with col_sel2:
                    sel2 = st.selectbox("Synthèse 2", synth_names, index=min(1, len(synth_names)-1), key="comp_sel2")
                
                if st.button("🔍 Comparer", type="primary"):
                    synth1 = synth_options[sel1]
                    synth2 = synth_options[sel2]
                    
                    with st.spinner("Analyse en cours..."):
                        comparison = analyzer.compare_texts(synth1['summary'], synth2['summary'])
                    
                    # Similarity score
                    sim = comparison['similarity']
                    sim_color = "green" if sim > 70 else ("orange" if sim > 40 else "red")
                    st.markdown(f"### Similarité : <span style='color:{sim_color};font-size:2em;'>{sim}%</span>", unsafe_allow_html=True)
                    
                    st.divider()
                    
                    # Side by side view
                    col_v1, col_v2 = st.columns(2)
                    
                    with col_v1:
                        st.markdown(f"**📄 {synth1['title'][:40]}...**")
                        st.markdown(f"<div style='max-height:400px; overflow-y:auto; padding:10px; background:#1a1a2e; border-radius:8px;'>{synth1['summary'][:2000]}</div>", unsafe_allow_html=True)
                    
                    with col_v2:
                        st.markdown(f"**📄 {synth2['title'][:40]}...**")
                        st.markdown(f"<div style='max-height:400px; overflow-y:auto; padding:10px; background:#1a1a2e; border-radius:8px;'>{synth2['summary'][:2000]}</div>", unsafe_allow_html=True)
                    
                    # Unique elements
                    st.divider()
                    col_u1, col_u2 = st.columns(2)
                    
                    with col_u1:
                        st.markdown("**🔵 Éléments uniques à Synthèse 1**")
                        for elem in comparison['unique_to_1'][:5]:
                            if len(elem.strip()) > 20:
                                st.markdown(f"- {elem[:100]}...")
                    
                    with col_u2:
                        st.markdown("**🟢 Éléments uniques à Synthèse 2**")
                        for elem in comparison['unique_to_2'][:5]:
                            if len(elem.strip()) > 20:
                                st.markdown(f"- {elem[:100]}...")
        
        # --- Contradictions ---
        else:
            st.subheader("⚠️ Détection de Contradictions")
            
            if len(all_syntheses) < 2:
                st.warning("Vous devez avoir au moins 2 synthèses pour détecter des contradictions.")
            else:
                # Multi-select syntheses
                synth_options = {f"{s['title'][:40]}...": s for s in all_syntheses}
                selected_names = st.multiselect(
                    "Sélectionnez les synthèses à analyser (2-5)",
                    list(synth_options.keys()),
                    default=list(synth_options.keys())[:2]
                )
                
                if len(selected_names) >= 2 and st.button("🔍 Détecter les contradictions", type="primary"):
                    texts = [
                        (synth_options[name]['summary'], synth_options[name]['title'][:30])
                        for name in selected_names[:5]
                    ]
                    
                    with st.spinner("Analyse des contradictions..."):
                        contradictions = analyzer.detect_contradictions_regex(texts)
                    
                    if contradictions:
                        st.error(f"⚠️ {len(contradictions)} contradiction(s) potentielle(s) détectée(s)")
                        
                        for idx, c in enumerate(contradictions, 1):
                            severity_color = {"low": "🟡", "medium": "🟠", "high": "🔴"}.get(c.severity, "⚪")
                            
                            with st.expander(f"{severity_color} Contradiction #{idx}: {c.topic}", expanded=True):
                                col_c1, col_c2 = st.columns(2)
                                
                                with col_c1:
                                    st.markdown(f"**Source:** {c.source_1}")
                                    st.info(c.statement_1)
                                
                                with col_c2:
                                    st.markdown(f"**Source:** {c.source_2}")
                                    st.warning(c.statement_2)
                    else:
                        st.success("✅ Aucune contradiction détectée entre les sources sélectionnées.")
                        st.caption("Note: L'analyse utilise des heuristiques. Certaines contradictions subtiles peuvent ne pas être détectées.")

# --- Tab 6: Automation ---
if st.session_state.nav_selection == "🤖 Automation":
    st.header("🤖 Automatisation")
    
    scheduler = get_scheduler()
    alert_mgr = get_alert_manager()
    db = get_database()
    
    # Tabs for different automation features
    auto_tab = st.radio(
        "Section",
        ["📅 Tâches Planifiées", "🔔 Alertes", "🔌 API REST"],
        horizontal=True
    )
    
    st.divider()
    
    # --- Scheduled Tasks ---
    if auto_tab == "📅 Tâches Planifiées":
        st.subheader("📅 Tâches Planifiées")
        
        # Create new task
        with st.expander("➕ Créer une nouvelle tâche", expanded=False):
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
                task_name = st.text_input("Nom de la tâche", placeholder="Ex: Veille IA quotidienne")
                search_query = st.text_input("Recherche YouTube", placeholder="Ex: actualités intelligence artificielle")
                
            with col_t2:
                schedule_type = st.selectbox("Fréquence", ["daily", "weekly", "interval"])
                if schedule_type in ["daily", "weekly"]:
                    schedule_time = st.time_input("Heure d'exécution")
                    schedule_time_str = schedule_time.strftime("%H:%M")
                else:
                    interval_val = st.number_input("Intervalle", min_value=1, value=6)
                    interval_unit = st.selectbox("Unité", ["h", "m"])
                    schedule_time_str = f"{interval_val}{interval_unit}"
            
            col_t3, col_t4 = st.columns(2)
            with col_t3:
                summary_type = st.selectbox("Type de synthèse", ["short", "medium", "long", "news"])
            with col_t4:
                projects = db.get_all_projects()
                project_names = {p.name: p.id for p in projects}
                selected_project = st.selectbox("Projet destination", list(project_names.keys()))
            
            if st.button("✅ Créer la tâche", type="primary"):
                if task_name and search_query:
                    scheduler.add_task(
                        name=task_name,
                        search_query=search_query,
                        schedule_type=schedule_type,
                        schedule_time=schedule_time_str,
                        summary_type=summary_type,
                        project_id=project_names[selected_project]
                    )
                    st.success(f"Tâche '{task_name}' créée!")
                    st.rerun()
                else:
                    st.warning("Remplissez le nom et la recherche.")
        
        st.divider()
        
        # List existing tasks
        tasks = scheduler.get_all_tasks()
        
        if tasks:
            for task in tasks:
                with st.container():
                    col_info, col_status, col_actions = st.columns([3, 2, 1])
                    
                    with col_info:
                        status_icon = "✅" if task.enabled else "⏸️"
                        st.markdown(f"### {status_icon} {task.name}")
                        st.caption(f"🔍 {task.search_query}")
                        st.caption(f"⏰ {task.schedule_type} @ {task.schedule_time} | 📊 {task.summary_type}")
                    
                    with col_status:
                        if task.next_run:
                            st.markdown(f"**Prochain:** {task.next_run[:16]}")
                        if task.last_run:
                            st.caption(f"Dernier: {task.last_run[:16]}")
                    
                    with col_actions:
                        if st.button("⏯️", key=f"toggle_{task.id}", help="Activer/Désactiver"):
                            scheduler.toggle_task(task.id)
                            st.rerun()
                        if st.button("🗑️", key=f"del_task_{task.id}", help="Supprimer"):
                            scheduler.delete_task(task.id)
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("Aucune tâche planifiée. Créez-en une ci-dessus!")
        
        # Instructions
        with st.expander("ℹ️ Comment fonctionne le scheduler ?"):
            st.markdown("""
            Les tâches planifiées sont stockées dans un fichier de configuration.
            
            **Pour exécuter les tâches automatiquement**, vous pouvez :
            1. Utiliser un cron/Task Scheduler Windows qui exécute un script
            2. Lancer l'API REST (`python api.py`) et utiliser un service externe
            
            Les tâches seront exécutées selon leur planification et les synthèses seront
            automatiquement sauvegardées dans le projet sélectionné.
            """)
    
    # --- Alerts ---
    elif auto_tab == "🔔 Alertes":
        st.subheader("🔔 Notifications")
        
        unread = alert_mgr.get_unread_alerts()
        if unread:
            st.warning(f"📬 {len(unread)} notification(s) non lue(s)")
            
            if st.button("Marquer tout comme lu"):
                alert_mgr.mark_all_read()
                st.rerun()
        
        alerts = alert_mgr.get_all_alerts(limit=30)
        
        if alerts:
            for alert in alerts:
                icon = {"new_video": "🎬", "synthesis_complete": "✅", "error": "❌"}.get(alert.type, "📌")
                read_style = "opacity: 0.6;" if alert.read else "font-weight: bold;"
                
                st.markdown(f"""
                <div style="{read_style} padding: 10px; border-left: 3px solid #FF4B4B; margin: 5px 0;">
                    <strong>{icon} {alert.title}</strong><br/>
                    <span style="color: #888;">{alert.message}</span><br/>
                    <small>{alert.created_at[:16]}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune notification pour le moment.")
        
        if alerts:
            if st.button("🗑️ Effacer toutes les notifications"):
                alert_mgr.clear_alerts()
                st.rerun()
    
    # --- API REST ---
    else:
        st.subheader("🔌 API REST")
        
        st.markdown("""
        SynthetIA dispose d'une API REST pour l'intégration externe.
        
        ### Démarrer l'API
        ```bash
        cd src
        python api.py
        # ou
        uvicorn api:app --reload --port 8001
        ```
        
        L'API sera disponible sur **http://localhost:8001**
        
        ### Documentation automatique
        - **Swagger UI:** http://localhost:8001/docs
        - **ReDoc:** http://localhost:8001/redoc
        """)
        
        st.divider()
        
        st.markdown("### Endpoints disponibles")
        
        endpoints = [
            ("GET", "/projects", "Liste des projets"),
            ("POST", "/projects", "Créer un projet"),
            ("GET", "/syntheses", "Liste des synthèses"),
            ("GET", "/syntheses/{id}", "Détails d'une synthèse"),
            ("DELETE", "/syntheses/{id}", "Supprimer une synthèse"),
            ("GET", "/tasks", "Tâches planifiées"),
            ("POST", "/tasks", "Créer une tâche"),
            ("GET", "/alerts", "Notifications"),
            ("GET", "/stats", "Statistiques"),
        ]
        
        for method, path, desc in endpoints:
            method_color = {"GET": "green", "POST": "blue", "DELETE": "red"}.get(method, "gray")
            st.markdown(f"`{method}` **{path}** - {desc}")
        
        st.divider()
        
        st.markdown("### Exemple d'utilisation")
        st.code("""
import requests

# Récupérer les synthèses
response = requests.get("http://localhost:8001/syntheses")
syntheses = response.json()

# Créer une tâche planifiée
task_data = {
    "name": "Veille Tech",
    "search_query": "actualités tech 2024",
    "schedule_type": "daily",
    "schedule_time": "09:00"
}
response = requests.post("http://localhost:8001/tasks", json=task_data)
        """, language="python")

# --- Tab 7: Stats ---
if st.session_state.nav_selection == "📊 Stats":
    st.header("📊 Statistiques d'Utilisation")
    
    analytics = get_analytics()
    
    # KPI Cards
    stats = analytics.get_summary_stats()
    avg_stats = analytics.get_average_stats()
    
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    with col_k1:
        st.metric(
            label="🎯 Synthèses",
            value=stats['total_syntheses'],
            delta=f"Moy. {avg_stats['avg_videos']} vidéos"
        )
    
    with col_k2:
        st.metric(
            label="🎬 Vidéos traitées",
            value=stats['total_videos']
        )
    
    with col_k3:
        st.metric(
            label="⏱️ Temps gagné",
            value=f"{stats['time_saved_hours']}h",
            delta=f"~{avg_stats['avg_time_saved']}min/synth"
        )
    
    with col_k4:
        st.metric(
            label="📝 Mots générés",
            value=f"{stats['words_generated']:,}".replace(",", " ")
        )
    
    st.divider()
    
    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📈 Activité (30 derniers jours)")
        
        activity_data = analytics.get_activity_by_day(30)
        
        if any(d['count'] > 0 for d in activity_data):
            try:
                import plotly.express as px
                import pandas as pd
                
                df = pd.DataFrame(activity_data)
                fig = px.bar(
                    df, x='date', y='count',
                    labels={'date': 'Date', 'count': 'Synthèses'},
                    color_discrete_sequence=['#FF4B4B']
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0.1)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.caption(f"Graphique non disponible: {e}")
        else:
            st.info("Pas encore d'activité enregistrée")
    
    with col_chart2:
        st.subheader("🏷️ Top Sujets")
        
        topics = analytics.get_top_topics(8)
        
        if topics:
            try:
                import plotly.express as px
                import pandas as pd
                
                df = pd.DataFrame(topics)
                fig = px.bar(
                    df, y='topic', x='count',
                    orientation='h',
                    labels={'topic': 'Sujet', 'count': 'Nombre'},
                    color_discrete_sequence=['#4BAFFF']
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0.1)',
                    font_color='white',
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.caption(f"Graphique non disponible: {e}")
        else:
            st.info("Pas encore de sujets enregistrés")
    
    st.divider()
    
    # Distribution charts
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.subheader("📊 Types de Synthèse")
        
        type_dist = analytics.get_summary_type_distribution()
        
        if type_dist:
            try:
                import plotly.express as px
                import pandas as pd
                
                df = pd.DataFrame([
                    {'type': k, 'count': v} 
                    for k, v in type_dist.items()
                ])
                fig = px.pie(
                    df, values='count', names='type',
                    color_discrete_sequence=['#FF4B4B', '#4BAFFF', '#4BFF8B', '#FFB84B', '#B84BFF']
                )
                fig.update_layout(
                    height=250,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            except:
                for t, c in type_dist.items():
                    st.write(f"**{t}**: {c}")
        else:
            st.info("Pas de données")
    
    with col_d2:
        st.subheader("📤 Formats d'Export")
        
        export_dist = analytics.get_export_format_distribution()
        
        if export_dist:
            try:
                import plotly.express as px
                import pandas as pd
                
                df = pd.DataFrame([
                    {'format': k.upper(), 'count': v} 
                    for k, v in export_dist.items()
                ])
                fig = px.pie(
                    df, values='count', names='format',
                    color_discrete_sequence=['#4BAFFF', '#FF4B4B', '#4BFF8B', '#FFB84B', '#B84BFF', '#FF4BBF']
                )
                fig.update_layout(
                    height=250,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            except:
                for f, c in export_dist.items():
                    st.write(f"**{f.upper()}**: {c}")
        else:
            st.info("Aucun export enregistré")
    
    # Hourly activity
    st.divider()
    st.subheader("🕐 Activité par Heure")
    
    hourly = analytics.get_hourly_activity()
    
    if any(v > 0 for v in hourly.values()):
        try:
            import plotly.express as px
            import pandas as pd
            
            df = pd.DataFrame([
                {'hour': f"{h}h", 'count': c}
                for h, c in sorted(hourly.items())
            ])
            fig = px.bar(
                df, x='hour', y='count',
                labels={'hour': 'Heure', 'count': 'Synthèses'},
                color_discrete_sequence=['#B84BFF']
            )
            fig.update_layout(
                height=200,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0.1)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.write("Activité par heure:", hourly)
    else:
        st.info("Pas encore d'activité enregistrée")
