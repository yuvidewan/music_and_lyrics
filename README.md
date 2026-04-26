---
title: Song Game
emoji: M
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
---

# Song Game

A FastAPI music guessing game powered by Spotify playlist data, Genius lyrics, and iTunes preview clips.

The app lets you play multiple modes from the browser:

- `Album Cover`: guess the song, album, and artist from album art
- `Guess the Lyric`: guess the song and artist from lyrics
- `Guess the Song`: guess the song and artist from an audio preview
- `Finish the Lyric`: fill in missing lyric words, with optional extra context lines

It also supports different run types:

- `Classic`: one round
- `Arcade`: a fixed number of rounds
- `Timed`: score as many points as possible before time runs out

## Features

- pulls songs from a Spotify playlist
- cleans playlist metadata for gameplay
- fetches lyrics using Genius
- fetches audio previews using iTunes Search
- caches playlist data, lyrics, and preview URLs for faster repeated rounds
- supports album-art gameplay
- supports finish-the-lyric context reveal
- works with classic, arcade, and timed sessions

## Project Structure

```text
song_game/
├── main.py            # FastAPI app and game/session logic
├── extract_data.py    # Spotify playlist extraction
├── clean_data.py      # Playlist cleanup and normalization
├── song_play.py       # iTunes preview lookup
├── requirements.txt   # Python dependencies
├── static/
│   ├── index.html     # Frontend markup
│   ├── app.js         # Frontend logic
│   └── styles.css     # Frontend styles
└── README.md
```

## Requirements

- Python 3.10+
- Spotify app credentials
- Genius API token

## Environment Variables

Create a `.env` file in `song_game/` with:

```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
LYRICS_KEY=your_genius_access_token
```

## Install

From inside `song_game/`:

```bash
pip install -r requirements.txt
```

## Run

From inside `song_game/`:

```bash
uvicorn main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

## How It Works

1. `extract_data.py` reads tracks from a Spotify playlist.
2. `clean_data.py` extracts the fields needed for the game.
3. `main.py` builds rounds for each mode.
4. The frontend starts a session and submits guesses through the API.
5. Score, progress, timer state, and next rounds are returned by the backend.

## Current Scoring

### Album Cover

- song correct: `50`
- album correct: `30`
- artist correct: `20`
- combo bonus for `2/3`: `15`
- combo bonus for `3/3`: `30`

### Lyrics / Preview

- song correct: `70`
- artist correct: `30`

### Finish the Lyric

- full lyric match: `100`

## API Overview

Main gameplay currently uses:

- `POST /api/session/start`
- `POST /api/session/guess`
- `POST /api/session/end`

There are also dedicated finish-the-lyric helper endpoints still present:

- `POST /api/finish-lyric/start`
- `POST /api/finish-lyric/guess`

## Notes

- `.cache`, virtual environments, `.env`, and `__pycache__` are ignored in git.
- Spotify auth may generate a local `.cache` file after login.
- Some songs may not have lyrics, preview clips, or album images, so the backend skips invalid rounds.

## Possible Next Improvements

- leaderboard / high scores
- custom playlist selection
- fuzzy answer matching for minor typos
- hint penalties
- multiplayer or party mode
