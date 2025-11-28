
import os
from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix.contrib.search import Search, Filter
from moviepy import AudioFileClip
from pydub import AudioSegment
from utils import slugify

class YouTubeAudioProcessor:
    def __init__(self, output_dir: str = "./downloads", num_segments: int = 10):
        self.output_dir = output_dir
        self.num_segments = num_segments
        os.makedirs(output_dir, exist_ok=True)

    def download_audio(self, url: str) -> tuple[str, str, str]:
        yt = YouTube(url, on_progress_callback=on_progress)
        ys = yt.streams.get_audio_only()
        safe_title = slugify(yt.title)
        filename = f"{safe_title}.m4a"
        audio_file = ys.download(filename=filename)
        return audio_file, yt.title, yt.author

    def search_subject(self, subject: str):
        filters = Filter.create().type(Filter.Type.VIDEO)
        s = Search(subject, filters=filters)
        non_shorts = [v for v in s.results if v not in s.shorts]
        return non_shorts[:5]

    def check_subtitles(self, url: str):
        yt = YouTube(url, on_progress_callback=on_progress)
        cles_fr = [cle for cle in yt.captions.keys() if "fr" in cle.code or "en" in cle.code]
        return cles_fr[0].code if cles_fr else None

    def get_subtitles(self, url: str, code: str):
        yt = YouTube(url, on_progress_callback=on_progress)
        caption = yt.captions[code]
        title = yt.title if yt.title else "inconnue"
        return caption.generate_srt_captions(), title, yt.author

    def extract_audio_from_mp4(self, input_video: str) -> list[str]:
        audio_path = os.path.join(self.output_dir, "full_audio.mp3")
        audio = AudioFileClip(input_video)
        audio.write_audiofile(audio_path, codec="mp3", bitrate="80k")
        segments = self.split_audio_equal(audio_path)
        os.remove(audio_path)
        return segments

    def split_audio_equal(self, input_file: str) -> list[str]:
        audio = AudioSegment.from_file(input_file)
        duration = len(audio)
        segment_length = duration // self.num_segments
        segments = []
        for i in range(self.num_segments):
            start = i * segment_length
            end = start + segment_length if i < self.num_segments - 1 else duration
            segment = audio[start:end]
            segment_path = os.path.join(self.output_dir, f"segment_{i}.mp3")
            segment.export(segment_path, format="mp3")
            segments.append(segment_path)
            return segments
