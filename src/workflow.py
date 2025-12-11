import os
import datetime
import warnings
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from dotenv import load_dotenv

from downloader import YouTubeAudioProcessor
from transcriber import WhisperTranscriber
from summarizer import Summarizer
from exporter import Exporter
from utils import clean_files, time_since
from prompts import PromptManager

# Load environment variables
load_dotenv()

# Constants
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

from config import PREFERRED_CHANNELS

class WorkflowManager:
    def __init__(self, processor, transcriber, summarizer, exporter):
        # Dependencies injected
        self.processor = processor
        self.transcriber = transcriber
        self.summarizer = summarizer
        self.exporter = exporter

    def get_video_text(self, url):
        """Extracts text from a video (subtitles or audio transcription)."""
        is_local = False
        # Better heuristic for local files vs URLs
        if os.path.exists(url) or (not url.startswith("http") and not "youtube.com" in url and not "youtu.be" in url):
             is_local = True

        if is_local:
            try:
                if not os.path.exists(url):
                     raise FileNotFoundError(f"Fichier local introuvable : {url}")

                video_path = Path(url)
                # Use processor to extract audio/split
                segments = self.processor.extract_audio_from_mp4(video_path)
                
                if not segments:
                     raise Exception("Aucun segment audio extrait.")

                # Transcribe segments
                texts = self.transcriber.transcribe_segments(segments)
                result = "\n".join(texts)
                
                if not result.strip():
                     raise Exception("La transcription est vide (pas de voix détectée ?).")

                title = video_path.stem
                author = "Fichier Local"
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                method = "local_mp4"
                return result, title, author, date, method
            except Exception as e:
                print(f"Error processing local file: {e}")
                raise Exception(f"Échec du traitement fichier local : {e}")

        # YouTube Logic (Only if NOT local)
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
             raise Exception(f"Échec traitement YouTube : {e}")

    def process_single_video(self, url):
        """Processes a single video and returns the summary."""
        text, title, author, date, method = self.get_video_text(url)
        summary = self.summarizer.summarize_long_text(text, author)
        
        source_info = [{"title": title, "url": url, "date": date}]
        return summary, title, source_info

    def search_videos(self, query, limit=3):
        """Searches for videos and returns a list of video objects."""
        videos = self.processor.search_subject(query)
        if not videos:
            return []
        return videos[:limit]

    def init_search(self, query, sort_by="relevance", upload_date=None, exclude_terms=None):
        """Initializes a search session."""
        search_obj = self.processor.get_search_object(query, sort_by, upload_date, exclude_terms)
        # Initial fetch (pytubefix Search object fetches on init usually, or we access results)
        # We return the object to maintain state
        return search_obj

    def is_channel_preferred(self, channel_name, active_categories):
        """Checks if a channel is in the preferred list for the active categories."""
        if not channel_name:
            return False
            
        # If no categories are active, check ALL preferred channels
        categories_to_check = active_categories if active_categories else PREFERRED_CHANNELS.keys()
            
        for category in categories_to_check:
            if category in PREFERRED_CHANNELS:
                for preferred in PREFERRED_CHANNELS[category]:
                    if preferred.lower() in channel_name.lower():
                        return True
        return False

    def get_search_results(self, search_obj, duration_mode="any", active_categories=None, enable_boost=True, days_limit=None):
        """Returns filtered results from a search object, with optional channel boosting."""
        raw_results = [v for v in search_obj.results if v not in search_obj.shorts]
        # Initial filter
        filtered = self.processor.filter_videos(raw_results, duration_mode, days_limit=days_limit)
        
        # Helper to count boosted in current list
        def count_boosted(videos):
            return sum(1 for v in videos if self.is_channel_preferred(v.author, active_categories))

        # Smart Retrieval Loop: If we don't have enough results after filtering, fetch more pages
        # Goal: Try to get at least 5 results, OR if boost is on, at least 2 trusted sources
        attempts = 0
        max_attempts = 3
        
        # Initial check
        boosted_count = count_boosted(filtered) if enable_boost else 0

        while attempts < max_attempts:
            # Conditions to continue fetching:
            # 1. Not enough total results (< 5)
            # 2. Boost enabled AND not enough trusted sources (< 2)
            need_more_total = len(filtered) < 5
            need_more_boosted = enable_boost and boosted_count < 2
            
            if not (need_more_total or need_more_boosted):
                break

            print(f"DEBUG: Fetching more... Total: {len(filtered)}, Boosted: {boosted_count} (Attempt {attempts+1}/{max_attempts})")
            try:
                # Fetch next batch
                new_videos = self.processor.fetch_next(search_obj)
                if not new_videos:
                    break
                    
                # Filter new batch
                new_filtered = self.processor.filter_videos(new_videos, duration_mode, days_limit=days_limit)
                
                # Add unique new videos
                current_urls = {v.watch_url for v in filtered}
                for v in new_filtered:
                    if v.watch_url not in current_urls:
                        filtered.append(v)
                
                # Re-check counts
                if enable_boost:
                    boosted_count = count_boosted(filtered)

            except Exception as e:
                print(f"Warning: Error fetching more videos: {e}")
                break
            
            attempts += 1
            
        # Boost preferred channels
        if enable_boost:
            boosted = []
            regular = []
            for v in filtered:
                # Add a dynamic property 'is_boosted' to the object for UI usage
                # Note: pytube objects might not like new attributes, stick to re-ordering first
                # We can wrap or just re-order. To pass to UI, we might need to set it.
                is_fav = self.is_channel_preferred(v.author, active_categories)
                v.is_boosted = is_fav # Monkey-patching for UI
                
                if is_fav:
                    boosted.append(v)
                else:
                    regular.append(v)
            return boosted + regular
            
        return filtered

    def load_more_videos(self, search_obj, duration_mode="any", active_categories=None, enable_boost=True, days_limit=None):
        """Fetches more videos for an existing search session."""
        new_videos = self.processor.fetch_next(search_obj)
        filtered = self.processor.filter_videos(new_videos, duration_mode, days_limit=days_limit)
        
        if enable_boost:
            boosted = []
            regular = []
            for v in filtered:
                is_fav = self.is_channel_preferred(v.author, active_categories)
                v.is_boosted = is_fav
                if is_fav:
                    boosted.append(v)
                else:
                    regular.append(v)
            return boosted + regular
            
        return filtered

    def get_video_info(self, url):
        """Wrapper for processor.get_video_info"""
        return self.processor.get_video_info(url)

    def synthesize_videos(self, selected_videos, search_term, title_override=None):
        """Synthesizes multiple videos into a single document."""
        texts = []
        source_info = []
        
        for vid in selected_videos:
            # vid is an object (YouTube or LocalVideo), not a dict
            url = vid.watch_url
            title = vid.title
            summary_text, _, _ = self.process_video_path(url)
            texts.append(f"Source: {title}\n{summary_text}")
            source_info.append(vid)

        final_search_term = search_term if search_term else "Synthèse Manuelle"
        prompt_context = title_override if title_override else final_search_term
        summary = "\n\n== Text suivant ==".join(texts)
        
        for attempt in range(3):
            if self.summarizer.summary_type in ["meeting"]:
                for _ in range(2):
                    summary = self.summarizer.summarize_multi_texts(prompt_context, summary)
                    summary = "\n\n== Text suivant ==".join(summary)

            else:
                summary = self.summarizer.summarize_multi_texts(prompt_context, summary)
            
        
                   
            # Check validity
            check_valide_search = self.summarizer.check_synthese(summary, prompt_context)
            check = eval(check_valide_search)
            if check:
                break

        summary = self.summarizer.enhance_markdown(summary)
        return summary, final_search_term, source_info

    def refine_summary(self, current_summary, instructions):
        """Refines the summary based on user instructions."""
        return self.summarizer.refine_summary(current_summary, instructions)

    def process_video_path(self, video_path_str, type_summary="short"):
        """Processes a local video file."""
        video_path = Path(video_path_str)
        segments = self.processor.extract_audio_from_mp4(video_path)
        summary_segments = self.transcriber.transcribe_segments(segments)
        title = video_path.stem
        full_text = "\n\n".join(summary_segments)
        
        # 1. Generate detailed summary
        detailed_summary = self.summarizer.summarize_long_text(full_text, author=title)
        
        # 2. Generate global analysis if type is long
        if type_summary == "long":
            global_analysis = self.summarizer.generate_global_analysis(detailed_summary)
            final_output = f"{global_analysis}\n\n---\n\n# Détails des Sections\n\n{detailed_summary}"
        else:
            final_output = detailed_summary
            
        source_info = [{"title": title, "url": str(video_path.absolute())}]
        return final_output, title, source_info

    def save_summary(self, summary, title, fmt, source_info):
        """Saves the summary using the exporter."""
        return self.exporter.save_summary(summary, title, fmt, source_info)

    def get_pdf_bytes(self, summary, title, source_info):
        """Generates PDF bytes for download."""
        return self.exporter.generate_pdf_bytes(summary, title, source_info)

    def cleanup(self):
        """Cleans up temporary files."""
        list_path = ["./audio_segments", "./chunk_data"]
        clean_files(list_path)
