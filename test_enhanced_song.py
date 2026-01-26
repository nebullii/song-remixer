"""Test script for enhanced song generator with vocal and instrumental variations."""

from src.music_generator import generate_and_download

# Sample lyrics with proper section markers
test_lyrics = """[Verse 1]
Walking down the street tonight
City lights are shining bright
Feel the rhythm in my soul
Music makes me feel whole

[Chorus]
We're dancing in the moonlight
Everything feels so right
We're dancing in the moonlight
All through the night

[Verse 2]
Stars above are gleaming
This moment feels like dreaming
Your hand in mine so tight
Perfect summer night

[Chorus]
We're dancing in the moonlight
Everything feels so right
We're dancing in the moonlight
All through the night

[Bridge]
Time stands still when we're together
This feeling lasts forever
Nothing else matters now
We're here and that's enough somehow

[Chorus]
We're dancing in the moonlight
Everything feels so right
We're dancing in the moonlight
All through the night"""

def test_full_features():
    """Test with all enhancements enabled."""
    print("=" * 60)
    print("Testing Enhanced Song Generator")
    print("=" * 60)
    print("\n🎵 Generating song with ALL enhancements:")
    print("   ✓ Vocal harmonies in chorus/bridge")
    print("   ✓ Section-specific instrumentals")
    print("   ✓ Intro and outro")
    print("   ✓ Audio effects (reverb, chorus, delay)")
    print("   ✓ Smooth crossfade transitions")
    print("\nThis will take a few minutes...\n")
    
    output_path = generate_and_download(
        lyrics=test_lyrics,
        title="Moonlight Dance",
        style="pop",
        mood="energetic",
        vocal_gender="female",
        output_dir="output",
        add_harmonies=True,      # Enable vocal harmonies
        add_intro_outro=True,    # Add intro/outro
    )
    
    print("\n" + "=" * 60)
    print(f"✅ SUCCESS! Song generated: {output_path}")
    print("=" * 60)
    print("\n🎧 Listen to your song to hear:")
    print("   • Intro with atmospheric build")
    print("   • Verse with light instrumentation")
    print("   • Chorus with full harmonies and rich sound")
    print("   • Bridge with different mood and effects")
    print("   • Outro with smooth fade-out")
    print("   • Smooth transitions between all sections")
    
    return output_path


def test_simple_version():
    """Test without harmonies and intro/outro for comparison."""
    print("\n" + "=" * 60)
    print("Testing Simple Version (for comparison)")
    print("=" * 60)
    print("\n🎵 Generating simpler version without:")
    print("   ✗ No vocal harmonies")
    print("   ✗ No intro/outro")
    print("   ✓ Still has section-specific effects")
    print("\nThis will be faster...\n")
    
    output_path = generate_and_download(
        lyrics=test_lyrics,
        title="Moonlight Dance Simple",
        style="pop",
        mood="energetic",
        vocal_gender="female",
        output_dir="output",
        add_harmonies=False,     # Disable harmonies
        add_intro_outro=False,   # No intro/outro
    )
    
    print("\n" + "=" * 60)
    print(f"✅ Simple version generated: {output_path}")
    print("=" * 60)
    print("\n💡 Compare this with the full version to hear the difference!")
    
    return output_path


if __name__ == "__main__":
    import sys
    
    print("\n🎼 Enhanced Song Generator Test\n")
    print("Choose a test option:")
    print("1. Full version with all enhancements (recommended)")
    print("2. Simple version without harmonies/intro/outro")
    print("3. Both versions for comparison")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    try:
        if choice == "1":
            test_full_features()
        elif choice == "2":
            test_simple_version()
        elif choice == "3":
            test_full_features()
            test_simple_version()
        else:
            print("Invalid choice. Running full version by default...")
            test_full_features()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Set REPLICATE_API_TOKEN in your .env file")
        print("2. Installed all dependencies: pip install -r requirements.txt")
        sys.exit(1)
