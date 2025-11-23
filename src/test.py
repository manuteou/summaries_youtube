import os
from rich.console import Console
from rich.markdown import Markdown
from ollama import Client

from downloader import download_audio, search_subject
from transcriber import transcribe_audio
from summarizer import summarize_multi_texts
from exporter import save_summary
from dotenv import load_dotenv


console = Console()
load_dotenv()

DEVICE = os.getenv("DEVICE", "cpu")
MODEL = os.getenv("MODEL", "tiny")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
FORMAT = os.getenv("FORMAT", "md")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
FFMPEG_DIR = os.getenv("FFMPEG")


os.environ["PATH"] += os.pathsep + FFMPEG_DIR

title = "l'info politique en france"
s = search_subject(title)
for ss in s : print(ss.watch_url)

audios = [download_audio(video.watch_url) for video in s]

texts = []
for audio in audios:
    result = transcribe_audio(audio[0], device=DEVICE, model_size=MODEL)
    texts.append(f"Source : {audio[1]} (Auteur : {audio[2]})\n{result['text']}")

for text in texts: print(text)

all_texts = "\n\n".join(texts)
client = Client(host=OLLAMA_HOST)
summary = summarize_multi_texts(all_texts, client, OLLAMA_MODEL)

md = Markdown(summary)
console.print(md)
save_summary(summary, title, OUTPUT_DIR, FORMAT)
