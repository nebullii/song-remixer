"""Fetch album lyrics from Genius API using direct requests."""

import os
import re
import time
from collections import Counter

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://api.genius.com"


def get_headers() -> dict:
    """Get authorization headers."""
    token = os.getenv("GENIUS_ACCESS_TOKEN")
    if not token:
        raise ValueError("GENIUS_ACCESS_TOKEN not found in environment")
    return {"Authorization": f"Bearer {token}"}


def search_songs(query: str, per_page: int = 20) -> list[dict]:
    """Search for songs on Genius."""
    url = f"{BASE_URL}/search"
    params = {"q": query, "per_page": per_page}
    response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()

    hits = response.json()["response"]["hits"]
    return [hit["result"] for hit in hits]


def get_artist_songs(artist_name: str, max_songs: int = 50) -> list[dict]:
    """Get songs by an artist."""
    # First, find the artist
    songs = search_songs(artist_name, per_page=10)
    if not songs:
        raise ValueError(f"No songs found for artist: {artist_name}")

    # Get artist ID from first matching result
    artist_id = None
    for song in songs:
        if artist_name.lower() in song["primary_artist"]["name"].lower():
            artist_id = song["primary_artist"]["id"]
            break

    if not artist_id:
        artist_id = songs[0]["primary_artist"]["id"]

    # Fetch artist's songs
    url = f"{BASE_URL}/artists/{artist_id}/songs"
    params = {"per_page": max_songs, "sort": "popularity"}
    response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()

    return response.json()["response"]["songs"]


