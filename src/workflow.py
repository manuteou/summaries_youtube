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
DEBUG = os.getenv("DEBUG", "False")

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

    def _log_debug(self, var_name, content):
        """Helper to log variables to a file if DEBUG is enabled."""
        if DEBUG:
            debug_dir = Path("./debug")
            debug_dir.mkdir(exist_ok=True)
            log_file = debug_dir / "debug_log.txt"
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] {var_name}:\n{content}\n{'-'*40}\n")
            except Exception as e:
                print(f"Failed to write to debug log: {e}")

    def get_video_text(self, url):
        """Extracts text from a video (subtitles or audio transcription)."""
        # Check if it's a local file
        if os.path.exists(url):
            try:
                video_path = Path(url)
                # Use processor to extract audio/split
                segments = self.processor.extract_audio_from_mp4(video_path)
                # Transcribe segments
                texts = self.transcriber.transcribe_segments(segments)
                result = "\n".join(texts)
                
                title = video_path.stem
                author = "Fichier Local"
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                method = "local_mp4"
                return result, title, author, date, method
            except Exception as e:
                print(f"Error processing local file: {e}")
                # Fallback to default (might retry as URL or fail)

        code = self.processor.check_subtitles(url)
        if code:
            subtitles_file, title, author, date = self.processor.get_subtitles(url, code)
            result = self.transcriber.extract_subtitles(subtitles_file)
            method = "subtitles"
        else:
            audio_file, title, author, date = self.processor.download_audio(url)
            result = self.transcriber.transcribe_audio(audio_file)
            method = "audio"
        
        return result, title, author, date, method

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

    def _filter_and_boost_videos(self, videos, duration_mode="any", active_categories=None, enable_boost=True, days_limit=None):
        """Filters videos and applies boosting logic for preferred channels."""
        # Initial filter
        filtered = self.processor.filter_videos(videos, duration_mode, days_limit=days_limit)
        
        if not enable_boost:
            return filtered

        boosted = []
        regular = []
        
        for v in filtered:
            # Monkey-patching for UI
            is_fav = self.is_channel_preferred(v.author, active_categories)
            v.is_boosted = is_fav 
            
            if is_fav:
                boosted.append(v)
            else:
                regular.append(v)
                
        return boosted + regular

    def get_search_results(self, search_obj, duration_mode="any", active_categories=None, enable_boost=True, days_limit=None):
        """Returns filtered results from a search object, with optional channel boosting."""
        raw_results = [v for v in search_obj.results if v not in search_obj.shorts] 
        
        # Initial filter and boost
        processed_videos = self._filter_and_boost_videos(raw_results, duration_mode, active_categories, enable_boost, days_limit)
        
        # Helper to count boosted
        def count_boosted(videos):
            return sum(1 for v in videos if getattr(v, 'is_boosted', False))

        attempts = 0
        max_attempts = 3
        
        # Initial check
        boosted_count = count_boosted(processed_videos) if enable_boost else 0

        while attempts < max_attempts:
            need_more_total = len(processed_videos) < 5
            need_more_boosted = enable_boost and boosted_count < 2
            
            if not (need_more_total or need_more_boosted):
                break

            print(f"DEBUG: Fetching more... Total: {len(processed_videos)}, Boosted: {boosted_count} (Attempt {attempts+1}/{max_attempts})")
            try:
                # Fetch next batch
                new_videos = self.processor.fetch_next(search_obj)
                if not new_videos:
                    break
                    
                # We need to filter and boost the NEW videos, but also de-duplicate against EXISTING
                # Best way is to just add to raw candidates and re-process, but 'processed_videos' is already sorted.
                # So let's filter the new batch and append unique ones.
                
                new_processed = self._filter_and_boost_videos(new_videos, duration_mode, active_categories, enable_boost, days_limit)
                
                current_urls = {v.watch_url for v in processed_videos}
                
                # Append NEW unique videos.
                # Since we want to maintain the "Boosted First" order, if we just append, new boosted videos will be at the end.
                # Ideally we should re-sort everything or insert. For simplicity, we just append and maybe re-sort later if strictly needed,
                # but let's try to keep it simple: merge and re-sort.
                
                combined = processed_videos + [v for v in new_processed if v.watch_url not in current_urls]
                
                # Re-sort/Boost the whole combined list to ensure proper ordering
                # We can't use _filter_and_boost_videos on already processed items easily without double processing logic 
                # (though it is idempotent mostly).
                # Actually, _filter_and_boost_videos calls filter_videos which might be expensive or check metadata.
                # Let's just manually re-sort 'combined' based on is_boosted.
                
                if enable_boost:
                    boosted = [v for v in combined if getattr(v, 'is_boosted', False)]
                    regular = [v for v in combined if not getattr(v, 'is_boosted', False)]
                    processed_videos = boosted + regular
                else:
                    processed_videos = combined

                # Re-check counts
                if enable_boost:
                    boosted_count = count_boosted(processed_videos)

            except Exception as e:
                print(f"Warning: Error fetching more videos: {e}")
                break
            
            attempts += 1
            
        return processed_videos

    def load_more_videos(self, search_obj, duration_mode="any", active_categories=None, enable_boost=True, days_limit=None):
        """Fetches more videos for an existing search session."""
        new_videos = self.processor.fetch_next(search_obj)
        return self._filter_and_boost_videos(new_videos, duration_mode, active_categories, enable_boost, days_limit)

    def get_video_info(self, url):
        """Wrapper for processor.get_video_info"""
        return self.processor.get_video_info(url)

    def synthesize_videos(self, selected_videos, search_term, title_doc):
        """Synthesizes multiple videos into a single document."""
        texts = []
        source_info = []
        final_search_term = search_term if search_term else "est de rédiger une SYNTHÈSE ANALYTIQUE GLOBALE"
        
        # 1. Pre-process all videos (transcribe + summarize individual) ONCE
        print("DEBUG: Starting batch processing of videos...")
        for video in selected_videos:
            try:
                text, title, author, date, method = self.get_video_text(video.watch_url)
                video_summary = self.summarizer.summarize_long_text(text, author)
                texts.append(f"Source : {title} (Auteur : {author}, Date: {date})\n{video_summary}")
                source_info.append({"title": title, "url": video.watch_url, "date": video.publish_date})
            except Exception as e:
                print(f"Error processing video {video.watch_url}: {e}")
                # Continue with others even if one fails
                continue

        if not texts:
            raise Exception("No videos could be processed successfully.")

        summary_of_texts = "\n\n== Text suivant ==".join(texts)
        
        # 2. Retry loop ONLY for the Global Analysis part
        # Pass instructions via a dict
        final_search_term = search_term if search_term else ""
        analysis_input = {
            'content': summary_of_texts,
            'instructions': final_search_term
        }
        
        global_analysis = ""
        
        for attempt in range(3): 
            print(f"DEBUG: Global Analysis Generation - Attempt {attempt+1}")
            try:
                global_analysis = self.summarizer.generate_global_analysis(analysis_input, "global")
                
                # Validate if needed
                check_valide_search = self.summarizer.check_synthese(global_analysis, title_doc)
                check = eval(check_valide_search) # Caveat: eval is risky but kept as requested
                
                if check:
                    break
                else:
                    print(f"DEBUG: Attempt {attempt+1} failed validation.")
            except Exception as e:
                print(f"DEBUG: Error in global analysis generation: {e}")
        
        # Concatenate Global Analysis + Details
        full_summary = global_analysis
        
        return full_summary, final_search_term, source_info

    def refine_summary(self, current_summary, instructions):
        """Refines the summary based on user instructions."""
        return self.summarizer.refine_summary(current_summary, instructions)

    def get_refinement_instruction(self, size_opt, tone_opt, fmt_opt, lang_opt, custom_instr):
        """Builds the instruction string via PromptManager."""
        return self.summarizer.prompt_manager.get_refinement_instruction(size_opt, tone_opt, fmt_opt, lang_opt, custom_instr)


    def process_video_path(self, video_path_str, title):
        """Processes a local video file."""
        video_path = Path(video_path_str)
        segments = self.processor.extract_audio_from_mp4(video_path)
        summary_segments = self.transcriber.transcribe_segments(segments)
    
        self._log_debug("TITLE", title)
        self._log_debug("SEGMENTS", segments)
        
        full_text = "\n\n".join(summary_segments)
        self._log_debug("SUMMARY_SEGMENTS", summary_segments)
        
    
        detailed_summary = self.summarizer.summarize_long_text(full_text, author=title)
        self._log_debug("DETAILED_SUMMARY", detailed_summary)
        
    
        global_analysis = self.summarizer.generate_global_analysis(detailed_summary)
        self._log_debug("GLOBAL_ANALYSIS", global_analysis)
        final_output = f"{global_analysis}\n\n---\n\n# Détails des Sections\n\n{detailed_summary}"
            
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
        list_path = ["./audio_segments", "./chunk_data", "./segments_text"]
        clean_files(list_path)

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
DEBUG = os.getenv("DEBUG", "False")

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

    def _log_debug(self, var_name, content):
        """Helper to log variables to a file if DEBUG is enabled."""
        if DEBUG:
            debug_dir = Path("./debug")
            debug_dir.mkdir(exist_ok=True)
            log_file = debug_dir / "debug_log.txt"
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] {var_name}:\n{content}\n{'-'*40}\n")
            except Exception as e:
                print(f"Failed to write to debug log: {e}")

    def get_video_text(self, url):
        """Extracts text from a video (subtitles or audio transcription)."""
        # Check if it's a local file
        if os.path.exists(url):
            try:
                video_path = Path(url)
                # Use processor to extract audio/split
                segments = self.processor.extract_audio_from_mp4(video_path)
                # Transcribe segments
                texts = self.transcriber.transcribe_segments(segments)
                result = "\n".join(texts)
                
                title = video_path.stem
                author = "Fichier Local"
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                method = "local_mp4"
                return result, title, author, date, method
            except Exception as e:
                print(f"Error processing local file: {e}")
                # Fallback to default (might retry as URL or fail)

        code = self.processor.check_subtitles(url)
        if code:
            subtitles_file, title, author, date = self.processor.get_subtitles(url, code)
            result = self.transcriber.extract_subtitles(subtitles_file)
            method = "subtitles"
        else:
            audio_file, title, author, date = self.processor.download_audio(url)
            result = self.transcriber.transcribe_audio(audio_file)
            method = "audio"
        
        return result, title, author, date, method

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

    def synthesize_videos(self, selected_videos, search_term, title_doc):
        """Synthesizes multiple videos into a single document."""
        texts = []
        source_info = []
        final_search_term = search_term if search_term else "est de rédiger une SYNTHÈSE ANALYTIQUE GLOBALE"
        for attempt in range(3):
            for video in  selected_videos:
                text, title, author, date, method = self.get_video_text(video.watch_url)
                video_summary = self.summarizer.summarize_long_text(text, author)
                texts.append(f"Source : {title} (Auteur : {author}, Date: {date})\n{video_summary}")
                source_info.append({"title": title, "url": video.watch_url, "date": video.publish_date})

            summary_of_texts = "\n\n== Text suivant ==".join(texts)
            
            # Pass instructions via a dict
            final_search_term = search_term if search_term else ""
            analysis_input = {
                'content': summary_of_texts,
                'instructions': final_search_term
            }
            
            global_analysis = self.summarizer.generate_global_analysis(analysis_input, "global")
            
            # Validate if needed (optional, keeping logic similar but maybe less strict on title check)
            check_valide_search = self.summarizer.check_synthese(global_analysis, title_doc)
            check = eval(check_valide_search) # Caveat: eval is risky but keeping legacy logic for now
            if check:
                break
        
        # Concatenate Global Analysis + Details
        # We do NOT run enhance_markdown on the whole thing to avoid losing structure/details
        # But we might want to enhance the global analysis part if it's raw
        
        full_summary = global_analysis
        
        return full_summary, final_search_term, source_info

    def refine_summary(self, current_summary, instructions):
        """Refines the summary based on user instructions."""
        return self.summarizer.refine_summary(current_summary, instructions)

    def get_refinement_instruction(self, size_opt, tone_opt, fmt_opt, lang_opt, custom_instr):
        """Builds the instruction string via PromptManager."""
        return self.summarizer.prompt_manager.get_refinement_instruction(size_opt, tone_opt, fmt_opt, lang_opt, custom_instr)


    def process_video_path(self, video_path_str, title):
        """Processes a local video file."""
        video_path = Path(video_path_str)
        segments = self.processor.extract_audio_from_mp4(video_path)
        summary_segments = self.transcriber.transcribe_segments(segments)
    
        self._log_debug("TITLE", title)
        self._log_debug("SEGMENTS", segments)
        
        full_text = "\n\n".join(summary_segments)
        self._log_debug("SUMMARY_SEGMENTS", summary_segments)
        
   
        detailed_summary = self.summarizer.summarize_long_text(full_text, author=title)
        self._log_debug("DETAILED_SUMMARY", detailed_summary)
        
    
        global_analysis = self.summarizer.generate_global_analysis(detailed_summary)
        self._log_debug("GLOBAL_ANALYSIS", global_analysis)
        final_output = f"{global_analysis}\n\n---\n\n# Détails des Sections\n\n{detailed_summary}"
            
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
        list_path = ["./audio_segments", "./chunk_data", "./segments_text"]
        clean_files(list_path)
