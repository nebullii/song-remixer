"""AI-powered song remix generator."""

import os
import anthropic


def get_client() -> anthropic.Anthropic:
    """Initialize Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment")
    return anthropic.Anthropic(api_key=api_key)


def generate_remixed_song(song_data: dict, style_hint: str = None) -> dict:
    """
    Generate an original song inspired by the source song's vocabulary and themes.
    """
    client = get_client()

    themes = ", ".join(song_data["themes"][:20])
    vocab_sample = ", ".join(song_data["vocabulary"][:50])
    
    # Handle both single song and album data structures
    source_name = song_data.get("song") or song_data.get("album", "Unknown")
    artist_name = song_data["artist"]

    style_instruction = f"\nStyle hint: {style_hint}" if style_hint else ""

    prompt = f"""You are a professional songwriter writing lyrics for a POP SONG (not a poem). Create an ORIGINAL song inspired by "{source_name}" by {artist_name}.

Key themes: {themes}
Sample vocabulary: {vocab_sample}
{style_instruction}

CRITICAL SONG STRUCTURE REQUIREMENTS:
1. Write a SONG, not a poem. Songs have:
   - A catchy, memorable CHORUS that repeats 2-3 times (this is the hook!)
   - Short, punchy lines (4-8 words per line typically)
   - Repetition of key phrases and the title
   - Rhythm that can be sung to a beat

2. Use this EXACT structure:
   [Verse 1] - 4-6 lines, sets up the story
   [Chorus] - 4-6 lines, catchy hook with the song title, REPEATABLE
   [Verse 2] - 4-6 lines, develops the story
   [Chorus] - repeat the same chorus
   [Bridge] - 2-4 lines, emotional shift
   [Chorus] - repeat the same chorus again

3. The CHORUS must:
   - Be the same lyrics each time it appears
   - Include the song title
   - Be catchy and memorable
   - Use simple, singable words

4. Keep lines SHORT and rhythmic. Think radio pop songs, not Shakespeare.

Format your response EXACTLY as:
TITLE: [Your catchy song title]
MOOD: [One word: energetic/melancholic/dreamy/intense/hopeful/nostalgic]

[Verse 1]
(your lyrics)

[Chorus]
(your catchy, repeatable hook)

[Verse 2]
(your lyrics)

[Chorus]
(same chorus lyrics repeated)

[Bridge]
(your lyrics)

[Chorus]
(same chorus lyrics repeated)
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
