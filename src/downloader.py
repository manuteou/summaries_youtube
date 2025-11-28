from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix.contrib.search import Search, Filter
from utils import slugify
import os
from moviepy import AudioFileClip
from pydub import AudioSegment


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


def extract_audio_from_mp4(input_video, output_dir="./test_audio", num_segments=10):
    os.makedirs(output_dir, exist_ok=True)
    audio = AudioFileClip(input_video)
    audio_path = f"{output_dir}/full_audio.mp3"
    audio.write_audiofile(audio_path, codec="mp3", bitrate="80k")
    segments = split_audio_equal(audio_path, output_dir, num_segments=num_segments)
    os.remove(audio_path)
    return segments


def split_audio_equal(input_file, output_dir, num_segments=10):
    audio = AudioSegment.from_file(input_file)
    duration = len(audio) 
    segment_length = duration // num_segments

    segments = []
    for i in range(num_segments):
        start = i * segment_length
        end = start + segment_length if i < num_segments - 1 else duration
        segment = audio[start:end]
        segment_path = os.path.join(output_dir, f"segment_{i}.mp3")
        segment.export(segment_path, format="mp3")
        segments.append(segment_path)
    return segments


if __name__ == "__main__":
   
    code = check_subtitles('https://www.youtube.com/watch?v=yoiCjhPAdBA')
    print(code)