"""Audio effects and processing for vocals and instrumentals."""

import numpy as np
from pydub import AudioSegment
from pydub.effects import compress_dynamic_range
from scipy import signal
from scipy.signal import butter, lfilter
import io


def _audio_to_numpy(audio: AudioSegment) -> tuple[np.ndarray, int]:
    """Convert AudioSegment to numpy array."""
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    
    # Normalize to [-1, 1]
    if audio.sample_width == 2:  # 16-bit
        samples = samples / 32768.0
    elif audio.sample_width == 4:  # 32-bit
        samples = samples / 2147483648.0
    
    # Handle stereo
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))
    
    return samples, audio.frame_rate


def _numpy_to_audio(samples: np.ndarray, frame_rate: int, channels: int = 1) -> AudioSegment:
    """Convert numpy array back to AudioSegment."""
    # Denormalize from [-1, 1] to int16
    samples = np.clip(samples, -1.0, 1.0)
    samples_int16 = (samples * 32767).astype(np.int16)
    
    # Convert to bytes
    audio_bytes = samples_int16.tobytes()
    
    # Create AudioSegment
    return AudioSegment(
        data=audio_bytes,
        sample_width=2,
        frame_rate=frame_rate,
        channels=channels
    )


def add_reverb(audio: AudioSegment, room_size: float = 0.5, wet_mix: float = 0.3) -> AudioSegment:
    """
    Add reverb effect to audio.
    
    Args:
        audio: Input audio
        room_size: Size of reverb (0.0-1.0), larger = more reverb
        wet_mix: Mix of wet signal (0.0-1.0), 0 = dry, 1 = fully wet
    """
    samples, frame_rate = _audio_to_numpy(audio)
    channels = audio.channels
    
    # Simple reverb using comb filters
    delay_samples = int(room_size * 0.05 * frame_rate)  # 0-50ms delay
    decay = 0.3 + (room_size * 0.4)  # Decay factor
    
    if channels == 2:
        # Process each channel
        reverb_samples = np.zeros_like(samples)
        for ch in range(2):
            channel_data = samples[:, ch]
            reverb_channel = np.copy(channel_data)

            # Apply multiple delays for richer reverb
            for i, delay_mult in enumerate([1.0, 1.3, 1.7, 2.1]):
                delay = int(delay_samples * delay_mult)
                if 0 < delay < len(channel_data):
                    delayed = np.zeros_like(channel_data)
                    delayed[delay:] = channel_data[:-delay] * (decay ** (i + 1))
                    reverb_channel += delayed

            reverb_samples[:, ch] = reverb_channel
    else:
        reverb_samples = np.copy(samples)
        num_samples = len(samples)
        for i, delay_mult in enumerate([1.0, 1.3, 1.7, 2.1]):
            delay = int(delay_samples * delay_mult)
            if 0 < delay < num_samples:
                delayed = np.zeros_like(samples)
                delayed[delay:] = samples[:-delay] * (decay ** (i + 1))
                reverb_samples += delayed
    
    # Mix dry and wet signals
    mixed = samples * (1 - wet_mix) + reverb_samples * wet_mix
    
    return _numpy_to_audio(mixed, frame_rate, channels)


