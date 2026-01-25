"""Music generation: instrumental + vocals combined."""

import os
import asyncio
import math
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import replicate
import edge_tts
from pydub import AudioSegment
from . import audio_effects


# Bark voice presets for different moods/genders
# Valid presets: en_speaker_0 through en_speaker_9, announcer
BARK_VOICE_PRESETS = {
    "female": {
        "energetic": "en_speaker_9",
        "melancholic": "en_speaker_2",
        "dreamy": "en_speaker_2",
        "intense": "en_speaker_9",
        "hopeful": "en_speaker_1",
        "nostalgic": "en_speaker_2",
        "default": "en_speaker_1",
    },
    "male": {
        "energetic": "en_speaker_6",
        "melancholic": "en_speaker_3",
        "dreamy": "en_speaker_3",
        "intense": "en_speaker_6",
        "hopeful": "en_speaker_0",
        "nostalgic": "en_speaker_3",
        "default": "en_speaker_0",
    },
    "neutral": {
        "energetic": "en_speaker_6",
        "melancholic": "en_speaker_2",
        "dreamy": "en_speaker_2",
        "intense": "en_speaker_6",
        "hopeful": "en_speaker_1",
        "nostalgic": "en_speaker_3",
        "default": "en_speaker_1",
    },
}

# Section-specific instrumental intensity configurations
SECTION_CONFIGS = {
    "intro": {
        "intensity": "minimal",
        "prompt_suffix": "minimal, atmospheric, building, intro",
        "duration_multiplier": 0.8,
        "vocal_volume": 0,  # No vocals in intro
        "instrumental_volume": -5,
    },
    "verse": {
        "intensity": "light",
        "prompt_suffix": "light instrumentation, supporting melody, verse",
        "duration_multiplier": 1.0,
        "vocal_volume": 5,
        "instrumental_volume": -18,
    },
    "pre-chorus": {
        "intensity": "medium",
        "prompt_suffix": "building energy, transitioning, pre-chorus",
        "duration_multiplier": 1.0,
        "vocal_volume": 3,
        "instrumental_volume": -15,
    },
    "chorus": {
        "intensity": "full",
        "prompt_suffix": "full arrangement, energetic, layered, powerful chorus",
        "duration_multiplier": 1.0,
        "vocal_volume": 3,
        "instrumental_volume": -12,
    },
    "bridge": {
        "intensity": "varied",
        "prompt_suffix": "contrasting, different mood, bridge section",
        "duration_multiplier": 1.0,
        "vocal_volume": 2,
        "instrumental_volume": -14,
    },
    "outro": {
        "intensity": "fading",
        "prompt_suffix": "fading, resolution, ending, outro",
        "duration_multiplier": 0.9,
        "vocal_volume": 0,  # No vocals in outro
        "instrumental_volume": -8,
    },
}

# Legacy Edge TTS voice map (fallback)
VOICE_MAP = {
    "female": {
        "energetic": "en-US-AriaNeural",
        "melancholic": "en-US-JennyNeural",
        "dreamy": "en-GB-SoniaNeural",
        "intense": "en-US-AriaNeural",
        "hopeful": "en-US-AriaNeural",
        "nostalgic": "en-GB-SoniaNeural",
        "default": "en-US-AriaNeural",
    },
    "male": {
        "energetic": "en-US-GuyNeural",
        "melancholic": "en-GB-RyanNeural",
        "dreamy": "en-GB-RyanNeural",
        "intense": "en-US-GuyNeural",
        "hopeful": "en-US-GuyNeural",
        "nostalgic": "en-GB-RyanNeural",
        "default": "en-US-GuyNeural",
    },
    "neutral": {
        "energetic": "en-US-AriaNeural",
        "melancholic": "en-US-JennyNeural",
        "dreamy": "en-GB-SoniaNeural",
        "intense": "en-US-GuyNeural",
        "hopeful": "en-US-AriaNeural",
        "nostalgic": "en-GB-RyanNeural",
        "default": "en-US-AriaNeural",
    },
}


