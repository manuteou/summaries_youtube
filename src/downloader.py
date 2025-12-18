"""
downloader.py - Refactored YouTube download and audio processing services

Ce module a été refactorisé pour suivre le principe SRP (Single Responsibility Principle).
Chaque classe a une responsabilité unique et bien définie.
"""

import os
import datetime
import time
import concurrent.futures
from typing import List, Tuple, Optional, Any, Dict
from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix.contrib.search import Search, Filter
from pytubefix.exceptions import RegexMatchError
import subprocess
from pydub import AudioSegment

from utils import slugify
from constants import (
    MIN_VIDEO_DURATION_SECONDS,
    SHORT_VIDEO_MAX_SECONDS,
    MEDIUM_VIDEO_MAX_SECONDS,
    SEGMENT_LENGTH_MS,
    DEFAULT_AUDIO_SAMPLE_RATE,
    AUDIO_COMPRESSION_LEVEL,
    THREAD_POOL_SIZE,
    MAX_DOWNLOAD_RETRIES,
    RETRY_DELAY_SECONDS,
)


class YouTubeSearchService:
    """Service de recherche YouTube uniquement (SRP)."""
    
    def search(self, query: str, filters: Optional[Filter] = None) -> Search:
        """Crée un objet de recherche YouTube."""
        if filters is None:
            filters = Filter.create().type(Filter.Type.VIDEO)
        return Search(query, filters=filters)
    
    def create_filters(
        self, 
        sort_by: str = "relevance", 
        upload_date: Optional[str] = None
    ) -> Filter:
        """Crée des filtres de recherche."""
        filters = Filter.create().type(Filter.Type.VIDEO)
        
        sort_mapping = {
            "date": Filter.SortBy.UPLOAD_DATE,
            "views": Filter.SortBy.VIEW_COUNT,
            "relevance": Filter.SortBy.RELEVANCE,
        }
        filters = filters.sort_by(sort_mapping.get(sort_by, Filter.SortBy.RELEVANCE))
        
        date_mapping = {
            "today": Filter.UploadDate.TODAY,
            "week": Filter.UploadDate.THIS_WEEK,
            "month": Filter.UploadDate.THIS_MONTH,
            "year": Filter.UploadDate.THIS_YEAR,
        }
        if upload_date and upload_date in date_mapping:
            filters = filters.upload_date(date_mapping[upload_date])
        
        return filters
    
    def fetch_next(self, search_obj: Search) -> List[Any]:
        """Récupère la page suivante de résultats."""
        search_obj.get_next_results()
        return [v for v in search_obj.results if v not in search_obj.shorts]


class YouTubeDownloader:
    """Service de téléchargement audio YouTube (SRP)."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def download_audio(self, url: str) -> Tuple[str, str, str, Optional[datetime.datetime]]:
        """Télécharge l'audio d'une vidéo YouTube avec retry."""
        for attempt in range(MAX_DOWNLOAD_RETRIES):
            try:
                yt = YouTube(url, on_progress_callback=on_progress)
                ys = yt.streams.get_audio_only()
                safe_title = slugify(yt.title)
                filename = f"{safe_title}.m4a"
                audio_file = ys.download(output_path=self.output_dir, filename=filename)
                return audio_file, yt.title, yt.author, yt.publish_date
            except Exception as e:
                print(f"Retry {attempt + 1}/{MAX_DOWNLOAD_RETRIES}: {e}")
                if attempt == MAX_DOWNLOAD_RETRIES - 1:
                    raise
                time.sleep(RETRY_DELAY_SECONDS)
        return "", "", "", None
    
    def get_video_info(self, url: str) -> Optional[YouTube]:
        """Récupère les métadonnées d'une vidéo."""
        try:
            return YouTube(url)
        except RegexMatchError:
            print(f"Erreur : URL YouTube invalide ('{url}')")
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération des infos : {e}")
            return None
    
    def check_subtitles(self, url: str) -> Optional[str]:
        """Vérifie la disponibilité des sous-titres FR/EN."""
        yt = YouTube(url, on_progress_callback=on_progress)
        codes_fr_en = [k for k in yt.captions.keys() if "fr" in k.code or "en" in k.code]
        return codes_fr_en[0].code if codes_fr_en else None
    
    def get_subtitles(
        self, url: str, code: str
    ) -> Tuple[str, str, str, Optional[datetime.datetime]]:
        """Récupère les sous-titres d'une vidéo."""
        yt = YouTube(url, on_progress_callback=on_progress)
        caption = yt.captions[code]
        title = yt.title or "inconnue"
        return caption.generate_srt_captions(), title, yt.author, yt.publish_date


