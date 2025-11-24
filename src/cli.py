import argparse
import os
from rich.console import Console
from rich.markdown import Markdown
from ollama import Client
from dotenv import load_dotenv

from downloader import download_audio, search_subject, check_subtitles, get_subtitles
from transcriber import transcribe_audio, extract_subtitles
from summarizer import summarize_text, summarize_multi_texts
from exporter import save_summary

console = Console()
load_dotenv()

DEVICE = os.getenv("DEVICE", "cpu")
MODEL = os.getenv("MODEL", "tiny")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
FORMAT = os.getenv("FORMAT", "md")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
FFMPEG_DIR = os.getenv("FFMPEG")

if FFMPEG_DIR:
    os.environ["PATH"] += os.pathsep + FFMPEG_DIR


def main():
    parser = argparse.ArgumentParser(description="Résumé ou synthèse de vidéos YouTube")
    parser.add_argument("--url", help="URL d'une vidéo YouTube (mode résumé)")
    parser.add_argument("--search", help="Terme de recherche YouTube (mode synthèse multi‑vidéos)")
    parser.add_argument("--device", default=DEVICE, help="Choix du device (cpu ou cuda)")
    parser.add_argument("--model", default=MODEL, help="Taille du modèle Whisper (tiny, base, small, medium, large)")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Dossier de sortie")
    parser.add_argument("--format", default=FORMAT, choices=["md", "txt"], help="Format de sortie")
    args = parser.parse_args()

   

    try:
        client = Client(host=OLLAMA_HOST, headers={"x-some-header": "some-value"})

        # --- Mode résumé d'une seule vidéo ---
        if args.url:
            code = check_subtitles(args.url)
            if code:
                print("Sous-titre detectés")
                subtitles_file, title, author = get_subtitles(args.url, code)
                result = extract_subtitles(subtitles_file)

            else:
                print("pas de sous titre detecté -> lancement du transcribe audio")
                audio_file, title, author = download_audio(args.url)
                result = transcribe_audio(audio_file, device=args.device, model_size=args.model)
            
            summary = summarize_text(result["text"], client, OLLAMA_MODEL, author)
            md = Markdown(summary)
            console.print(md)
            save_summary(summary, title, args.output_dir, args.format)

        # --- Mode synthèse multi‑vidéos ---
        elif args.search:
            title = args.search
            videos = search_subject(title)
            audios = [download_audio(video.watch_url) for video in videos]

            texts = []
            for audio in audios:
                result = transcribe_audio(audio[0], device=args.device, model_size=args.model)
                texts.append(f"Source : {audio[1]} (Auteur : {audio[2]})\n{result['text']}")

            all_texts = "\n\n".join(texts)
            summary = summarize_multi_texts(all_texts, client, OLLAMA_MODEL)

            md = Markdown(summary)
            console.print(md)
            save_summary(summary, title, args.output_dir, args.format)

        else:
            console.print("[red]Erreur : vous devez fournir --url ou --search[/red]")

    except Exception as e:
        console.print(f"[red]Erreur : {e}[/red]")


if __name__ == "__main__":
    main()