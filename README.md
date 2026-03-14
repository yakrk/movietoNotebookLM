# YouTube Playlist → NotebookLM

Automatically imports all videos from a YouTube playlist into a new [NotebookLM](https://notebooklm.google.com) notebook as sources.

## How It Works

1. Extracts all video URLs from the YouTube playlist using `yt-dlp`
2. Opens a Chromium browser (via Playwright) with a persistent profile
3. Creates a new NotebookLM notebook
4. Adds each YouTube video URL as a source, one by one

## Requirements

- Python 3.10+
- A Google account with access to NotebookLM

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python main.py "https://www.youtube.com/playlist?list=PLxxxxx"
```

With a custom notebook title:

```bash
python main.py "https://www.youtube.com/playlist?list=PLxxxxx" --title "My Study Notes"
```

## First Run (Authentication)

On the first run, a browser window will open. Log into your Google account and navigate to the NotebookLM homepage. Then return to the terminal and press **Enter** to continue.

Your login session is saved in `~/.notebooklm_profile/`, so you won't need to log in again on subsequent runs.

## Notes

- NotebookLM supports up to 50 sources per notebook. If your playlist has more videos, only the first 50 will be added.
- Only YouTube videos with captions (auto-generated or user-uploaded) are supported as sources in NotebookLM.
- A short delay is added between each source addition to avoid UI issues.