def add_chorus(audio: AudioSegment, depth: float = 0.3, rate: float = 1.5) -> AudioSegment:
    """
    Add chorus effect to thicken the sound.
    
    Args:
        audio: Input audio
        depth: Depth of chorus effect (0.0-1.0)
        rate: Rate of modulation in Hz
    """
    samples, frame_rate = _audio_to_numpy(audio)
    channels = audio.channels
    
    # Create modulated delay
    duration = len(samples) / frame_rate
    t = np.linspace(0, duration, len(samples))
    
    # LFO (Low Frequency Oscillator) for chorus
    max_delay_ms = 20 * depth  # 0-20ms delay
    lfo = np.sin(2 * np.pi * rate * t) * max_delay_ms / 1000
    
    if channels == 2:
        chorus_samples = np.zeros_like(samples)
        for ch in range(2):
            channel_data = samples[:, ch]
            chorus_channel = np.copy(channel_data)

            # Apply modulated delay
            for i in range(len(channel_data)):
                delay_idx = int(lfo[i] * frame_rate)
                src_idx = i - delay_idx
                # Bounds check for both directions
                if 0 <= src_idx < len(channel_data):
                    chorus_channel[i] += channel_data[src_idx] * 0.5

            chorus_samples[:, ch] = chorus_channel
    else:
        chorus_samples = np.copy(samples)
        num_samples = len(samples)
        for i in range(num_samples):
            delay_idx = int(lfo[i] * frame_rate)
            src_idx = i - delay_idx
            # Bounds check for both directions
            if 0 <= src_idx < num_samples:
                chorus_samples[i] += samples[src_idx] * 0.5
    
    # Normalize to prevent clipping
    chorus_samples = chorus_samples * 0.7
    
    return _numpy_to_audio(chorus_samples, frame_rate, channels)


def add_delay(audio: AudioSegment, delay_ms: int = 300, feedback: float = 0.4, mix: float = 0.3) -> AudioSegment:
    """
    Add delay/echo effect.
    
    Args:
        audio: Input audio
        delay_ms: Delay time in milliseconds
        feedback: Amount of feedback (0.0-0.9)
        mix: Mix of wet signal (0.0-1.0)
    """
    samples, frame_rate = _audio_to_numpy(audio)
    channels = audio.channels
    
    delay_samples = int(delay_ms * frame_rate / 1000)
    
    if channels == 2:
        delayed_samples = np.zeros_like(samples)
        for ch in range(2):
            channel_data = samples[:, ch]
            delayed_channel = np.copy(channel_data)
            num_samples = len(channel_data)

            # Apply delay with feedback (bounds-safe)
            if 0 < delay_samples < num_samples:
                for i in range(delay_samples, num_samples):
                    delayed_channel[i] += delayed_channel[i - delay_samples] * feedback

            delayed_samples[:, ch] = delayed_channel
    else:
        delayed_samples = np.copy(samples)
        num_samples = len(samples)
        if 0 < delay_samples < num_samples:
            for i in range(delay_samples, num_samples):
                delayed_samples[i] += delayed_samples[i - delay_samples] * feedback
    
    # Mix dry and wet
    mixed = samples * (1 - mix) + delayed_samples * mix
    
    return _numpy_to_audio(mixed, frame_rate, channels)


def pitch_shift(audio: AudioSegment, semitones: float) -> AudioSegment:
    """
    Shift pitch by semitones using simple resampling.
    
    Args:
        audio: Input audio
        semitones: Number of semitones to shift (positive = up, negative = down)
    """
    # Calculate pitch shift ratio
    ratio = 2 ** (semitones / 12.0)
    
    # Change frame rate to shift pitch (simple method)
    new_frame_rate = int(audio.frame_rate * ratio)
    
    # Resample
    shifted = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
    
    # Convert back to original frame rate to maintain duration
    shifted = shifted.set_frame_rate(audio.frame_rate)
    
    return shifted


def create_harmony_layer(vocals: AudioSegment, interval: int, volume_offset: int = -8) -> AudioSegment:
    """
    Create a harmony layer by pitch shifting.
    
    Args:
        vocals: Original vocal track
        interval: Interval in semitones (e.g., 3 for minor third, 5 for fifth, 7 for fifth)
        volume_offset: Volume adjustment in dB (negative = quieter)
    """
    harmony = pitch_shift(vocals, interval)
    harmony = harmony + volume_offset  # Make harmony quieter than lead
    return harmony


