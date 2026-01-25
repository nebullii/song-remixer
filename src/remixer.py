"""AI-powered song remix generator."""

import os
import anthropic


def get_client() -> anthropic.Anthropic:
    """Initialize Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment")
    return anthropic.Anthropic(api_key=api_key)


def generate_remixed_song(album_data: dict, style_hint: str = None) -> dict:
    """
    Generate an original song inspired by the album's vocabulary and themes.
    """
    client = get_client()

    themes = ", ".join(album_data["themes"][:20])
    vocab_sample = ", ".join(album_data["vocabulary"][:50])
    track_titles = [t["title"] for t in album_data["tracks"]]

    style_instruction = f"\nStyle hint: {style_hint}" if style_hint else ""

    prompt = f"""You are a creative songwriter. Create an ORIGINAL song inspired by the vocabulary and themes from "{album_data['album']}" by {album_data['artist']}.

Key themes: {themes}
Sample vocabulary: {vocab_sample}
Original track titles: {', '.join(track_titles)}
{style_instruction}

IMPORTANT:
- Create completely ORIGINAL lyrics - do not copy existing lyrics
- Use themes and vocabulary as INSPIRATION only
- Include clear verse/chorus structure
- Make it emotional and singable

Format your response EXACTLY as:
TITLE: [Your song title]
MOOD: [One word: energetic/melancholic/dreamy/intense/hopeful/nostalgic]

[Your original lyrics with verse/chorus labels]
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    return parse_song_response(response.content[0].text)


def parse_song_response(response: str) -> dict:
    """Parse the AI response into structured song data."""
    lines = response.strip().split('\n')

    title = "Untitled Remix"
    mood = "dreamy"
    lyrics_start = 0

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("MOOD:"):
            mood = line.replace("MOOD:", "").strip().lower()
        elif line.strip() and not line.startswith(("TITLE:", "MOOD:")):
            lyrics_start = i
            break

    lyrics = '\n'.join(lines[lyrics_start:]).strip()

    return {"title": title, "mood": mood, "lyrics": lyrics}
