from rich.prompt import Confirm
from rich.console import Console

console = Console()

console.print("Testing Confirm.ask...")
if Confirm.ask("Do you see this prompt?", default=True):
    console.print("[green]User said Yes[/green]")
else:
    console.print("[red]User said No[/red]")