def _select_voice(mood: str, vocal_gender: str | None) -> str:
    """Select Edge TTS voice (legacy fallback)."""
    gender = (vocal_gender or "neutral").lower()
    mood_key = (mood or "default").lower()
    gender_map = VOICE_MAP.get(gender, VOICE_MAP["neutral"])
    return gender_map.get(mood_key, gender_map["default"])


def _select_bark_voice(mood: str, vocal_gender: str | None) -> str:
    """Select Bark voice preset for singing."""
    gender = (vocal_gender or "neutral").lower()
    mood_key = (mood or "default").lower()
    gender_map = BARK_VOICE_PRESETS.get(gender, BARK_VOICE_PRESETS["neutral"])
    return gender_map.get(mood_key, gender_map["default"])


def _format_lyrics_for_singing(lyrics: str) -> str:
    """Format lyrics with musical notation for Bark singing synthesis."""
    # Remove section markers
    clean = lyrics.replace("[Verse 1]", "").replace("[Verse 2]", "")
    clean = clean.replace("[Verse 3]", "").replace("[Verse 4]", "")
    clean = clean.replace("[Chorus]", "").replace("[Bridge]", "")
    clean = clean.replace("[Outro]", "").replace("[Intro]", "")
    clean = clean.replace("[Pre-Chorus]", "").replace("[Hook]", "")

    # Split into lines and wrap each with musical markers
    lines = [line.strip() for line in clean.split('\n') if line.strip()]

    # Add singing markers - ♪ tells Bark to sing
    sung_lines = [f"♪ {line} ♪" for line in lines]

    return " ".join(sung_lines)


def generate_vocals_bark(lyrics: str, mood: str, output_path: str, vocal_gender: str | None = None):
    """Generate singing vocals using Bark on Replicate."""
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN not found")

    voice_preset = _select_bark_voice(mood, vocal_gender)
    singing_text = _format_lyrics_for_singing(lyrics)

    # Bark works best with shorter text - truncate if too long
    # (each section should already be reasonably short)
    max_chars = 250
    if len(singing_text) > max_chars:
        singing_text = singing_text[:max_chars]

    print(f"  Generating singing vocals with Bark...")

    # Bark model on Replicate
    output = replicate.run(
        "suno-ai/bark:b76242b40d67c76ab6742e987628a2a9ac019e11d56ab96c4e91ce03b79b2787",
        input={
            "prompt": singing_text,
            "history_prompt": voice_preset,
            "text_temp": 0.7,
            "waveform_temp": 0.7,
        }
    )

    # Handle different output formats from Replicate
    if isinstance(output, dict):
        audio_url = output.get("audio_out") or output.get("audio")
    elif isinstance(output, str):
        audio_url = output
    else:
        raise ValueError(f"Unexpected Bark output format: {type(output)}")

    if not audio_url:
        raise ValueError("No audio URL in Bark output")

    # Download the audio (Bark returns WAV format)
    response = requests.get(audio_url)
    response.raise_for_status()

    # Save as WAV first, then convert to MP3
    wav_path = output_path.replace(".mp3", "_temp.wav")
    with open(wav_path, "wb") as f:
        f.write(response.content)

    # Convert WAV to MP3 using pydub
    audio = AudioSegment.from_wav(wav_path)
    audio.export(output_path, format="mp3")

    # Clean up temp WAV file
    os.remove(wav_path)


async def generate_vocals_async(lyrics: str, mood: str, output_path: str, vocal_gender: str | None = None):
    """Generate vocals using Edge TTS (legacy fallback)."""
    voice = _select_voice(mood, vocal_gender)

    # Clean lyrics for TTS
    clean_lyrics = lyrics.replace("[Verse 1]", "").replace("[Verse 2]", "")
    clean_lyrics = clean_lyrics.replace("[Chorus]", "").replace("[Bridge]", "")
    clean_lyrics = clean_lyrics.replace("[Outro]", "").replace("[Intro]", "")

    communicate = edge_tts.Communicate(clean_lyrics, voice, rate="-5%")
    await communicate.save(output_path)


