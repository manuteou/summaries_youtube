from pytubefix import YouTube
from pytubefix.cli import on_progress

def download_audio(url: str) -> tuple[str, str]:
    yt = YouTube(url, on_progress_callback=on_progress)
    ys = yt.streams.get_audio_only()
    audio_file = ys.download()
    return audio_file, yt.title