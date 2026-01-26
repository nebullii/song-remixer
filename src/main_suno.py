"""Song Remixer CLI - Simplified Suno-only pipeline."""

import subprocess
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .suno_generator import generate_song_suno

console = Console()


def parse_user_input(user_input: str) -> tuple[str, str, str]:
    """Parse user input to extract song, artist, and optional style."""
    user_input = user_input.strip()
    style = "pop, catchy"

    # Check for style hints in parentheses
    if "(" in user_input and user_input.endswith(")"):
        style_start = user_input.rfind("(")
        style = user_input[style_start + 1:-1].strip()
        user_input = user_input[:style_start].strip()

    # Try different separators
    if " by " in user_input.lower():
        idx = user_input.lower().index(" by ")
        album = user_input[:idx].strip()
        artist = user_input[idx + 4:].strip()
    elif " - " in user_input:
        parts = user_input.split(" - ", 1)
        album = parts[0].strip()
        artist = parts[1].strip()
    elif ": " in user_input:
        parts = user_input.split(": ", 1)
        artist = parts[0].strip()
        album = parts[1].strip()
    else:
        raise ValueError(
            "Please use format: 'Song by Artist' or 'Song - Artist'\n"
            "Example: 'Billie Jean by Michael Jackson'"
        )

    return album, artist, style


def play_audio(audio_path: str):
    """Auto-play the generated audio file."""
    console.print(f"\n[bold green]Here's your song![/bold green]")
    console.print(f"[dim]Saved to: {audio_path}[/dim]\n")

    try:
        subprocess.Popen(
            ["open", audio_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        console.print("[dim]♫ Now playing...[/dim]\n")
    except Exception:
        console.print(f"Play manually: open \"{audio_path}\"\n")


def main():
    load_dotenv()

    console.print(Panel(
        "[bold blue]Song Remixer[/bold blue] [dim](Suno Edition)[/dim]\n\n"
        "Tell me a song and I'll create an original song inspired by it!\n\n"
        "[dim]Format: Song by Artist[/dim]\n"
        "[dim]Example: Billie Jean by Michael Jackson[/dim]\n"
        "[dim]Add style: Billie Jean by Michael Jackson (funk, groovy)[/dim]\n\n"
        "[yellow]Single API • Faster • Full song generation[/yellow]\n\n"
        "[dim]Type 'quit' to exit[/dim]",
        title="Welcome"
    ))

    while True:
        try:
            console.print()
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

            if user_input.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]Goodbye![/dim]")
                break

            if not user_input.strip():
                continue

            try:
                album, artist, style = parse_user_input(user_input)
            except ValueError as e:
                console.print(f"\n[yellow]Hmm, I didn't quite get that.[/yellow] {e}")
                continue

            console.print(f"\n[bold magenta]Song Remixer[/bold magenta]: Creating a song inspired by [bold]{album}[/bold] by [bold]{artist}[/bold]...\n")

            # Single API call - Suno does everything
            result = generate_song_suno(
                artist=artist,
                album=album,
                style=style,
            )

            play_audio(result["audio_path"])

        except KeyboardInterrupt:
            console.print("\n\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"\n[red]Something went wrong:[/red] {e}")


if __name__ == "__main__":
    main()