class VideoFilter:
    """Service de filtrage de vidéos (SRP)."""
    
    def filter_videos(
        self, 
        videos: List[Any], 
        duration_mode: str = "any", 
        days_limit: Optional[int] = None
    ) -> List[Any]:
        """Filtre les vidéos selon durée et date, avec récupération des métadonnées en parallèle."""
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Récupération parallèle des métadonnées
        videos_metadata = self._fetch_metadata_parallel(videos)
        
        # Filtrage
        filtered = []
        for item in videos_metadata:
            if not item["success"]:
                continue
                
            v = item["video"]
            length = item["length"]
            pub_date = item["publish_date"]
            
            # Attacher les métadonnées pour l'UI
            self._attach_metadata(v, item)
            
            # Filtre durée minimale
            if length < MIN_VIDEO_DURATION_SECONDS:
                continue
            
            # Filtre date
            if not self._passes_date_filter(pub_date, days_limit, now):
                continue
            
            # Filtre mode durée
            if self._passes_duration_filter(length, duration_mode):
                filtered.append(v)
        
        return filtered
    
    def _fetch_metadata_parallel(self, videos: List[Any]) -> List[Dict]:
        """Récupère les métadonnées en parallèle."""
        def get_meta(v):
            try:
                return {
                    "video": v,
                    "title": v.title,
                    "length": v.length,
                    "publish_date": v.publish_date,
                    "views": v.views,
                    "author": v.author,
                    "thumbnail_url": v.thumbnail_url,
                    "description": v.description,
                    "success": True
                }
            except Exception:
                return {"success": False}
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE) as executor:
            futures = {executor.submit(get_meta, v): v for v in videos}
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res.get("success"):
                    results.append(res)
        return results
    
    @staticmethod
    def _attach_metadata(video: Any, metadata: Dict) -> None:
        """Attache les métadonnées au video pour persistance UI."""
        video.title_attr = metadata["title"]
        video.author_attr = metadata["author"]
        video.thumb_attr = metadata["thumbnail_url"]
        video.views_attr = metadata["views"]
        video.length_attr = metadata["length"]
        video.publish_date_attr = metadata["publish_date"]
        video.description_attr = metadata["description"]
    
    @staticmethod
    def _passes_date_filter(
        pub_date: Optional[datetime.datetime], 
        days_limit: Optional[int], 
        now: datetime.datetime
    ) -> bool:
        """Vérifie si la vidéo passe le filtre de date."""
        if not days_limit or not pub_date:
            return True
        
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)
        
        age = now - pub_date
        return age.days <= days_limit
    
    @staticmethod
    def _passes_duration_filter(length: int, duration_mode: str) -> bool:
        """Vérifie si la vidéo passe le filtre de durée."""
        if not duration_mode or duration_mode == "any":
            return True
        elif duration_mode == "short" and length < SHORT_VIDEO_MAX_SECONDS:
            return True
        elif duration_mode == "medium" and SHORT_VIDEO_MAX_SECONDS <= length <= MEDIUM_VIDEO_MAX_SECONDS:
            return True
        elif duration_mode == "long" and length > MEDIUM_VIDEO_MAX_SECONDS:
            return True
        return False


