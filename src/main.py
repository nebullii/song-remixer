"""Song Remixer CLI - Create new songs from album inspiration."""

import subprocess
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from .lyrics_fetcher import fetch_album_lyrics
from .remixer import generate_remixed_song

console = Console()


def parse_user_input(user_input: str) -> tuple[str, str, str]:
    """Parse user input to extract album, artist, and optional style.

    Supports formats:
    - "Album by Artist"
    - "Album - Artist"
    - "Artist: Album"
    """
    user_input = user_input.strip()
    style = "pop, catchy"

    # Check for style hints in parentheses at the end
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
            "Please use format: 'Album by Artist' or 'Album - Artist'\n"
            "Example: 'Thriller by Michael Jackson'"
        )

    return album, artist, style


def process_request(album: str, artist: str, style: str):
    """Process the remix request and return the audio path."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        # Step 1: Fetch lyrics
        task = progress.add_task("Fetching album lyrics from Genius...", total=None)
        album_data = fetch_album_lyrics(artist, album)
        progress.remove_task(task)

        console.print(f"[green]✓[/green] Found {album_data['track_count']} tracks")
        console.print(f"[dim]Themes: {', '.join(album_data['themes'][:10])}[/dim]\n")

        # Step 2: Generate remixed song lyrics
        task = progress.add_task("Creating your remixed song with AI...", total=None)
        song = generate_remixed_song(album_data, style_hint=style)
        progress.remove_task(task)

        console.print(f"[green]✓[/green] Generated: [bold]{song['title']}[/bold]")
        console.print(f"[dim]Mood: {song['mood']}[/dim]\n")

        # Display lyrics
        console.print(Panel(song["lyrics"], title=song["title"], border_style="blue"))

        # Step 3: Generate audio with AI music and singing
        from .music_generator import generate_and_download
        from .voice import guess_vocal_gender
        progress.stop()
        console.print("\n[yellow]Generating music with AI (singing on beat)...[/yellow]")
        
        # Guess vocal gender from artist name
        vocal_gender = guess_vocal_gender(artist)
        
        audio_path = generate_and_download(
            lyrics=song["lyrics"],
            title=song["title"],
            style=style,
            mood=song.get("mood", "energetic"),
            vocal_gender=vocal_gender,
            singing_method="bark"  # Use Bark for actual singing vocals + instrumental
        )

    return audio_path


def play_audio(audio_path: str):
    """Auto-play the generated audio file."""
    console.print(f"\n[bold green]Here's your remixed song![/bold green]")
    console.print(f"[dim]Saved to: {audio_path}[/dim]\n")

    # Auto-play on macOS
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
        "[bold blue]Song Remixer[/bold blue]\n\n"
        "Tell me an album and I'll create an original song inspired by it!\n"
        "[dim]Format: Album by Artist[/dim]\n"
        "[dim]Example: Thriller by Michael Jackson[/dim]\n"
        "[dim]Add style: Thriller by Michael Jackson (80s synth, dark)[/dim]\n\n"
        "[dim]Type 'quit' to exit[/dim]",
        title="Welcome"
    ))

    while True:
        try:
            # Interactive prompt - like chatting
            console.print()
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

            if user_input.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]Goodbye![/dim]")
                break

            if not user_input.strip():
                continue

            # Parse the input
            try:
                album, artist, style = parse_user_input(user_input)
            except ValueError as e:
                console.print(f"\n[yellow]Hmm, I didn't quite get that.[/yellow] {e}")
                continue

            console.print(f"\n[bold magenta]Song Remixer[/bold magenta]: Got it! Creating a song inspired by [bold]{album}[/bold] by [bold]{artist}[/bold]...\n")

            # Process and generate
            audio_path = process_request(album, artist, style)

            # Reply with the audio
            play_audio(audio_path)

        except KeyboardInterrupt:
            console.print("\n\n[dim]Goodbye![/dim]")
            break
        except ValueError as e:
            console.print(f"\n[red]Error:[/red] {e}")
        except Exception as e:
            console.print(f"\n[red]Something went wrong:[/red] {e}")


if __name__ == "__main__":
    main()
