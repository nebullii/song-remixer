import hashlib
import os

def get_cache_key(artist, song, style):
    key = f"{artist}_{song}_{style}".lower()
    hash_key = hashlib.md5(key.encode()).hexdigest()[:12]
    return f"cache_{hash_key}.mp3"

test_cases = [
    ("Michael Jackson", "Thriller", "pop, catchy"),
    ("Michael Jackson", "Thriller", "pop"),
    ("michael jackson", "triller", "pop"),
    ("michael jackson", "triller", "pop, catchy"),
    ("Michael Jackson", "triller", "pop, catchy"),
    ("Adele", "Hello", "pop, catchy"),
]

for artist, song, style in test_cases:
    print(f"{artist} - {song} ({style}): {get_cache_key(artist, song, style)}")