class AudioExtractor:
    """Service d'extraction audio de fichiers locaux (SRP)."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def extract_audio_from_video(self, input_video: str) -> List[str]:
        """Extrait l'audio d'un fichier vidéo et retourne les segments."""
        audio_path = os.path.join(self.output_dir, "full_audio.flac")
        
        command = [
            "ffmpeg",
            "-i", str(input_video),
            "-vn",
            "-acodec", "flac",
            "-ar", str(DEFAULT_AUDIO_SAMPLE_RATE),
            "-compression_level", str(AUDIO_COMPRESSION_LEVEL),
            "-y",
            audio_path
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise Exception("Extraction audio échouée : fichier vide ou non créé.")
        
        segments = self.split_audio(audio_path)
        os.remove(audio_path)
        return segments
    
    def split_audio(self, input_file: str) -> List[str]:
        """Découpe un fichier audio en segments de 10 minutes."""
        audio = AudioSegment.from_file(input_file)
        duration = len(audio)
        
        if duration <= SEGMENT_LENGTH_MS:
            num_segments = 1
        else:
            num_segments = (duration // SEGMENT_LENGTH_MS) + 1
        
        segments = []
        for i in range(num_segments):
            start = i * SEGMENT_LENGTH_MS
            end = min((i + 1) * SEGMENT_LENGTH_MS, duration)
            
            if start >= duration:
                break
            
            segment = audio[start:end]
            segment_path = os.path.join(self.output_dir, f"segment_{i}.mp3")
            segment.export(segment_path, format="mp3")
            segments.append(segment_path)
        
        return segments


# =============================================================================
# FACADE - Classe de compatibilité rétroactive
# =============================================================================

class YouTubeAudioProcessor:
    """
    Façade pour maintenir la compatibilité avec le code existant.
    Délègue aux services spécialisés (SRP).
    """
    
    def __init__(self, output_dir: str, num_segments: int = 10, source: int = 3):
        self.output_dir = output_dir
        self.num_segments = num_segments
        self.source = source
        os.makedirs(output_dir, exist_ok=True)
        
        # Services spécialisés
        self._searcher = YouTubeSearchService()
        self._downloader = YouTubeDownloader(output_dir)
        self._filter = VideoFilter()
        self._extractor = AudioExtractor(output_dir)
    
    # Délégation au YouTubeDownloader
    def download_audio(self, url: str) -> Tuple[str, str, str, Optional[datetime.datetime]]:
        return self._downloader.download_audio(url)
    
    def get_video_info(self, url: str) -> Optional[YouTube]:
        return self._downloader.get_video_info(url)
    
    def check_subtitles(self, url: str) -> Optional[str]:
        return self._downloader.check_subtitles(url)
    
    def get_subtitles(
        self, url: str, code: str
    ) -> Tuple[str, str, str, Optional[datetime.datetime]]:
        return self._downloader.get_subtitles(url, code)
    
    # Délégation au YouTubeSearchService
    def search_subject(self, subject: str) -> List[Any]:
        filters = Filter.create().type(Filter.Type.VIDEO).sort_by(Filter.SortBy.UPLOAD_DATE)
        search = self._searcher.search(subject, filters)
        return self._filter.filter_videos(search.results, duration_mode="any")
    
    def get_search_object(
        self, 
        subject: str, 
        sort_by: str = "relevance", 
        upload_date: Optional[str] = None, 
        exclude_terms: Optional[str] = None
    ) -> Search:
        if exclude_terms:
            terms = exclude_terms.split()
            for term in terms:
                subject += f" -{term}"
        
        filters = self._searcher.create_filters(sort_by, upload_date)
        return self._searcher.search(subject, filters)
    
    def fetch_next(self, search_obj: Search) -> List[Any]:
        return self._searcher.fetch_next(search_obj)
    
    # Délégation au VideoFilter
    def filter_videos(
        self, 
        videos: List[Any], 
        duration_mode: str, 
        days_limit: Optional[int] = None
    ) -> List[Any]:
        return self._filter.filter_videos(videos, duration_mode, days_limit)
    
    # Délégation à l'AudioExtractor
    def extract_audio_from_mp4(self, input_video: str) -> List[str]:
        return self._extractor.extract_audio_from_video(input_video)
    
    def split_audio_equal(self, input_file: str) -> List[str]:
        return self._extractor.split_audio(input_file)