def generate_vocals(lyrics: str, mood: str, output_path: str, vocal_gender: str | None = None):
    """Generate vocals - uses Bark for singing, falls back to Edge TTS."""
    # Try Bark first for singing-style vocals
    if os.getenv("REPLICATE_API_TOKEN"):
        try:
            generate_vocals_bark(lyrics, mood, output_path, vocal_gender)
            return
        except Exception as e:
            print(f"  Bark failed ({e}), falling back to Edge TTS...")

    # Fallback to Edge TTS (speech, not singing)
    asyncio.run(generate_vocals_async(lyrics, mood, output_path, vocal_gender=vocal_gender))


def _split_lyrics_sections(lyrics: str) -> list[dict]:
    """Split lyrics into labeled sections like [Verse 1], [Chorus], etc."""
    sections: list[dict] = []
    current_label = "Section"
    current_lines: list[str] = []

    for raw in lyrics.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]") and len(line) > 2:
            if current_lines:
                sections.append({"label": current_label, "text": "\n".join(current_lines).strip()})
                current_lines = []
            current_label = line[1:-1].strip()
            continue
        if line:
            current_lines.append(line)

    if current_lines:
        sections.append({"label": current_label, "text": "\n".join(current_lines).strip()})

    if not sections:
        return [{"label": "Section", "text": lyrics.strip()}]

    return sections


def _atempo_filters(ratio: float) -> str:
    """Build a safe ffmpeg atempo filter chain for any ratio."""
    filters = []
    remaining = ratio
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.6f}")
    return ",".join(filters)


