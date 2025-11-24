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


def check_subtitles(url):
    yt = YouTube(url, on_progress_callback=on_progress)
    cles_fr = [cle for cle in yt.captions.keys() if "fr" in cle.code or "en" in cle.code]
    if len(cles_fr) == 0:
        return None
    return cles_fr[0].code


def get_subtitles(url, code):
    yt = YouTube(url, on_progress_callback=on_progress)
    caption = yt.captions[code]
    if yt.title is None:
        return caption.generate_srt_captions(), "inconnue", yt.author
    return caption.generate_srt_captions(), yt.title, yt.author

if __name__ == "__main__":
   
    code = check_subtitles('https://www.youtube.com/watch?v=yoiCjhPAdBA')
    print(code)