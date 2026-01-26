"""Quick manual test - edit the lyrics below and run this script."""

from src.music_generator import generate_and_download

# Edit your lyrics here (keep the section markers!)
my_lyrics = """[Verse 1]
Your lyrics here
Add your own words

[Chorus]
Your chorus here
This will have harmonies

[Verse 2]
Second verse here
More of your lyrics

[Chorus]
Your chorus here
This will have harmonies"""

# Generate the song
output = generate_and_download(
    lyrics=my_lyrics,
    title="My Test Song",
    style="pop",           # Try: pop, rock, jazz, electronic, indie
    mood="energetic",      # Try: energetic, melancholic, dreamy, intense
    vocal_gender="female", # Try: female, male, neutral
    add_harmonies=True,
    add_intro_outro=True,
)

print(f"\n✅ Song saved to: {output}")
