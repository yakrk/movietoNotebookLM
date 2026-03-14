#!/usr/bin/env python3
"""
YouTube Playlist → NotebookLM

Usage:
    python main.py <youtube-playlist-url> [--title "My Notebook"]

Example:
    python main.py "https://www.youtube.com/playlist?list=PLxxxxx"
    python main.py "https://www.youtube.com/playlist?list=PLxxxxx" --title "My Study Notes"
"""

import argparse
import sys

from playlist_extractor import get_playlist_urls
from notebooklm_automator import add_playlist_to_notebooklm


def main():
    parser = argparse.ArgumentParser(
        description="Import a YouTube playlist into a new NotebookLM notebook."
    )
    parser.add_argument("playlist_url", help="URL of the YouTube playlist")
    parser.add_argument(
        "--title",
        default="",
        help="Optional title for the new NotebookLM notebook",
    )
    args = parser.parse_args()

    print(f"Extracting videos from playlist: {args.playlist_url}\n")
    try:
        video_urls = get_playlist_urls(args.playlist_url)
    except ValueError as e:
        print(f"Error extracting playlist: {e}")
        sys.exit(1)

    if not video_urls:
        print("No videos found in the playlist. Exiting.")
        sys.exit(0)

    add_playlist_to_notebooklm(video_urls, notebook_title=args.title)


if __name__ == "__main__":
    main()