def scrape_lyrics(song_url: str) -> str:
    """Scrape lyrics from a Genius song page."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = None
    for _ in range(3):
        response = requests.get(song_url, headers=headers, timeout=10)
        if response.status_code == 200:
            break
        time.sleep(0.5)

    if not response or response.status_code != 200:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")

    # Find lyrics containers
    lyrics_divs = soup.find_all("div", {"data-lyrics-container": "true"})
    if not lyrics_divs:
        # Fallback for alternate layouts
        lyrics_divs = soup.select("div.lyrics, div.lyrics-root")
        if not lyrics_divs:
            return ""

    lyrics_parts = []
    for div in lyrics_divs:
        # Get text, replacing <br> with newlines
        for br in div.find_all("br"):
            br.replace_with("\n")
        lyrics_parts.append(div.get_text())

    return "\n".join(lyrics_parts)


def fetch_song_lyrics(artist_name: str, song_name: str) -> dict:
    """
    Fetch lyrics for a single song.
    Much faster than fetching an entire album.
    """
    query = f"{song_name} {artist_name}"
    songs = search_songs(query, per_page=5)

    if not songs:
        raise ValueError(f"No songs found for '{song_name}' by '{artist_name}'")

    # Find best match
    artist_lower = artist_name.lower()
    song_lower = song_name.lower()

    best_match = None
    for song in songs:
        if artist_lower in song["primary_artist"]["name"].lower():
            if song_lower in song["title"].lower() or song["title"].lower() in song_lower:
                best_match = song
                break
            if not best_match:
                best_match = song

    if not best_match:
        best_match = songs[0]

    print(f"  Fetching: {best_match['title']}")
    lyrics = scrape_lyrics(best_match["url"])

    if not lyrics:
        raise ValueError(f"Could not fetch lyrics for '{song_name}'")

    lyrics = clean_lyrics(lyrics)
    words = extract_words(lyrics)
    word_counts = Counter(words)

    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
                 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our',
                 'their', 'this', 'that', 'these', 'those', 'and', 'but',
                 'or', 'so', 'if', 'then', 'than', 'when', 'where', 'what',
                 'who', 'which', 'how', 'why', 'all', 'each', 'every', 'both',
                 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not',
                 'only', 'own', 'same', 'just', 'can', 'now', 'to', 'of',
                 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'up', 'about',
                 'into', 'over', 'after', 'like', 'get', 'got', 'go', 'going',
                 'gone', 'come', 'came', 'know', 'see', 'want', 'dont', "don't",
                 'im', "i'm", 'ive', "i've", 'youre', "you're", 'its', "it's",
                 'oh', 'yeah', 'ya', 'na', 'la', 'da', 'uh', 'ah', 'ooh', 'hey'}

    themes = [word for word, _ in word_counts.most_common(50)
              if word.lower() not in stopwords and len(word) > 2][:20]

    return {
        "artist": artist_name,
        "album": song_name,  # Use song name as "album" for compatibility
        "track_count": 1,
        "tracks": [{"title": best_match["title"], "lyrics": lyrics}],
        "vocabulary": list(set(words)),
        "themes": themes
    }


def fetch_album_lyrics(artist_name: str, album_name: str) -> dict:
    """Fetch lyrics for songs from an album/artist.
    
    DEPRECATED: Use fetch_single_song for faster processing.
    """
    # Search for songs with album name + artist
    query = f"{album_name} {artist_name}"
    songs = search_songs(query, per_page=20)

    if not songs:
        raise ValueError(f"No songs found for '{album_name}' by '{artist_name}'")

    # Filter songs by artist
    artist_lower = artist_name.lower()
    matching_songs = [
        s for s in songs
        if artist_lower in s["primary_artist"]["name"].lower()
    ]

    if not matching_songs:
        matching_songs = songs[:10]  # Fall back to top results

    tracks = []
    all_words = []

    for song in matching_songs[:12]:  # Limit to avoid rate limiting
        print(f"  Fetching: {song['title']}")
        lyrics = scrape_lyrics(song["url"])

        if lyrics:
            lyrics = clean_lyrics(lyrics)
            tracks.append({"title": song["title"], "lyrics": lyrics})
            all_words.extend(extract_words(lyrics))

        time.sleep(0.3)  # Be nice to the server

    if not tracks:
        raise ValueError(f"Could not fetch lyrics for any songs")

    word_counts = Counter(all_words)

    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
                 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our',
                 'their', 'this', 'that', 'these', 'those', 'and', 'but',
                 'or', 'so', 'if', 'then', 'than', 'when', 'where', 'what',
                 'who', 'which', 'how', 'why', 'all', 'each', 'every', 'both',
                 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not',
                 'only', 'own', 'same', 'just', 'can', 'now', 'to', 'of',
                 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'up', 'about',
                 'into', 'over', 'after', 'like', 'get', 'got', 'go', 'going',
                 'gone', 'come', 'came', 'know', 'see', 'want', 'dont', "don't",
                 'im', "i'm", 'ive', "i've", 'youre', "you're", 'its', "it's",
                 'oh', 'yeah', 'ya', 'na', 'la', 'da', 'uh', 'ah', 'ooh', 'hey'}

    themes = [word for word, _ in word_counts.most_common(100)
              if word.lower() not in stopwords and len(word) > 2][:30]

    return {
        "artist": artist_name,
        "album": album_name,
        "track_count": len(tracks),
        "tracks": tracks,
        "vocabulary": list(set(all_words)),
        "themes": themes
    }


def fetch_single_song(artist_name: str, song_title: str) -> dict:
    """Fetch lyrics for a single song by title and artist. Much faster than fetching an entire album."""
    query = f"{song_title} {artist_name}"
    songs = search_songs(query, per_page=10)

    if not songs:
        raise ValueError(f"No songs found for '{song_title}' by '{artist_name}'")

    # Find the best matching song
    artist_lower = artist_name.lower()
    song_lower = song_title.lower()
    
    best_match = None
    for song in songs:
        if (artist_lower in song["primary_artist"]["name"].lower() and 
            song_lower in song["title"].lower()):
            best_match = song
            break
    
    if not best_match:
        # Fall back to first result
        best_match = songs[0]
    
    print(f"  Fetching: {best_match['title']} by {best_match['primary_artist']['name']}")
    lyrics = scrape_lyrics(best_match["url"])
    
    if not lyrics:
        raise ValueError(f"Could not fetch lyrics for '{song_title}'")
    
    lyrics = clean_lyrics(lyrics)
    all_words = extract_words(lyrics)
    word_counts = Counter(all_words)
    
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
                 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our',
                 'their', 'this', 'that', 'these', 'those', 'and', 'but',
                 'or', 'so', 'if', 'then', 'than', 'when', 'where', 'what',
                 'who', 'which', 'how', 'why', 'all', 'each', 'every', 'both',
                 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not',
                 'only', 'own', 'same', 'just', 'can', 'now', 'to', 'of',
                 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'up', 'about',
                 'into', 'over', 'after', 'like', 'get', 'got', 'go', 'going',
                 'gone', 'come', 'came', 'know', 'see', 'want', 'dont', "don't",
                 'im', "i'm", 'ive', "i've", 'youre', "you're", 'its', "it's",
                 'oh', 'yeah', 'ya', 'na', 'la', 'da', 'uh', 'ah', 'ooh', 'hey'}
    
    themes = [word for word, _ in word_counts.most_common(100)
              if word.lower() not in stopwords and len(word) > 2][:30]
    
    return {
        "artist": best_match["primary_artist"]["name"],
        "song": best_match["title"],
        "track_count": 1,
        "tracks": [{"title": best_match["title"], "lyrics": lyrics}],
        "vocabulary": list(set(all_words)),
        "themes": themes
    }


def clean_lyrics(lyrics: str) -> str:
    """Clean up lyrics text."""
    lyrics = re.sub(r'\[.*?\]', '', lyrics)  # Remove [Verse], [Chorus] etc
    lyrics = re.sub(r'\d*Embed$', '', lyrics)
    lyrics = re.sub(r'You might also like', '', lyrics)
    lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)
    return lyrics.strip()


def extract_words(text: str) -> list[str]:
    """Extract meaningful words from text."""
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    return [w for w in words if len(w) > 1]
