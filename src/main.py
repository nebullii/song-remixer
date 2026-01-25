"""Song Remixer CLI - Create new songs from album inspiration."""

import argparse
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .lyrics_fetcher import fetch_album_lyrics
from .remixer import generate_remixed_song

console = Console()


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Create a new song inspired by an album"
    )
    parser.add_argument("album", help="Album name")
    parser.add_argument("artist", help="Artist name")
    parser.add_argument("--style", help="Music style (e.g., 'pop, energetic, 80s')", default="pop, catchy")
    parser.add_argument("--tts", action="store_true", help="Use TTS instead of Suno (spoken, not sung)")
    parser.add_argument("--debug", action="store_true", help="Show debug info")

    args = parser.parse_args()

    console.print(Panel(
        f"[bold blue]Song Remixer[/bold blue]\n"
        f"Album: {args.album}\n"
        f"Artist: {args.artist}",
        title="Starting"
    ))

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Step 1: Fetch lyrics
            task = progress.add_task("Fetching album lyrics from Genius...", total=None)
            album_data = fetch_album_lyrics(args.artist, args.album)
            progress.remove_task(task)

            console.print(f"[green]✓[/green] Found {album_data['track_count']} tracks")
            console.print(f"[dim]Themes: {', '.join(album_data['themes'][:10])}[/dim]\n")

            # Step 2: Generate remixed song lyrics
            task = progress.add_task("Creating your remixed song with AI...", total=None)
            song = generate_remixed_song(album_data, style_hint=args.style)
            progress.remove_task(task)

            console.print(f"[green]✓[/green] Generated: [bold]{song['title']}[/bold]")
            console.print(f"[dim]Mood: {song['mood']}[/dim]\n")

            # Display lyrics
            console.print(Panel(song["lyrics"], title=song["title"], border_style="blue"))

            # Step 3: Generate audio
            if args.tts:
                # Use Edge-TTS (spoken word)
                from .tts import generate_song_audio
                task = progress.add_task("Generating TTS audio...", total=None)
                audio_path = generate_song_audio(song)
                progress.remove_task(task)
            else:
                # Use Suno AI (actual music)
                from .music_generator import generate_and_download
                progress.stop()
                console.print("\n[yellow]Generating music with Suno AI...[/yellow]")
                audio_path = generate_and_download(
                    lyrics=song["lyrics"],
                    title=song["title"],
                    style=args.style
                )

            console.print(f"\n[green]✓[/green] Audio saved: [bold]{audio_path}[/bold]")

        console.print("\n[bold green]Done![/bold green] Play your new song:")
        console.print(f"  open \"{audio_path}\"")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if args.debug:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
