import argparse
import os
import warnings


warnings.filterwarnings("ignore")

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
import webbrowser
from ollama import Client
from dotenv import load_dotenv
from pathlib import Path

from downloader import  YouTubeAudioProcessor
from transcriber import WhisperTranscriber
from summarizer import Summarizer
from exporter import Exporter
from exporter import Exporter
from utils import clean_files, time_since

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
        subtitles_file, title, author, date = processor.get_subtitles(url, code)
        console.print(f"[blue]video a analyser =>[/blue] [yellow4]{title}[/yellow4] [dim]({date})[/dim]")
        console.print("[blue]Sous-titre detectés[/blue]")
        result = transcribe.extract_subtitles(subtitles_file)

    else:
        audio_file, title, author, date = processor.download_audio(url)
        console.print(f"[blue]video a analyser =>[/blue] [yellow4]{title}[/yellow4] [dim]({date})[/dim]")
        console.print("[yellow]Pas de sous titre detecté[/yellow] -> [green]lancement du transcribe audio[/green]")
        result = transcribe.transcribe_audio(audio_file)

    return result, title, author, date


def process_single_video(args, summarizer, transcribe, processor, exporter):
    text, source, author, date = get_video_text(args.url, args.device, args.model, transcribe, processor)
    summary = summarizer.summarize_long_text(text, author)
    md = Markdown(summary)
    console.print(md)
    source_info = [{"title": source, "url": args.url, "date": date}]
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
        relative_date = time_since(video.publish_date)
        duration_min = video.length // 60
        duration_sec = video.length % 60
        duration_str = f"{duration_min}m{duration_sec:02d}s"
        console.print(f"[dim]Auteur : {video.author} | Date : {relative_date} | Durée : {duration_str} | URL : {video.watch_url}[/dim]")
        
        while True:
            choice = Prompt.ask(
                f"Voulez-vous traiter cette vidéo ? [dim](y)es / (n)o / (p)review / (d)ecription / (q)uit[/dim]",
                choices=["y", "n", "p", "d", "q"],
                default="y",
                console=console
            )

            if choice == "p":
                webbrowser.open(video.watch_url)
                console.print("[blue]Ouverture de la vidéo dans le navigateur...[/blue]")
                continue
            elif choice == "d":
                description = getattr(video, "description", None)
                if not description:
                     try:
                         description = video.description
                     except:
                         description = "Description non disponible."
                
                console.print(f"\n[bold]Description :[/bold]\n{description}\n")
                continue
            elif choice == "q":
                console.print("[red]Arrêt de la sélection.[/red]")
                return
            elif choice == "y":
                selected_videos.append(video)
                break
            elif choice == "n":
                console.print("[yellow]Vidéo ignorée.[/yellow]")
                break

    if not selected_videos:
        console.print("[red]Aucune vidéo sélectionnée. Fin du programme.[/red]")
        return

    synthesize_videos(selected_videos, args, summarizer, transcribe, processor, exporter)


def synthesize_videos(selected_videos, args, summarizer, transcribe, processor, exporter):
    texts = []
    for video in selected_videos:
        text, source, author, date = get_video_text(video.watch_url, args.device, args.model, transcribe, processor)
        text = summarizer.summarize_long_text(text, author)
        texts.append(f"Source : {source} (Auteur : {author}, Date: {date})\n{text}")
    
    check = False
    search_term = args.search if args.search else "Synthèse Manuelle"
    
    for attempt in range(3):
        if not check:
            summary = "\n\n== Text suivant ==".join(texts)
        for _ in range(2):
            summary = summarizer.summarize_multi_texts(search_term, summary)
        check = eval(check_result(summary, search_term, summarizer))
        if check:
            break

    summary = summarizer.enhance_markdown(summary)
    md = Markdown(summary)
    console.print(md)
    source_info = [{"title": v.title, "url": v.watch_url, "date": v.publish_date} for v in selected_videos]
    exporter.save_summary(summary, search_term, args.format, source_info)


def process_manual_videos(args, summarizer, transcribe, processor, exporter):
    selected_videos = []
    while True:
        url = Prompt.ask("\n[bold green]Entrez une URL YouTube (ou 's' pour lancer la synthèse, 'q' pour quitter)[/bold green]", console=console)
        
        if url.lower() == 'q':
            console.print("[red]Arrêt du programme.[/red]")
            return
        elif url.lower() == 's':
            if not selected_videos:
                console.print("[yellow]Aucune vidéo dans la liste. Ajoutez des URL d'abord.[/yellow]")
                continue
            break
        
        console.print("[blue]Récupération des informations...[/blue]")
        video = processor.get_video_info(url)
        
        if video:
            console.print(f"\n[bold blue]Vidéo trouvée :[/bold blue] {video.title}")
            relative_date = time_since(video.publish_date)
            duration_min = video.length // 60
            duration_sec = video.length % 60
            duration_str = f"{duration_min}m{duration_sec:02d}s"
            console.print(f"[dim]Auteur : {video.author} | Date : {relative_date} | Durée : {duration_str}[/dim]")
            
            if Confirm.ask("Ajouter cette vidéo à la liste ?", default=True):
                selected_videos.append(video)
                console.print(f"[green]Vidéo ajoutée ! ({len(selected_videos)} vidéos dans la liste)[/green]")
            else:
                console.print("[yellow]Vidéo ignorée.[/yellow]")
        else:
            console.print("[red]Impossible de récupérer les infos de la vidéo. Vérifiez l'URL.[/red]")

    if selected_videos:
        console.print(f"\n[bold green]Lancement de la synthèse pour {len(selected_videos)} vidéos...[/bold green]")
        synthesize_videos(selected_videos, args, summarizer, transcribe, processor, exporter)


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
    parser.add_argument("--manual", action="store_true", help="Mode saisie manuelle de vidéos")
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
        elif args.manual:
            process_manual_videos(args, summarizer, transcribe, processor, exporter)
        else:
            console.print("[red]Erreur : vous devez fournir --url, --search, --video-path ou --manual[/red]")

    except Exception as e:
        console.print(f"[red]Erreur : {e}[/red]")
        raise e
    finally:
        clean_files(list_path)

if __name__ == "__main__":
    main()