def apply_section_effects(audio: AudioSegment, section_type: str) -> AudioSegment:
    """
    Apply section-specific effects to vocals or instrumentals.
    
    Args:
        audio: Input audio
        section_type: Type of section (intro, verse, chorus, bridge, outro)
    """
    section_type = section_type.lower()
    
    if section_type == "intro":
        # Minimal processing, maybe light reverb
        audio = add_reverb(audio, room_size=0.3, wet_mix=0.2)
    
    elif section_type == "verse":
        # Clean, intimate sound
        audio = add_reverb(audio, room_size=0.4, wet_mix=0.25)
    
    elif section_type == "chorus":
        # Full, rich sound with reverb and chorus
        audio = add_reverb(audio, room_size=0.6, wet_mix=0.35)
        audio = add_chorus(audio, depth=0.25, rate=1.5)
    
    elif section_type == "bridge":
        # Different character - more delay
        audio = add_reverb(audio, room_size=0.5, wet_mix=0.3)
        audio = add_delay(audio, delay_ms=250, feedback=0.3, mix=0.2)
    
    elif section_type == "outro":
        # Spacious, fading
        audio = add_reverb(audio, room_size=0.7, wet_mix=0.4)
    
    return audio


def crossfade_segments(seg1: AudioSegment, seg2: AudioSegment, duration_ms: int = 500) -> AudioSegment:
    """
    Crossfade between two audio segments.
    
    Args:
        seg1: First segment
        seg2: Second segment
        duration_ms: Crossfade duration in milliseconds
    """
    # Ensure segments are long enough
    if len(seg1) < duration_ms or len(seg2) < duration_ms:
        return seg1 + seg2
    
    # Split segments
    seg1_main = seg1[:-duration_ms]
    seg1_tail = seg1[-duration_ms:]
    seg2_head = seg2[:duration_ms]
    seg2_main = seg2[duration_ms:]
    
    # Fade out seg1_tail and fade in seg2_head
    seg1_tail = seg1_tail.fade_out(duration_ms)
    seg2_head = seg2_head.fade_in(duration_ms)
    
    # Overlay the faded sections
    crossfaded = seg1_tail.overlay(seg2_head)
    
    # Combine all parts
    result = seg1_main + crossfaded + seg2_main
    
    return result


def create_vocal_layers(vocals: AudioSegment, section_type: str, num_harmonies: int = 2) -> AudioSegment:
    """
    Create multi-layered vocals with harmonies.
    
    Args:
        vocals: Original vocal track
        section_type: Type of section (determines harmony intensity)
        num_harmonies: Number of harmony layers to add
    """
    # Start with lead vocals
    result = vocals + 2  # Boost lead slightly
    
    # Add harmonies based on section type
    if section_type.lower() in ["chorus", "bridge"]:
        # Full harmonies for chorus and bridge
        harmony_intervals = [3, 5, -3, 7][:num_harmonies]  # Third, fifth, lower third, seventh
        harmony_volumes = [-6, -8, -7, -9][:num_harmonies]  # Different volumes for each
        
        for interval, volume in zip(harmony_intervals, harmony_volumes):
            harmony = create_harmony_layer(vocals, interval, volume)
            result = result.overlay(harmony)
    
    elif section_type.lower() == "verse":
        # Subtle harmonies for verse
        if num_harmonies >= 1:
            harmony = create_harmony_layer(vocals, 5, -10)  # Quiet fifth
            result = result.overlay(harmony)
    
    # Apply section-specific effects to the layered vocals
    result = apply_section_effects(result, section_type)
    
    return result


def apply_dynamic_volume(audio: AudioSegment, section_type: str) -> AudioSegment:
    """
    Apply section-specific volume adjustments.
    
    Args:
        audio: Input audio
        section_type: Type of section
    """
    section_type = section_type.lower()
    
    volume_map = {
        "intro": -3,
        "verse": -2,
        "pre-chorus": 0,
        "chorus": 2,
        "bridge": 0,
        "outro": -4,
    }
    
    adjustment = volume_map.get(section_type, 0)
    return audio + adjustment


def compress_audio(audio: AudioSegment, threshold: float = -20.0, ratio: float = 4.0) -> AudioSegment:
    """
    Apply dynamic range compression for more consistent volume.
    
    Args:
        audio: Input audio
        threshold: Threshold in dB
        ratio: Compression ratio
    """
    # Use pydub's built-in compression
    return compress_dynamic_range(audio, threshold=threshold, ratio=ratio)
