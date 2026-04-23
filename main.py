from pathlib import Path
import random
from uuid import uuid4

import lyricsgenius
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from extract_data import extract
from clean_data import clean_playlist_data
from song_play import get_itunes_preview

from dotenv import load_dotenv
import os

load_dotenv()
LYRIC_KEY = os.getenv("LYRICS_KEY")

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

games = {}


class Guess(BaseModel):
    game_id: str
    song_name: str
    artist: str


def genius_result_matches_artist(song, artist):
    genius_artist = song.artist.lower()
    artist = artist.lower()
    return artist in genius_artist or genius_artist in artist


def play():
    if not LYRIC_KEY:
        raise RuntimeError("LYRICS_KEY is missing from .env")

    results = extract()
    songs = clean_playlist_data(results=results)

    total_songs = len(songs)
    if total_songs == 0:
        raise RuntimeError("No songs found in playlist")

    genius = lyricsgenius.Genius(LYRIC_KEY, timeout=15, retries=1)

    for _ in range(10):
        idx = random.randint(0, total_songs - 1)
        name = songs[idx]["name"]
        artist = songs[idx]["artist"]

        song = genius.search_song(name, artist)
        if song is None or song.lyrics is None:
            print(f"No Genius lyrics found for {artist} - {name}")
            continue

        if not genius_result_matches_artist(song, artist):
            print(f"Bad Genius match for {artist} - {name}: got {song.artist} - {song.title}")
            continue

        return name.lower(), artist.lower(), song.lyrics

    raise RuntimeError("Lyrics not found for the selected songs. Press play again.")


def play_song_preview():
    results = extract()
    songs = clean_playlist_data(results=results)

    total_songs = len(songs)
    if total_songs == 0:
        raise RuntimeError("No songs found in playlist")

    for _ in range(10):
        idx = random.randint(0, total_songs - 1)
        name = songs[idx]["name"]
        artist = songs[idx]["artist"]

        preview = get_itunes_preview(name, artist)
        if preview is None or preview.get("preview_url") is None:
            print(f"No iTunes preview found for {artist} - {name}")
            continue

        return name.lower(), artist.lower(), preview["preview_url"]

    raise RuntimeError("Preview not found for the selected songs. Press play again.")


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/game/start")
async def start_game():
    try:
        name, artist, lyrics = await run_in_threadpool(play)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    game_id = str(uuid4())
    games[game_id] = {
        "name": name,
        "artist": artist,
    }

    return {
        "game_id": game_id,
        "lyrics": lyrics,
    }


@app.post("/api/song/start")
async def start_song_game():
    try:
        name, artist, preview_url = await run_in_threadpool(play_song_preview)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    game_id = str(uuid4())
    games[game_id] = {
        "name": name,
        "artist": artist,
    }

    return {
        "game_id": game_id,
        "preview_url": preview_url,
    }


@app.post("/api/game/guess")
def guess_song(guess: Guess):
    game = games.get(guess.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found. Press play again.")

    ans_name = guess.song_name.lower()
    ans_artist = guess.artist.lower()

    if ans_name == game["name"] or ans_artist == game["artist"]:
        result = "SUCCESS"
        success = True
    else:
        result = "NO BUENO"
        success = False

    return {
        "success": success,
        "message": result,
        "answer": {
            "song_name": game["name"],
            "artist": game["artist"],
        },
    }
