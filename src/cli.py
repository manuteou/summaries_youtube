import argparse
import os
from rich.console import Console
from rich.markdown import Markdown
from ollama import Client

from downloader import download_audio
from transcriber import transcribe_audio
from summarizer import summarize_text
from exporter import save_summary
from dotenv import load_dotenv

console = Console()
load_dotenv()
DEVICE = os.getenv("DEVICE")
MODEL = os.getenv("MODEL")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")
FORMAT = os.getenv("FORMAT")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
FFMPEG_DIR = os.getenv("FFMPEG") 

os.environ["PATH"] += os.pathsep + FFMPEG_DIR

def main():
    parser = argparse.ArgumentParser(description="Résumé d'une vidéo YouTube à partir de son audio")
    parser.add_argument("--url", required=True, help="URL de la vidéo YouTube")
    parser.add_argument("--device", default=DEVICE, help="Choix du device (cpu ou cuda)")
    parser.add_argument("--model", default=MODEL, help="Taille du modèle Whisper (tiny, base, small, medium, large)")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Dossier de sortie")
    parser.add_argument("--format", default=FORMAT, choices=["md", "txt"], help="Format de sortie")
    args = parser.parse_args()

    try:
        
        audio_file, title = download_audio(args.url)
        result = transcribe_audio(audio_file, device=args.device, model_size=args.model)

        client = Client(host=OLLAMA_HOST, headers={"x-some-header": "some-value"})
        summary = summarize_text(result["text"], client, OLLAMA_MODEL)

        md = Markdown(summary)
        console.print(md)

        save_summary(summary, title, args.output_dir, args.format)

    except Exception as e:
        console.print(f"[red]Erreur : {e}[/red]")

if __name__ == "__main__":
    main()
