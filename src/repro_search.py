from downloader import YouTubeAudioProcessor
from rich.console import Console

console = Console()

try:
    processor = YouTubeAudioProcessor(output_dir="./test_output", source=3)
    console.print("Searching for 'Bien reussir parcoursup'...")
    videos = processor.search_subject("Bien reussir parcoursup")
    
    if not videos:
        console.print("[red]No videos found![/red]")
    else:
        console.print(f"[green]Found {len(videos)} videos:[/green]")
        for v in videos:
            console.print(f"- {v.title} ({v.watch_url})")

except Exception as e:
    console.print(f"[red]Error: {e}[/red]")
