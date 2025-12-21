"""
workflow.py - Refactored workflow orchestration

Ce module orchestre le flux de travail complet pour la synthèse de vidéos.
Utilise l'injection de dépendances pour les services (DIP).
"""

import os
import datetime
import warnings
from pathlib import Path
from typing import List, Tuple, Optional, Any, Dict
from rich.console import Console
from rich.markdown import Markdown
from dotenv import load_dotenv

from downloader import YouTubeAudioProcessor
from transcriber import WhisperTranscriber
from summarizer import Summarizer
from exporter import Exporter
from utils import clean_files, time_since, sanitize_text
from prompts import PromptManager
from config import PREFERRED_CHANNELS
from constants import MIN_RESULTS_TARGET, MIN_BOOSTED_SOURCES, MAX_FETCH_ATTEMPTS

# Load environment variables
load_dotenv()

# Environment configuration
DEVICE = os.getenv("DEVICE", "cpu")
MODEL = os.getenv("MODEL", "medium")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./summaries")
FORMAT = os.getenv("FORMAT", "md")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
FFMPEG_DIR = os.getenv("FFMPEG")

if FFMPEG_DIR:
    os.environ["PATH"] += os.pathsep + FFMPEG_DIR

warnings.filterwarnings("ignore")


class WorkflowManager:
    """
    Orchestrateur du workflow de synthèse vidéo.
    
    Utilise l'injection de dépendances (DIP) pour les services :
    - processor: Service de traitement YouTube/audio
    - transcriber: Service de transcription
    - summarizer: Service de résumé
    - exporter: Service d'export
    """
    
    def __init__(self, processor, transcriber, summarizer, exporter):
        """Initialise le workflow avec les services injectés."""
        self.processor = processor
        self.transcriber = transcriber
        self.summarizer = summarizer
        self.exporter = exporter

    # =========================================================================
    # VIDEO TEXT EXTRACTION
    # =========================================================================
    
    def get_video_text(self, url: str) -> Tuple[str, str, str, str, str]:
        """
        Extrait le texte d'une vidéo (sous-titres ou transcription audio).
        
        Args:
            url: URL YouTube ou chemin de fichier local
            
        Returns:
            Tuple (text, title, author, date, method)
        """
        if self._is_local_file(url):
            return self._process_local_file(url)
        return self._process_youtube_video(url)
    
    def _is_local_file(self, url: str) -> bool:
        """Détermine si l'URL est un fichier local."""
        return (
            os.path.exists(url) or 
            (not url.startswith("http") and 
             "youtube.com" not in url and 
             "youtu.be" not in url)
        )
    
    def _process_local_file(self, path: str) -> Tuple[str, str, str, str, str]:
        """Traite un fichier vidéo local."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Fichier local introuvable : {path}")
        
        video_path = Path(path)
        segments = self.processor.extract_audio_from_mp4(video_path)
        
        if not segments:
            raise Exception("Aucun segment audio extrait.")
        
        texts = self.transcriber.transcribe_segments(segments)
        result = "\n".join(texts)
        
        if not result.strip():
            raise Exception("La transcription est vide (pas de voix détectée ?).")
        
        return (
            result,
            video_path.stem,
            "Fichier Local",
            datetime.datetime.now().strftime("%Y-%m-%d"),
            "local_mp4"
        )
    
    def _process_youtube_video(self, url: str) -> Tuple[str, str, str, str, str]:
        """Traite une vidéo YouTube."""
        try:
            code = self.processor.check_subtitles(url)
            if code:
                subtitles_file, title, author, date = self.processor.get_subtitles(url, code)
                result = self.transcriber.extract_subtitles(subtitles_file)
                method = "subtitles"
            else:
                audio_file, title, author, date = self.processor.download_audio(url)
                if not audio_file:
                    raise Exception("Impossible de télécharger l'audio YouTube.")
                result = self.transcriber.transcribe_audio(audio_file)
                method = "audio"
            
            return result, title, author, date, method
        except Exception as e:
            raise Exception(f"Échec traitement YouTube : {sanitize_text(str(e))}")

    # =========================================================================
    # SINGLE VIDEO PROCESSING
    # =========================================================================
    
    def process_single_video(self, url: str) -> Tuple[str, str, List[Dict]]:
        """
        Traite une seule vidéo et retourne le résumé.
        
        Returns:
            Tuple (summary, title, source_info)
        """
        text, title, author, date, method = self.get_video_text(url)
        summary = self.summarizer.summarize_long_text(text, author)
        source_info = [{"title": title, "url": url, "date": date}]
        return summary, title, source_info

    # =========================================================================
    # SEARCH FUNCTIONALITY
    # =========================================================================
    
    def search_videos(self, query: str, limit: int = 3) -> List[Any]:
        """Recherche des vidéos et retourne une liste d'objets vidéo."""
        videos = self.processor.search_subject(query)
        return videos[:limit] if videos else []

    def init_search(
        self, 
        query: str, 
        sort_by: str = "relevance", 
        upload_date: Optional[str] = None, 
        exclude_terms: Optional[str] = None
    ) -> Any:
        """Initialise une session de recherche."""
        return self.processor.get_search_object(query, sort_by, upload_date, exclude_terms)

    def is_channel_preferred(
        self, 
        channel_name: Optional[str], 
        active_categories: Optional[List[str]]
    ) -> bool:
        """Vérifie si une chaîne est dans la liste des sources préférées."""
        if not channel_name:
            return False
        
        categories_to_check = active_categories if active_categories else PREFERRED_CHANNELS.keys()
        
        for category in categories_to_check:
            if category in PREFERRED_CHANNELS:
                for preferred in PREFERRED_CHANNELS[category]:
                    if preferred.lower() in channel_name.lower():
                        return True
        return False

    def _apply_boost_ordering(
        self, 
        videos: List[Any], 
        active_categories: Optional[List[str]]
    ) -> List[Any]:
        """
        Trie les vidéos en plaçant les sources préférées en premier (DRY).
        
        Cette méthode est extraite pour éviter la duplication de code
        entre get_search_results et load_more_videos.
        """
        boosted, regular = [], []
        for v in videos:
            is_fav = self.is_channel_preferred(v.author, active_categories)
            v.is_boosted = is_fav
            (boosted if is_fav else regular).append(v)
        return boosted + regular

    def get_search_results(
        self, 
        search_obj: Any, 
        duration_mode: str = "any", 
        active_categories: Optional[List[str]] = None, 
        enable_boost: bool = True, 
        days_limit: Optional[int] = None
    ) -> List[Any]:
        """
        Retourne les résultats filtrés avec boost optionnel des sources.
        
        Implémente une logique de récupération intelligente pour garantir
        un minimum de résultats et de sources de confiance.
        """
        raw_results = [v for v in search_obj.results if v not in search_obj.shorts]
        filtered = self.processor.filter_videos(raw_results, duration_mode, days_limit=days_limit)
        
        def count_boosted(videos: List[Any]) -> int:
            return sum(1 for v in videos if self.is_channel_preferred(v.author, active_categories))
        
        attempts = 0
        boosted_count = count_boosted(filtered) if enable_boost else 0
        
        # Boucle de récupération intelligente
        while attempts < MAX_FETCH_ATTEMPTS:
            need_more_total = len(filtered) < MIN_RESULTS_TARGET
            need_more_boosted = enable_boost and boosted_count < MIN_BOOSTED_SOURCES
            
            if not (need_more_total or need_more_boosted):
                break
            
            print(f"DEBUG: Fetching more... Total: {len(filtered)}, Boosted: {boosted_count} (Attempt {attempts + 1}/{MAX_FETCH_ATTEMPTS})")
            
            try:
                new_videos = self.processor.fetch_next(search_obj)
                if not new_videos:
                    break
                
                new_filtered = self.processor.filter_videos(new_videos, duration_mode, days_limit=days_limit)
                
                current_urls = {v.watch_url for v in filtered}
                for v in new_filtered:
                    if v.watch_url not in current_urls:
                        filtered.append(v)
                
                if enable_boost:
                    boosted_count = count_boosted(filtered)
                    
            except Exception as e:
                print(f"Warning: Error fetching more videos: {e}")
                break
            
            attempts += 1
        
        # Appliquer le tri boost (méthode extraite - DRY)
        if enable_boost:
            return self._apply_boost_ordering(filtered, active_categories)
        
        return filtered

    def load_more_videos(
        self, 
        search_obj: Any, 
        duration_mode: str = "any", 
        active_categories: Optional[List[str]] = None, 
        enable_boost: bool = True, 
        days_limit: Optional[int] = None
    ) -> List[Any]:
        """Récupère plus de vidéos pour une session de recherche existante."""
        new_videos = self.processor.fetch_next(search_obj)
        filtered = self.processor.filter_videos(new_videos, duration_mode, days_limit=days_limit)
        
        if enable_boost:
            return self._apply_boost_ordering(filtered, active_categories)
        
        return filtered

    def get_video_info(self, url: str) -> Optional[Any]:
        """Récupère les métadonnées d'une vidéo."""
        return self.processor.get_video_info(url)

    # =========================================================================
    # MULTI-VIDEO SYNTHESIS
    # =========================================================================
    
    def synthesize_videos(
        self, 
        selected_videos: List[Any], 
        search_term: str, 
        title_override: Optional[str] = None
    ) -> Tuple[str, str, List[Any]]:
        """
        Synthétise plusieurs vidéos en un seul document.
        
        Args:
            selected_videos: Liste d'objets vidéo (YouTube ou LocalVideo)
            search_term: Terme de recherche/sujet
            title_override: Titre personnalisé optionnel
            
        Returns:
            Tuple (summary, final_search_term, source_info)
        """
        texts = []
        source_info = []
        source_list_header = "=== SOURCES DISPONIBLES (utiliser UNIQUEMENT ces références) ===\n"
        
        for idx, vid in enumerate(selected_videos, start=1):
            url = vid.watch_url
            title = vid.title
            # Use get_video_text which handles both YouTube and local files correctly
            text, _, _, date, _ = self.get_video_text(url)
            # Summarize the extracted text
            summary_text = self.summarizer.summarize_long_text(text, author=title)
            # Format avec numéro de source explicite
            texts.append(f"[{idx}] Source: {title}\n{summary_text}")
            source_list_header += f"[{idx}] {title}\n"
            # Create source info dict for exporter (not raw YouTube object)
            source_info.append({"title": title, "url": url, "date": date})
        
        final_search_term = search_term if search_term else "Synthèse Manuelle"
        prompt_context = title_override if title_override else final_search_term
        # Inclure la liste des sources en haut du texte
        summary = source_list_header + "\n=== CONTENU DES SOURCES ===\n\n" + "\n\n".join(texts)
        
        # Boucle de validation avec retry
        for attempt in range(3):
            if self.summarizer.summary_type in ["meeting"]:
                for _ in range(2):
                    summary = self.summarizer.summarize_multi_texts(prompt_context, summary)
                    summary = "\n\n== Text suivant ==".join(summary)
            else:
                summary = self.summarizer.summarize_multi_texts(prompt_context, summary)
            
            # Validation du contenu
            check_result = self.summarizer.check_synthese(summary, prompt_context)
            if self._parse_check_result(check_result):
                break
        
        summary = self.summarizer.enhance_markdown(summary)
        return summary, final_search_term, source_info
    
    @staticmethod
    def _parse_check_result(result: str) -> bool:
        """Parse le résultat de vérification de manière sécurisée."""
        try:
            return eval(result)
        except:
            return result.strip().lower() == "true"

    def refine_summary(self, current_summary: str, instructions: str) -> str:
        """Affine le résumé selon les instructions utilisateur."""
        return self.summarizer.refine_summary(current_summary, instructions)

    def process_video_path(
        self, 
        video_path_str: str, 
        type_summary: str = "short"
    ) -> Tuple[str, str, List[Dict]]:
        """
        Traite un fichier vidéo local.
        
        Returns:
            Tuple (summary, title, source_info)
        """
        video_path = Path(video_path_str)
        segments = self.processor.extract_audio_from_mp4(video_path)
        summary_segments = self.transcriber.transcribe_segments(segments)
        title = video_path.stem
        full_text = "\n\n".join(summary_segments)
        
        # Résumé détaillé
        detailed_summary = self.summarizer.summarize_long_text(full_text, author=title)
        
        # Analyse globale si type long
        if type_summary == "long":
            global_analysis = self.summarizer.generate_global_analysis(detailed_summary)
            final_output = f"{global_analysis}\n\n---\n\n# Détails des Sections\n\n{detailed_summary}"
        else:
            final_output = detailed_summary
        
        source_info = [{"title": title, "url": str(video_path.absolute())}]
        return final_output, title, source_info

    # =========================================================================
    # EXPORT & CLEANUP
    # =========================================================================
    
    def save_summary(
        self, 
        summary: str, 
        title: str, 
        fmt: str, 
        source_info: Optional[List[Dict]] = None
    ) -> str:
        """Sauvegarde le résumé via l'exporter."""
        return self.exporter.save_summary(summary, title, fmt, source_info)

    def get_pdf_bytes(
        self, 
        summary: str, 
        title: str, 
        source_info: Optional[List[Dict]] = None
    ) -> bytes:
        """Génère le PDF en mémoire pour téléchargement."""
        return self.exporter.generate_pdf_bytes(summary, title, source_info)

    def cleanup(self) -> None:
        """Nettoie les fichiers temporaires."""
        list_path = ["./audio_segments", "./chunk_data"]
        clean_files(list_path)
