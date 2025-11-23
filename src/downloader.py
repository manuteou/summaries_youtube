from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix.contrib.search import Search, Filter
from utils import slugify

def download_audio(url: str) -> tuple[str, str, str]:
    yt = YouTube(url, on_progress_callback=on_progress)
    ys = yt.streams.get_audio_only()
    safe_title = slugify(yt.title)
    filename = f"{safe_title}.m4a"
    audio_file = ys.download(filename=filename)
    return audio_file, yt.title, yt.author

def search_subject(subject):
    filters =(
        Filter.create()
        .type(Filter.Type.VIDEO)
    )

    s = Search(f"{subject}", filters=filters)
    non_shorts = [v for v in s.results if v not in s.shorts]
    return non_shorts[:5]


if __name__ == "__main__":
   
    s = search_subject("les dernieres info de Ukraine")
    audios = [download_audio(video.watch_url) for video in s]
    