def _time_stretch_to_duration(input_path: str, output_path: str, target_ms: int) -> bool:
    """Time-stretch audio to a target duration using ffmpeg atempo."""
    try:
        original = AudioSegment.from_mp3(input_path)
    except Exception:
        return False

    original_ms = max(len(original), 1)
    if abs(original_ms - target_ms) < 50:
        original.export(output_path, format="mp3")
        return True

    ratio = original_ms / max(target_ms, 1)
    filter_chain = _atempo_filters(ratio)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter:a", filter_chain,
        output_path,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def generate_instrumental(style: str, title: str, duration: int = 30, section_label: str | None = None, mood: str | None = None) -> str:
    """Generate instrumental music using Replicate's MusicGen."""
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN not found. Get one at https://replicate.com/account/api-tokens")

    # Get section-specific configuration
    section_key = section_label.lower() if section_label else "verse"
    section_config = SECTION_CONFIGS.get(section_key, SECTION_CONFIGS["verse"])
    
    # Build enhanced prompt with section-specific details
    section_hint = section_config["prompt_suffix"]
    mood_hint = f", {mood} mood" if mood else ""
    music_prompt = (
        f"{style} instrumental, melodic, professional production, "
        f"{section_hint}, background music for song titled {title}{mood_hint}"
    )
    
    # Adjust duration based on section type
    adjusted_duration = int(duration * section_config.get("duration_multiplier", 1.0))

    print(f"  Generating {section_key} instrumental with MusicGen...")

    model_id = os.getenv(
        "REPLICATE_MUSICGEN_MODEL",
        "meta/musicgen:7be0f12c54a8d033a0fbd14418c9af98962da9a86f5ff7811f9b3423a1f0b7d7",
    )
    output = replicate.run(
        model_id,
        input={
            "prompt": music_prompt,
            "duration": adjusted_duration,
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

    # Load audio files
    vocals = AudioSegment.from_mp3(vocals_path)
    instrumental = AudioSegment.from_mp3(instrumental_temp)

    # Adjust volumes: vocals much louder, instrumental as quiet background
    vocals = vocals + 8  # Boost vocals significantly
    instrumental = instrumental - 15  # Push instrumental way back

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


def _download_instrumental(instrumental_url: str, output_path: str) -> str:
    response = requests.get(instrumental_url)
    response.raise_for_status()

    instrumental_temp = output_path.replace(".mp3", "_instrumental.mp3")
    with open(instrumental_temp, "wb") as f:
        f.write(response.content)
    return instrumental_temp


def _match_instrumental_to_vocals(instrumental_path: str, vocals_path: str) -> str:
    """Match instrumental duration to vocals using stretch, loop, and trim."""
    vocals = AudioSegment.from_mp3(vocals_path)
    instrumental = AudioSegment.from_mp3(instrumental_path)

    target_ms = len(vocals)
    if len(instrumental) < target_ms:
        loops_needed = (target_ms // len(instrumental)) + 1
        instrumental = instrumental * loops_needed

    instrumental = instrumental[:target_ms]
    temp_path = instrumental_path.replace(".mp3", "_fit.mp3")
    instrumental.export(temp_path, format="mp3")

    stretched_path = instrumental_path.replace(".mp3", "_stretch.mp3")
    if _time_stretch_to_duration(temp_path, stretched_path, target_ms):
        os.remove(temp_path)
        return stretched_path

    return temp_path


def _mix_vocals_instrumental_paths(vocals_path: str, instrumental_path: str, output_path: str, section_type: str = "verse"):
    """Mix vocals and instrumental with section-aware balance."""
    vocals = AudioSegment.from_mp3(vocals_path)
    instrumental = AudioSegment.from_mp3(instrumental_path)

    # Get section-specific volume adjustments
    section_key = section_type.lower()
    section_config = SECTION_CONFIGS.get(section_key, SECTION_CONFIGS["verse"])
    
    vocal_adjustment = section_config.get("vocal_volume", 5)
    instrumental_adjustment = section_config.get("instrumental_volume", -15)
    
    # Apply section-aware mixing
    vocals = vocals + vocal_adjustment
    instrumental = instrumental + instrumental_adjustment
    
    mixed = instrumental.overlay(vocals)
    
    # Apply light compression for cohesive sound
    mixed = audio_effects.compress_audio(mixed, threshold=-20.0, ratio=3.0)
    
    mixed.export(output_path, format="mp3")


def generate_and_download(
    lyrics: str,
    title: str,
    style: str = "pop",
    mood: str = "energetic",
    vocal_gender: str | None = None,
    output_dir: str = "output",
    align_sections: bool = True,
    add_harmonies: bool = True,
    add_intro_outro: bool = True,
) -> str:
    """
    Generate a complete song with vocals over instrumental music.
    
    Args:
        lyrics: Song lyrics with section markers
        title: Song title
        style: Music style (pop, rock, etc.)
        mood: Song mood (energetic, melancholic, etc.)
        vocal_gender: Voice gender (male, female, neutral)
        output_dir: Output directory
        align_sections: Generate sections separately for better alignment
        add_harmonies: Add vocal harmonies to chorus/bridge
        add_intro_outro: Add instrumental intro and outro
    """
    os.makedirs(output_dir, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in title)[:50]
    safe_title = safe_title.replace(" ", "_")

    output_path = os.path.join(output_dir, f"{safe_title}.mp3")

    if align_sections:
        print("  Generating enhanced song with vocal harmonies and instrumental variations...")
        sections = _split_lyrics_sections(lyrics)
        section_outputs: list[AudioSegment] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            # Add intro if requested
            if add_intro_outro:
                print("  Generating intro...")
                intro_url = generate_instrumental(style, title, duration=10, section_label="Intro", mood=mood)
                intro_path = _download_instrumental(intro_url, os.path.join(tmpdir, "intro.mp3"))
                intro_audio = AudioSegment.from_mp3(intro_path)
                intro_audio = audio_effects.apply_section_effects(intro_audio, "intro")
                intro_audio = intro_audio.fade_in(1000)
                section_outputs.append(intro_audio)
            
            for idx, section in enumerate(sections, start=1):
                section_label = section["label"]
                section_text = section["text"]
                if not section_text:
                    continue

                vocals_path = os.path.join(tmpdir, f"vocals_{idx}.mp3")
                instrumental_temp_path = os.path.join(tmpdir, f"section_{idx}.mp3")

                # Estimate duration from text length
                estimated_seconds = max(8, min(30, len(section_text) // 15 + 5))

                # Run vocals and instrumental generation in parallel
                print(f"  Section {idx} ({section_label}): generating vocals + instrumental...")

                with ThreadPoolExecutor(max_workers=2) as executor:
                    vocals_future = executor.submit(
                        generate_vocals, section_text, mood, vocals_path, vocal_gender
                    )
                    instrumental_future = executor.submit(
                        generate_instrumental,
                        style, title, estimated_seconds, section_label, mood
                    )

                    # Wait for both to complete
                    vocals_future.result()
                    instrumental_url = instrumental_future.result()

                # Process vocals with harmonies and effects
                vocals_audio = AudioSegment.from_mp3(vocals_path)
                
                # Add harmonies for chorus and bridge
                if add_harmonies and section_label.lower() in ["chorus", "bridge"]:
                    print(f"    Adding vocal harmonies to {section_label}...")
                    num_harmonies = 2 if section_label.lower() == "chorus" else 1
                    vocals_audio = audio_effects.create_vocal_layers(vocals_audio, section_label, num_harmonies)
                else:
                    # Apply effects without harmonies
                    vocals_audio = audio_effects.apply_section_effects(vocals_audio, section_label)
                
                # Apply dynamic volume
                vocals_audio = audio_effects.apply_dynamic_volume(vocals_audio, section_label)
                
                # Save processed vocals
                processed_vocals_path = os.path.join(tmpdir, f"vocals_processed_{idx}.mp3")
                vocals_audio.export(processed_vocals_path, format="mp3")

                # Download and process instrumental
                instrumental_path = _download_instrumental(instrumental_url, instrumental_temp_path)
                fitted_path = _match_instrumental_to_vocals(instrumental_path, processed_vocals_path)

                # Mix with section-aware balance
                mixed_path = os.path.join(tmpdir, f"mixed_{idx}.mp3")
                _mix_vocals_instrumental_paths(processed_vocals_path, fitted_path, mixed_path, section_label)
                
                section_audio = AudioSegment.from_mp3(mixed_path)
                section_outputs.append(section_audio)
            
            # Add outro if requested
            if add_intro_outro:
                print("  Generating outro...")
                outro_url = generate_instrumental(style, title, duration=12, section_label="Outro", mood=mood)
                outro_path = _download_instrumental(outro_url, os.path.join(tmpdir, "outro.mp3"))
                outro_audio = AudioSegment.from_mp3(outro_path)
                outro_audio = audio_effects.apply_section_effects(outro_audio, "outro")
                outro_audio = outro_audio.fade_out(3000)
                section_outputs.append(outro_audio)

        if not section_outputs:
            raise ValueError("No sections produced audio output")

        # Combine sections with crossfades
        print("  Combining sections with smooth transitions...")
        final_mix = section_outputs[0]
        for next_section in section_outputs[1:]:
            final_mix = audio_effects.crossfade_segments(final_mix, next_section, duration_ms=500)
        
        # Apply final master compression
        final_mix = audio_effects.compress_audio(final_mix, threshold=-18.0, ratio=2.5)
        
        final_mix.export(output_path, format="mp3")
        print(f"  Complete! Saved to {output_path}")
        return output_path

    # Fallback: single-track generation
    vocals_path = os.path.join(output_dir, f"{safe_title}_vocals.mp3")
    print(f"  Generating vocals...")
    generate_vocals(lyrics, mood, vocals_path, vocal_gender=vocal_gender)

    instrumental_url = generate_instrumental(style, title)
    mix_audio(vocals_path, instrumental_url, output_path)

    print(f"  Complete! Saved to {output_path}")
    return output_path
