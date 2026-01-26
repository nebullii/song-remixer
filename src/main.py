"""Song Remixer CLI - Create new songs from album inspiration."""

import subprocess
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from .lyrics_fetcher import fetch_album_lyrics, fetch_song_lyrics
from .remixer import generate_remixed_song

console = Console()


def parse_user_input(user_input: str) -> tuple[str, str, str, bool]:
    """Parse user input to extract song/album, artist, style, and mode.

    Supports formats:
    - "Song by Artist" (default - single song, fast)
    - "album: Album by Artist" (full album mode)
    - "Song - Artist"
    - "Artist: Song"

    Returns: (name, artist, style, is_album_mode)
    """
    user_input = user_input.strip()
    style = "pop, catchy"
    is_album = False

    # Check for album mode prefix
    if user_input.lower().startswith("album:"):
        is_album = True
        user_input = user_input[6:].strip()

    # Check for style hints in parentheses at the end
    if "(" in user_input and user_input.endswith(")"):
        style_start = user_input.rfind("(")
        style = user_input[style_start + 1:-1].strip()
        user_input = user_input[:style_start].strip()

    # Try different separators
    if " by " in user_input.lower():
        idx = user_input.lower().index(" by ")
        name = user_input[:idx].strip()
        artist = user_input[idx + 4:].strip()
    elif " - " in user_input:
        parts = user_input.split(" - ", 1)
        name = parts[0].strip()
        artist = parts[1].strip()
    elif ": " in user_input:
        parts = user_input.split(": ", 1)
        artist = parts[0].strip()
        name = parts[1].strip()
    else:
        raise ValueError(
            "Please use format: 'Song by Artist'\n"
            "Example: 'Billie Jean by Michael Jackson'\n"
            "For album mode: 'album: Thriller by Michael Jackson'"
        )

    return name, artist, style, is_album


def process_request(name: str, artist: str, style: str, use_tts: bool = True, is_album: bool = False):
    """Process the remix request and return the audio path."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        # Step 1: Fetch lyrics
        if is_album:
            task = progress.add_task("Fetching album lyrics from Genius...", total=None)
            album_data = fetch_album_lyrics(artist, name)
            progress.remove_task(task)
            console.print(f"[green]✓[/green] Found {album_data['track_count']} tracks")
        else:
            task = progress.add_task("Fetching song lyrics from Genius...", total=None)
            album_data = fetch_song_lyrics(artist, name)
            progress.remove_task(task)
            console.print(f"[green]✓[/green] Found song: {album_data['tracks'][0]['title']}")

        console.print(f"[dim]Themes: {', '.join(album_data['themes'][:10])}[/dim]\n")

        # Step 2: Generate remixed song lyrics
        task = progress.add_task("Creating your remixed song with AI...", total=None)
        song = generate_remixed_song(album_data, style_hint=style)
        progress.remove_task(task)

        console.print(f"[green]✓[/green] Generated: [bold]{song['title']}[/bold]")
        console.print(f"[dim]Mood: {song['mood']}[/dim]\n")

        # Display lyrics
        console.print(Panel(song["lyrics"], title=song["title"], border_style="blue"))

        # Step 3: Generate audio
        if use_tts:
            from .tts import generate_song_audio
            task = progress.add_task("Generating audio...", total=None)
            audio_path = generate_song_audio(song)
            progress.remove_task(task)
        else:
            from .music_generator import generate_and_download
            progress.stop()
            console.print("\n[yellow]Generating music with Suno AI...[/yellow]")
            audio_path = generate_and_download(
                lyrics=song["lyrics"],
                title=song["title"],
                style=style
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
        "Tell me a song and I'll create an original song inspired by it!\n"
        "[dim]Format: Song by Artist[/dim]\n"
        "[dim]Example: Billie Jean by Michael Jackson[/dim]\n"
        "[dim]Add style: Billie Jean by Michael Jackson (80s synth, dark)[/dim]\n"
        "[dim]For album mode: album: Thriller by Michael Jackson[/dim]\n\n"
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
                name, artist, style, is_album = parse_user_input(user_input)
            except ValueError as e:
                console.print(f"\n[yellow]Hmm, I didn't quite get that.[/yellow] {e}")
                continue

            mode_text = "album" if is_album else "song"
            console.print(f"\n[bold magenta]Song Remixer[/bold magenta]: Got it! Creating a song inspired by the {mode_text} [bold]{name}[/bold] by [bold]{artist}[/bold]...\n")

            # Process and generate
            audio_path = process_request(name, artist, style, use_tts=True, is_album=is_album)

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
