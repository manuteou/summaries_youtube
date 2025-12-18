# interfaces.py - Protocol definitions for dependency inversion
"""
Ce module définit les interfaces (Protocols) pour permettre
l'injection de dépendances et faciliter les tests.
"""

from typing import Protocol, runtime_checkable, List, Tuple, Optional, Any
from datetime import datetime


@runtime_checkable
class IVideoSearcher(Protocol):
    """Interface pour les services de recherche vidéo."""
    
    def search(self, query: str, **kwargs) -> Any:
        """Recherche des vidéos par requête."""
        ...
    
    def fetch_next(self, search_obj: Any) -> List[Any]:
        """Récupère la page suivante de résultats."""
        ...


@runtime_checkable
class IVideoDownloader(Protocol):
    """Interface pour le téléchargement de vidéos/audio."""
    
    def download_audio(self, url: str) -> Tuple[str, str, str, Optional[datetime]]:
        """Télécharge l'audio d'une vidéo. Retourne (path, title, author, date)."""
        ...
    
    def get_video_info(self, url: str) -> Optional[Any]:
        """Récupère les métadonnées d'une vidéo."""
        ...
    
    def check_subtitles(self, url: str) -> Optional[str]:
        """Vérifie la disponibilité des sous-titres."""
        ...
    
    def get_subtitles(self, url: str, code: str) -> Tuple[str, str, str, Optional[datetime]]:
        """Récupère les sous-titres."""
        ...


@runtime_checkable
class IVideoFilter(Protocol):
    """Interface pour le filtrage de vidéos."""
    
    def filter_videos(
        self, 
        videos: List[Any], 
        duration_mode: str, 
        days_limit: Optional[int] = None
    ) -> List[Any]:
        """Filtre les vidéos selon les critères."""
        ...


@runtime_checkable
class IAudioExtractor(Protocol):
    """Interface pour l'extraction audio de fichiers locaux."""
    
    def extract_audio_from_video(self, input_video: str) -> List[str]:
        """Extrait l'audio d'un fichier vidéo et retourne les segments."""
        ...
    
    def split_audio(self, input_file: str) -> List[str]:
        """Découpe un fichier audio en segments."""
        ...


@runtime_checkable
class ITranscriber(Protocol):
    """Interface pour les services de transcription."""
    
    def transcribe_audio(self, audio_file: str) -> str:
        """Transcrit un fichier audio en texte."""
        ...
    
    def transcribe_segments(self, segments: List[str]) -> List[str]:
        """Transcrit une liste de segments audio."""
        ...
    
    @staticmethod
    def extract_subtitles(srt_content: str) -> str:
        """Extrait le texte d'un contenu SRT."""
        ...


@runtime_checkable
class ISummarizer(Protocol):
    """Interface pour les services de résumé."""
    
    def summarize_text(self, text: str, author: str) -> str:
        """Génère un résumé court."""
        ...
    
    def summarize_long_text(self, text: str, author: str) -> str:
        """Génère un résumé long avec chunking."""
        ...
    
    def summarize_multi_texts(self, search: str, text: str) -> str:
        """Synthétise plusieurs textes."""
        ...


@runtime_checkable
class IExporter(Protocol):
    """Interface pour l'export de documents."""
    
    def save_summary(
        self, 
        summary: str, 
        title: str, 
        fmt: str, 
        source_info: Optional[List[dict]] = None
    ) -> str:
        """Sauvegarde un résumé dans le format spécifié."""
        ...
    
    def generate_pdf_bytes(
        self, 
        summary: str, 
        title: str, 
        source_info: Optional[List[dict]] = None
    ) -> bytes:
        """Génère un PDF en mémoire."""
        ...
