import argparse
import os
import warnings


warnings.filterwarnings("ignore")

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm
from ollama import Client
from dotenv import load_dotenv
from pathlib import Path

from downloader import  YouTubeAudioProcessor
from transcriber import WhisperTranscriber
from summarizer import Summarizer
from exporter import Exporter
from utils import clean_files

console = Console()
load_dotenv()

DEVICE = os.getenv("DEVICE")
MODEL = os.getenv("MODEL", "medium")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")
FORMAT = os.getenv("FORMAT")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
FFMPEG_DIR = os.getenv("FFMPEG")

if FFMPEG_DIR:
    os.environ["PATH"] += os.pathsep + FFMPEG_DIR


def get_video_text(url, device, model, transcribe, processor):
    code = processor.check_subtitles(url)
    if code:
        subtitles_file, title, author = processor.get_subtitles(url, code)
        console.print(f"[blue]video a analyser =>[/blue] [yellow4]{title}[/yellow4]")
        console.print("[blue]Sous-titre detectés[/blue]")
        result = transcribe.extract_subtitles(subtitles_file)

    else:
        audio_file, title, author = processor.download_audio(url)
        console.print(f"[blue]video a analyser =>[/blue] [yellow4]{title}[/yellow4]")
        console.print("[yellow]Pas de sous titre detecté[/yellow] -> [green]lancement du transcribe audio[/green]")
        result = transcribe.transcribe_audio(audio_file)

    return result, title, author


def process_single_video(args, summarizer, transcribe, processor, exporter):
    text, source, author = get_video_text(args.url, args.device, args.model, transcribe, processor)
    summary = summarizer.summarize_long_text(text, author)
    md = Markdown(summary)
    console.print(md)
    source_info = [{"title": source, "url": args.url}]
    exporter.save_summary(summary, source, args.format, source_info)


def check_result(text, serach, summarizer):
    check_valide_search = summarizer.check_synthese(text, serach)
    return check_valide_search


def process_multiple_videos(args, summarizer, transcribe, processor, exporter):
    videos = processor.search_subject(args.search)
    texts = []
    if not videos:
        console.print(f"[yellow]Aucune vidéo trouvée pour la recherche : {args.search}[/yellow]")
        console.print("[red]Aucune vidéo sélectionnée. Fin du programme.[/red]")
        return

    selected_videos = []
    for video in videos:
        if len(selected_videos) >= args.limit:
            break

        console.print(f"\n[bold blue]Vidéo trouvée :[/bold blue] {video.title}")
        console.print(f"[dim]Auteur : {video.author} | URL : {video.watch_url}[/dim]")
        
        if Confirm.ask("Voulez-vous traiter cette vidéo ?", default=True, console=console):
            selected_videos.append(video)
        else:
            console.print("[yellow]Vidéo ignorée.[/yellow]")

    if not selected_videos:
        console.print("[red]Aucune vidéo sélectionnée. Fin du programme.[/red]")
        return

    for video in selected_videos:
        text, source, author = get_video_text(video.watch_url, args.device, args.model, transcribe, processor)
        text = summarizer.summarize_long_text(text, author)
        texts.append(f"Source : {source} (Auteur : {author})\n{text}")
    
    check = False
    for attempt in range(3):
        if not check:
            summary = "\n\n== Text suivant ==".join(texts)
        for _ in range(2):
            summary = summarizer.summarize_multi_texts(args.search, summary)
        check = eval(check_result(summary, args.search, summarizer))
        if check:
            break

    summary = summarizer.enhance_markdown(summary)
    md = Markdown(summary)
    console.print(md)
    source_info = [{"title": v.title, "url": v.watch_url} for v in selected_videos]
    exporter.save_summary(summary, args.search, args.format, source_info)


def process_video_path(args, summarizer, transcribe, processor, exporter):
    video_path = Path(args.video_path)
    segments = processor.extract_audio_from_mp4(video_path)
    summary = transcribe.transcribe_segments(segments)
    title = video_path.stem
    summary = "\n\n".join(summary)
    
    # 1. Generate detailed summary (one pass only)
    detailed_summary = summarizer.summarize_long_text(summary, author=title)
    
    # 2. Generate global analysis if type is long
    if args.type == "long":
        global_analysis = summarizer.generate_global_analysis(detailed_summary)
        final_output = f"{global_analysis}\n\n---\n\n# Détails des Sections\n\n{detailed_summary}"
    else:
        final_output = detailed_summary
  
    md = Markdown(final_output)
    console.print(md)
    source_info = [{"title": title, "url": str(video_path.absolute())}]
    exporter.save_summary(final_output, title, args.format, source_info) 


def main():
    parser = argparse.ArgumentParser(description="Résumé ou synthèse de vidéos YouTube")
    parser.add_argument("--url", help="URL d'une vidéo YouTube (mode résumé)")
    parser.add_argument("--video-path",  help="Chemin de la video au format MP4")
    parser.add_argument("--search", help="Terme de recherche YouTube (mode synthèse multi‑vidéos)")
    parser.add_argument("--limit", type=int, default=3, help="Nombre de sources YouTube à rechercher (défaut: 3)")
    parser.add_argument("--device", default=DEVICE, help="Choix du device (cpu ou cuda)")
    parser.add_argument("--model", default=MODEL, help="Taille du modèle Whisper (tiny, base, small, medium, large)")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Dossier de sortie")
    parser.add_argument("--format", default=FORMAT, choices=["md", "txt", "pdf"], help="Format de sortie")
    parser.add_argument("--type", default="short", choices=["short", "medium", "long"], help="Type de résumé : short (concis), medium (équilibré), long (exhaustif)")
    args = parser.parse_args()

    list_path = ["./audio_segments", "./chunk_data", "./segments_text"]
    clean_files(list_path)

    try:
        transcribe = WhisperTranscriber(model_size=args.model, device=args.device)
        processor = YouTubeAudioProcessor(output_dir="./audio_segments", source=args.limit)
        client = Client(host=OLLAMA_HOST)
        summarizer = Summarizer(client, OLLAMA_MODEL, summary_type=args.type)
        exporter = Exporter(args.output_dir)
        
        if args.url:
            process_single_video(args, summarizer, transcribe, processor, exporter)
        elif args.search:
            process_multiple_videos(args, summarizer, transcribe, processor, exporter)
        elif args.video_path:
            process_video_path(args, summarizer, transcribe, processor, exporter)
        else:
            console.print("[red]Erreur : vous devez fournir --url ou --search[/red]")

    except Exception as e:
        console.print(f"[red]Erreur : {e}[/red]")
        raise e

if __name__ == "__main__":
    main()