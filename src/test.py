import os
import asyncio
from moviepy import AudioFileClip
from pydub import AudioSegment
from summarizer import summarize_long_text, enhance_markdown
import whisper
import warnings
warnings.filterwarnings("ignore")
from rich.console import Console
from rich.markdown import Markdown
from exporter import save_summary
from ollama import Client
import time
from utils import write_data, load_text
from transcriber import transcribe_audio
from dotenv import load_dotenv
import glob
load_dotenv()

DEVICE = os.getenv("DEVICE")
MODEL = os.getenv("MODEL")


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


def extract_audio_from_mp4(input_video, output_dir="./test_audio", num_segments=10):
    os.makedirs(output_dir, exist_ok=True)
    audio = AudioFileClip(input_video)
    audio_path = f"{output_dir}/full_audio.mp3"
    audio.write_audiofile(audio_path, codec="mp3", bitrate="80k")
    segments = split_audio_equal(audio_path, output_dir, num_segments=num_segments)
    os.remove(audio_path)
    return segments


def transcribe_audio_from_mp4(segments):
    text = []
    start_time = time.time() 
    whisper_model = whisper.load_model(MODEL, device="cpu")
    whisper_model.to(DEVICE)

    for i,segment in enumerate(segments):
        print(f"traitement du segement {i+1} en cours")
        data = transcribe_audio(segment, whisper_model)
        text.append(data)
        write_data(output_dir="./segment_text", data=data,seg=i)
    elapsed = time.time() - start_time
    print(f"\n✅ Transcription terminée : {len(segments)} segments traités en {elapsed:.2f} secondes")
    print(data)
    return data


if __name__ == "__main__":
    EXTRACT_AUDIO = False
    OLLAMA_MODEL="gemma3:4b"
    OLLAMA_HOST="localhost:11434"
    console = Console()
    client = Client(host=OLLAMA_HOST, headers={"x-some-header": "some-value"})
    start_time = time.time() 
    if EXTRACT_AUDIO:
        segments = extract_audio_from_mp4("/home/manu/app/summaries_youtube/src/Réunion Pilotage Direction de campus-20251125_093453-Enregistrement de la réunion.mp4")
        texts = transcribe_audio_from_mp4(segments)
    else:
        files = glob.glob("./segment_text/*")
        texts = load_text(files)
        print(texts)
    all_texts = "\n\n".join(texts)
    for i in range(2):
        summary =  summarize_long_text(all_texts, client, OLLAMA_MODEL, author="Laura")
        write_data(output_dir="./segment_text", data=all_texts,seg=i)
    final_summary = enhance_markdown(summary,client, OLLAMA_MODEL)
    
    md = Markdown(final_summary)
    console.print(md)
    title = 'test'
    save_summary(final_summary, title, "summaries", "md")
