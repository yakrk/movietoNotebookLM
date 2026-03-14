import yt_dlp


def get_playlist_urls(playlist_url: str) -> list[str]:
    """Extract all video URLs from a YouTube playlist."""
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    if not info:
        raise ValueError("Could not extract playlist info. Check the URL.")

    entries = info.get("entries", [])
    if not entries:
        raise ValueError("Playlist appears to be empty or private.")

    urls = [
        f"https://www.youtube.com/watch?v={entry['id']}"
        for entry in entries
        if entry and entry.get("id")
    ]

    print(f"Found {len(urls)} videos in playlist: {info.get('title', 'Unknown Playlist')}")
    return urls
