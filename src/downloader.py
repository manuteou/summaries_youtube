import os
import datetime
import time
from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix.contrib.search import Search, Filter
from pytubefix.exceptions import RegexMatchError
import subprocess
from pydub import AudioSegment
from utils import slugify

class YouTubeAudioProcessor:
    def __init__(self, output_dir: str, num_segments: int = 10, source: int = 3):
        self.output_dir = output_dir
        self.num_segments = num_segments
        self.source = source
        os.makedirs(output_dir, exist_ok=True)

    def download_audio(self, url: str) -> tuple[str, str, str, str]:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                yt = YouTube(url, on_progress_callback=on_progress)
                ys = yt.streams.get_audio_only()
                safe_title = slugify(yt.title)
                filename = f"{safe_title}.m4a"
                audio_file = ys.download(output_path=self.output_dir, filename=filename)
                return audio_file, yt.title, yt.author, yt.publish_date
            except Exception as e:
                print(f"Details of retry {attempt+1}/{max_retries} : {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)
        return "", "", "", ""

    def get_video_info(self, url: str):
        try:
            yt = YouTube(url)
            return yt
        except RegexMatchError:
             print(f"Erreur : URL YouTube invalide ou vidéo non trouvée ('{url}')")
             return None
        except Exception as e:
            print(f"Erreur lors de la récupération des infos : {e}")
            return None

    def search_subject(self, subject: str):
        filters = Filter.create().type(Filter.Type.VIDEO).sort_by(Filter.SortBy.UPLOAD_DATE)
        s = Search(subject, filters=filters)
        # raw_results = [v for v in s.results if v not in s.shorts] # Shorts filter is already good
      
        return self.filter_videos(s.results, duration_mode="any")

    def get_search_object(self, subject: str, sort_by: str = "relevance", upload_date: str = None, exclude_terms: str = None):
        if exclude_terms:
            terms = exclude_terms.split()
            for term in terms:
                subject += f" -{term}"

        filters = Filter.create().type(Filter.Type.VIDEO)
        
        if sort_by == "date":
            filters = filters.sort_by(Filter.SortBy.UPLOAD_DATE)
        elif sort_by == "views":
            filters = filters.sort_by(Filter.SortBy.VIEW_COUNT)
        else:
            filters = filters.sort_by(Filter.SortBy.RELEVANCE)
            
        if upload_date == "today":
            filters = filters.upload_date(Filter.UploadDate.TODAY)
        elif upload_date == "week":
            filters = filters.upload_date(Filter.UploadDate.THIS_WEEK)
        elif upload_date == "month":
            filters = filters.upload_date(Filter.UploadDate.THIS_MONTH)
        elif upload_date == "year":
            filters = filters.upload_date(Filter.UploadDate.THIS_YEAR)
            
        return Search(subject, filters=filters)

    def filter_videos(self, videos, duration_mode, days_limit=None):
        # We always filter out shorts (less than 120s typically, or strictly shorts)
        filtered = []
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Helper function for parallel processing
        def get_meta(v):
            try:
                # Pre-fetch all attributes to ensure they are cached in the object
                # and to validate they exist.
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
            except Exception as e:
                # Optional: print error for debugging
                # print(f"Meta fetch error for {v}: {e}")
                return {"success": False}

        # 1. Extraction des métadonnées en parallèle
        import concurrent.futures
        videos_metadata = []
        
        # Use ThreadPoolExecutor to fetch metadata in parallel
        # max_workers=10 or 20 is reasonable for IO bound
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_video = {executor.submit(get_meta, v): v for v in videos}
            for future in concurrent.futures.as_completed(future_to_video):
                res = future.result()
                if res["success"]:
                    videos_metadata.append(res)
        
        # 2. Filtrage via le dictionnaire
        for item in videos_metadata:
            v = item["video"]
            length = item["length"]
            pub_date = item["publish_date"]
            
            # Explicitly attach metadata for UI persistence
            v.title_attr = item["title"]
            v.author_attr = item["author"]
            v.thumb_attr = item["thumbnail_url"]
            v.views_attr = item["views"]
            v.length_attr = item["length"]
            v.publish_date_attr = item["publish_date"]
            v.description_attr = item["description"]

            # Global Safety Check (> 120s)
            if length < 120:
                continue
            
            # Date Check
            if days_limit and pub_date:
                if pub_date.tzinfo is None:
                    # Assume UTC if naive
                    pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)
                
                age = now - pub_date
                if age.days > days_limit:
                    continue

            # Duration Mode Logic
            if not duration_mode or duration_mode == "any":
                filtered.append(v)
            elif duration_mode == "short" and length < 300: # < 5 min
                filtered.append(v)
            elif duration_mode == "medium" and 300 <= length <= 1200: # 5-20 min
                filtered.append(v)
            elif duration_mode == "long" and length > 1200: # > 20 min
                filtered.append(v)
                
        return filtered

    def fetch_next(self, search_obj):
        search_obj.get_next_results()
        return [v for v in search_obj.results if v not in search_obj.shorts]

    def check_subtitles(self, url: str):
        yt = YouTube(url, on_progress_callback=on_progress)
        cles_fr = [cle for cle in yt.captions.keys() if "fr" in cle.code or "en" in cle.code]
        return cles_fr[0].code if cles_fr else None

    def get_subtitles(self, url: str, code: str):
        yt = YouTube(url, on_progress_callback=on_progress)
        caption = yt.captions[code]
        title = yt.title if yt.title else "inconnue"
        return caption.generate_srt_captions(), title, yt.author, yt.publish_date

    def extract_audio_from_mp4(self, input_video: str) -> list[str]:
        audio_path = os.path.join(self.output_dir, "full_audio.flac")
        
        command = [
            "ffmpeg",
            "-i", input_video,
            "-vn",
            "-acodec", "flac",
            "-ar", "16000",
            "-compression_level", "0",
            "-y",
            audio_path
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
             if os.path.exists(audio_path): os.remove(audio_path)
             raise Exception("Extraction audio échouée : Fichier audio vide ou non créé.")

        segments = self.split_audio_equal(audio_path)
        os.remove(audio_path)
        return segments

    def split_audio_equal(self, input_file: str) -> list[str]:
        audio = AudioSegment.from_file(input_file)
        duration = len(audio)
        # 10 minutes in milliseconds
        segment_length = 10 * 60 * 1000
        
        # If video is shorter than segment_length, keep it as one segment
        if duration <= segment_length:
            num_segments = 1
        else:
            num_segments = (duration // segment_length) + 1

        segments = []
        for i in range(num_segments):
            start = i * segment_length
            end = min((i + 1) * segment_length, duration)
            
            # Avoid creating empty segment if duration is exact multiple
            if start >= duration:
                break
                
            segment = audio[start:end]
            segment_path = os.path.join(self.output_dir, f"segment_{i}.mp3")
            segment.export(segment_path, format="mp3")
            segments.append(segment_path)
        return segments
