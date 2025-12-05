
import os
from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix.contrib.search import Search, Filter
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
        yt = YouTube(url, on_progress_callback=on_progress)
        ys = yt.streams.get_audio_only()
        safe_title = slugify(yt.title)
        filename = f"{safe_title}.m4a"
        audio_file = ys.download(output_path=self.output_dir, filename=filename)
        return audio_file, yt.title, yt.author, yt.publish_date

    def get_video_info(self, url: str):
        try:
            yt = YouTube(url)
            return yt
        except Exception as e:
            print(f"Erreur lors de la récupération des infos : {e}")
            return None

    def search_subject(self, subject: str):
        filters = Filter.create().type(Filter.Type.VIDEO).sort_by(Filter.SortBy.UPLOAD_DATE)
        s = Search(subject, filters=filters)
        non_shorts = [v for v in s.results if v not in s.shorts]
        return non_shorts

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

    def filter_videos(self, videos, duration_mode):
        if not duration_mode or duration_mode == "any":
            return videos
            
        filtered = []
        for v in videos:
            try:
                length = v.length
                if duration_mode == "short" and length < 300: # < 5 min
                    filtered.append(v)
                elif duration_mode == "medium" and 300 <= length <= 1200: # 5-20 min
                    filtered.append(v)
                elif duration_mode == "long" and length > 1200: # > 20 min
                    filtered.append(v)
            except Exception:
                # If length is not available, keep it to be safe or skip? 
                # Keeping it might be better than losing valid results.
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
        audio_path = os.path.join(self.output_dir, "full_audio.mp3")
        
        command = [
            "ffmpeg",
            "-i", input_video,
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "80k",
            "-y",
            audio_path
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
