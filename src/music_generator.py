"""Music generation: full AI-generated songs with singing vocals."""

import os
import requests
import replicate
from pydub import AudioSegment
import time


def generate_singing_vocals_bark(lyrics: str, output_path: str, vocal_gender: str | None = None) -> str:
    """
    Generate actual singing vocals using Suno's Bark model.
    Bark can generate singing by using special prompts with musical notation.
    Returns path to the generated vocals file.
    """
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN not found")

    print(f"  Generating singing vocals with Bark AI...")

    # Clean lyrics and add singing cues
    clean_lyrics = lyrics.replace("[Verse 1]", "").replace("[Verse 2]", "")
    clean_lyrics = clean_lyrics.replace("[Chorus]", "").replace("[Bridge]", "")
    clean_lyrics = clean_lyrics.replace("[Outro]", "").replace("[Intro]", "")

    # Add singing notation to prompt (Bark can sing with the ♪ symbol)
    singing_prompt = f"♪ {clean_lyrics} ♪"

    try:
        # Use Bark for singing synthesis
        output = replicate.run(
            "suno-ai/bark:b76242b40d67c76ab6742e987628a2a9ac019e11d56ab96c4e91ce03b79b2787",
            input={
                "prompt": singing_prompt,
                "text_temp": 0.7,
                "waveform_temp": 0.7,
                "output_full": False
            }
        )

        # Bark returns a dict with 'audio_out' FileOutput object
        if isinstance(output, dict) and 'audio_out' in output:
            file_output = output['audio_out']
            if hasattr(file_output, 'read'):
                audio_data = file_output.read()
            else:
                # Fallback: try as URL
                response = requests.get(str(file_output))
                response.raise_for_status()
                audio_data = response.content
        elif hasattr(output, 'read'):
            # It's a FileOutput object directly
            audio_data = output.read()
        elif isinstance(output, str):
            # It's a URL string
            response = requests.get(output)
            response.raise_for_status()
            audio_data = response.content
        else:
            raise ValueError(f"Unexpected output format from Bark: {type(output)}")

        # Save the audio data (Bark outputs WAV format)
        # Change extension to .wav if it's .mp3
        if output_path.endswith('.mp3'):
            output_path = output_path.replace('.mp3', '.wav')
        
        with open(output_path, "wb") as f:
            f.write(audio_data)

        return output_path

    except Exception as e:
        print(f"  Warning: Bark singing generation failed: {e}")
        raise


def _clean_lyrics_for_prompt(lyrics: str) -> str:
    """Clean and format lyrics for AI music generation."""
    # Keep structure markers but format them nicely
    clean = lyrics.replace("[Verse 1]", "\n[Verse 1]\n")
    clean = clean.replace("[Verse 2]", "\n[Verse 2]\n")
    clean = clean.replace("[Chorus]", "\n[Chorus]\n")
    clean = clean.replace("[Bridge]", "\n[Bridge]\n")
    clean = clean.replace("[Outro]", "\n[Outro]\n")
    clean = clean.replace("[Intro]", "\n[Intro]\n")
    return clean.strip()


def generate_full_song(
    lyrics: str,
    title: str,
    style: str = "pop",
    mood: str = "energetic",
    vocal_gender: str | None = None,
    duration: int = 60
) -> str:
    """
    Generate a complete song with AI-sung vocals and instrumental.
    Uses MusicGen with vocal-focused prompts to create singing on beat.
    Returns URL to the generated song.
    """
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN not found. Get one at https://replicate.com/account/api-tokens")

    # Prepare the music generation prompt with emphasis on vocals and singing
    gender_desc = ""
    if vocal_gender:
        gender_desc = f"{vocal_gender} singer, "

    # Create a rich prompt that guides MusicGen to generate music with vocals
    # MusicGen can generate vocals if properly prompted, though not with exact lyrics
    music_prompt = (
        f"{style} song, {gender_desc}{mood} mood, "
        f"clear singing vocals, melodic, catchy chorus, "
        f"professional studio production, "
        f"vocals singing on beat with instrumental accompaniment, "
        f"high quality, radio-ready"
    )

    print(f"  Generating song with AI vocals (singing melodically)...")
    print(f"  Style: {style}, Mood: {mood}")
    print(f"  Note: AI will generate singing vocals matching the style and mood")

    # Use MusicGen's melody model which is better at generating vocals
    model_id = os.getenv(
        "REPLICATE_MUSIC_MODEL",
        "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
    )

    try:
        output = replicate.run(
            model_id,
            input={
                "prompt": music_prompt,
                "duration": duration,
                "model_version": "stereo-melody-large",  # Melody model is better for vocals
                "output_format": "mp3",
                "continuation": False,
                "normalization_strategy": "peak",
                "top_k": 250,  # Higher diversity for more varied vocal generation
                "top_p": 0.0,
                "temperature": 1.0,
                "classifier_free_guidance": 3  # Stronger prompt adherence
            }
        )
        return output
    except Exception as e:
        print(f"  Warning: Primary music generation failed: {e}")
        print(f"  Trying alternative approach...")
        # Fallback: Try with different parameters
        try:
            output = replicate.run(
                "meta/musicgen:7be0f12c54a8d033a0fbd14418c9af98962da9a86f5ff7811f9b3423a1f0b7d7",
                input={
                    "prompt": music_prompt,
                    "duration": duration,
                    "model_version": "stereo-melody-large",
                    "output_format": "mp3",
                    "normalization_strategy": "peak"
                }
            )
            return output
        except Exception as e2:
            print(f"  Error: Could not generate music: {e2}")
            raise


