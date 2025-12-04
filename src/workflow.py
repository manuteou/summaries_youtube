import os
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

# Load environment variables
load_dotenv()

# Constants
DEVICE = os.getenv("DEVICE", "cpu")
MODEL = os.getenv("MODEL", "medium")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./summaries")
FORMAT = os.getenv("FORMAT", "md")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
FFMPEG_DIR = os.getenv("FFMPEG")

if FFMPEG_DIR:
    os.environ["PATH"] += os.pathsep + FFMPEG_DIR

warnings.filterwarnings("ignore")

class WorkflowManager:
    def __init__(self, output_dir=OUTPUT_DIR, model=MODEL, device=DEVICE, ollama_model=OLLAMA_MODEL, summary_type="short"):
        self.output_dir = output_dir
        self.model = model
        self.device = device
        self.ollama_model = ollama_model
        self.summary_type = summary_type
        
        # Initialize components
        self.transcribe = WhisperTranscriber(model_size=self.model, device=self.device)
        self.processor = YouTubeAudioProcessor(output_dir="./audio_segments", source=3) # Default limit, can be adjusted
        from ollama import Client
        self.client = Client(host=OLLAMA_HOST)
        self.summarizer = Summarizer(self.client, self.ollama_model, summary_type=self.summary_type)
        self.exporter = Exporter(self.output_dir)

    def get_video_text(self, url):
        """Extracts text from a video (subtitles or audio transcription)."""
        code = self.processor.check_subtitles(url)
        if code:
            subtitles_file, title, author, date = self.processor.get_subtitles(url, code)
            result = self.transcribe.extract_subtitles(subtitles_file)
            method = "subtitles"
        else:
            audio_file, title, author, date = self.processor.download_audio(url)
            result = self.transcribe.transcribe_audio(audio_file)
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

    def init_search(self, query):
        """Initializes a search session."""
        search_obj = self.processor.get_search_object(query)
        # Initial fetch (pytubefix Search object fetches on init usually, or we access results)
        # We return the object to maintain state
        return search_obj

    def get_search_results(self, search_obj):
        """Returns filtered results from a search object."""
        return [v for v in search_obj.results if v not in search_obj.shorts]

    def load_more_videos(self, search_obj):
        """Fetches more videos for an existing search session."""
        return self.processor.fetch_next(search_obj)

    def get_video_info(self, url):
        """Wrapper for processor.get_video_info"""
        return self.processor.get_video_info(url)

    def synthesize_videos(self, selected_videos, search_term):
        """Synthesizes multiple videos into a single document."""
        texts = []
        source_info = []
        
        for video in selected_videos:
            text, title, author, date, method = self.get_video_text(video.watch_url)
            # Summarize each video individually first (long text summary)
            video_summary = self.summarizer.summarize_long_text(text, author)
            texts.append(f"Source : {title} (Auteur : {author}, Date: {date})\n{video_summary}")
            source_info.append({"title": title, "url": video.watch_url, "date": video.publish_date})
        
        # Combine summaries
        check = False
        final_search_term = search_term if search_term else "Synthèse Manuelle"
        
        summary = ""
        # Iterative summarization loop (from original cli.py)
        for attempt in range(3):
            if not check:
                summary = "\n\n== Text suivant ==".join(texts)
            for _ in range(2):
                summary = self.summarizer.summarize_multi_texts(final_search_term, summary)
            
            # Check validity
            check_valide_search = self.summarizer.check_synthese(summary, final_search_term)
            check = eval(check_valide_search)
            if check:
                break

        summary = self.summarizer.enhance_markdown(summary)
        return summary, final_search_term, source_info

    def process_video_path(self, video_path_str, type_summary="short"):
        """Processes a local video file."""
        video_path = Path(video_path_str)
        segments = self.processor.extract_audio_from_mp4(video_path)
        summary_segments = self.transcribe.transcribe_segments(segments)
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

    def cleanup(self):
        """Cleans up temporary files."""
        list_path = ["./audio_segments", "./chunk_data", "./segments_text"]
        clean_files(list_path)
