from pytubefix import YouTube
from pytubefix.cli import on_progress
from utils import slugify

def download_audio(url: str) -> tuple[str, str]:
    yt = YouTube(url, on_progress_callback=on_progress)
    ys = yt.streams.get_audio_only()
    safe_title = slugify(yt.title)
    filename = f"{safe_title}.m4a"
    audio_file = ys.download(filename=filename)
    return audio_file, yt.title