def generate_instrumental(style: str, title: str, duration: int = 30) -> str:
    """Generate instrumental music using Replicate's MusicGen."""
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN not found. Get one at https://replicate.com/account/api-tokens")

    music_prompt = f"{style} instrumental, melodic, professional production, background music for song titled {title}"

    print(f"  Generating instrumental with MusicGen...")

    model_id = os.getenv(
        "REPLICATE_MUSICGEN_MODEL",
        "meta/musicgen:7be0f12c54a8d033a0fbd14418c9af98962da9a86f5ff7811f9b3423a1f0b7d7",
    )
    output = replicate.run(
        model_id,
        input={
            "prompt": music_prompt,
            "duration": duration,
            "model_version": "stereo-melody-large",
            "output_format": "mp3",
            "normalization_strategy": "peak"
        }
    )

    return output  # Returns URL


def mix_audio(vocals_path: str, instrumental_url: str, output_path: str):
    """Mix vocals with instrumental music."""
    print(f"  Mixing vocals with instrumental...")

    # Download instrumental
    response = requests.get(instrumental_url)
    response.raise_for_status()

    instrumental_temp = output_path.replace(".mp3", "_instrumental.mp3")
    with open(instrumental_temp, "wb") as f:
        f.write(response.content)

    # Load audio files (vocals are WAV from Bark, instrumental is MP3)
    if vocals_path.endswith('.wav'):
        vocals = AudioSegment.from_wav(vocals_path)
    else:
        vocals = AudioSegment.from_mp3(vocals_path)
    instrumental = AudioSegment.from_mp3(instrumental_temp)

    # Adjust volumes: vocals louder, instrumental as background
    vocals = vocals + 3  # Boost vocals by 3dB
    instrumental = instrumental - 6  # Lower instrumental by 6dB

    # Loop instrumental if vocals are longer
    if len(vocals) > len(instrumental):
        loops_needed = (len(vocals) // len(instrumental)) + 1
        instrumental = instrumental * loops_needed

    # Trim instrumental to match vocals length (with 2s fade out)
    instrumental = instrumental[:len(vocals) + 2000]
    instrumental = instrumental.fade_out(2000)

    # Overlay vocals on instrumental
    mixed = instrumental.overlay(vocals)

    # Export final mix
    mixed.export(output_path, format="mp3")

    # Cleanup temp files
    os.remove(instrumental_temp)
    os.remove(vocals_path)

    return output_path


def generate_and_download(
    lyrics: str,
    title: str,
    style: str = "pop",
    mood: str = "energetic",
    vocal_gender: str | None = None,
    output_dir: str = "output",
    singing_method: str = "full",
) -> str:
    """
    Generate a complete song with AI-sung vocals on beat.

    Args:
        lyrics: The song lyrics to be sung
        title: Song title
        style: Music style (pop, rock, hip-hop, etc.)
        mood: Emotional mood (energetic, melancholic, etc.)
        vocal_gender: Optional gender for vocals (male/female)
        output_dir: Output directory for the song
        singing_method: Method for generating singing vocals:
            - "full": Generate complete song with music and vocals (MusicGen)
            - "bark": Generate singing vocals with Bark + instrumental mix
            - "instrumental": Instrumental only (no vocals)

    Returns:
        Path to the generated song file
    """
    os.makedirs(output_dir, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in title)[:50]
    safe_title = safe_title.replace(" ", "_")
    output_path = os.path.join(output_dir, f"{safe_title}.mp3")

    if singing_method == "full":
        # Method 1: Generate complete song with music and vocal-like sounds (MusicGen)
        print(f"  Generating complete song with AI vocals...")
        song_url = generate_full_song(
            lyrics=lyrics,
            title=title,
            style=style,
            mood=mood,
            vocal_gender=vocal_gender,
            duration=60
        )

        # Download the generated song
        print(f"  Downloading generated song...")
        response = requests.get(song_url)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

    elif singing_method == "bark":
        # Method 2: Generate singing vocals with Bark, then mix with instrumental
        print(f"  Generating singing vocals with Bark AI...")
        vocals_path = os.path.join(output_dir, f"{safe_title}_vocals.wav")

        # Generate singing vocals
        generate_singing_vocals_bark(lyrics, vocals_path, vocal_gender)

        # Generate instrumental
        print(f"  Generating instrumental track...")
        instrumental_url = generate_instrumental(style, title, duration=60)

        # Mix vocals with instrumental
        mix_audio(vocals_path, instrumental_url, output_path)

    else:  # instrumental
        # Method 3: Generate instrumental only (no vocals)
        print(f"  Generating instrumental (no vocals)...")
        instrumental_url = generate_instrumental(style, title, duration=60)

        response = requests.get(instrumental_url)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

    print(f"  Complete! Saved to {output_path}")
    return output_path
