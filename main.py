from pathlib import Path
import random
import re
import time
from typing import Any
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
DEFAULT_PLAYLIST_URL = os.getenv("DEFAULT_PLAYLIST_URL", "")

STATIC_DIR = Path(__file__).parent / "static"
PLAYLIST_CACHE_TTL = 600
ROUND_CACHE_TTL = 1800
ARCADE_OPTIONS = [10, 15, 20, 25, 30]
TIMED_OPTIONS = [30, 60, 90, 120, 150, 180]
SUPPORTED_MODES = {"lyrics", "song", "album", "finish"}
SESSION_TYPES = {"classic", "arcade", "timed"}

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

playlist_cache: dict[str, dict[str, Any]] = {}
lyrics_cache: dict[str, dict[str, Any]] = {}
preview_cache: dict[str, dict[str, Any]] = {}
sessions: dict[str, dict[str, Any]] = {}
finish_lyric_games: dict[str, dict[str, Any]] = {}
genius_clients: dict[str, lyricsgenius.Genius] = {}


class StartSessionRequest(BaseModel):
    mode: str
    session_type: str = "classic"
    round_limit: int | None = None
    duration_seconds: int | None = None
    playlist_url: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    lyrics_key: str = ""


class SessionGuessRequest(BaseModel):
    session_id: str
    song_name: str = ""
    artist: str = ""
    album_name: str = ""
    lyric: str = ""


class FinishLyricGuess(BaseModel):
    game_id: str
    lyric: str


class EndSessionRequest(BaseModel):
    session_id: str


class DefaultSettingsResponse(BaseModel):
    playlist_url: str = ""


def now_ts() -> float:
    return time.time()


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[^a-z0-9\s]", "", value.lower())
    return " ".join(cleaned.split())


def song_key(song: dict[str, Any]) -> str:
    return f"{normalize_text(song['name'])}::{normalize_text(song['artist'])}"


def clean_setting(value: str | None) -> str:
    return value.strip() if value else ""


def request_settings(request: StartSessionRequest) -> dict[str, str]:
    return {
        "playlist_url": clean_setting(request.playlist_url) or DEFAULT_PLAYLIST_URL,
        "spotify_client_id": clean_setting(request.spotify_client_id),
        "spotify_client_secret": clean_setting(request.spotify_client_secret),
        "lyrics_key": clean_setting(request.lyrics_key),
    }


def playlist_cache_key(settings: dict[str, str]) -> str:
    return "::".join([
        settings["playlist_url"],
        settings["spotify_client_id"],
        settings["spotify_client_secret"],
    ])


def lyrics_cache_key(song: dict[str, Any], lyrics_key: str) -> str:
    return f"{lyrics_key or 'server'}::{song_key(song)}"


def genius_result_matches_artist(song: Any, artist: str) -> bool:
    genius_artist = normalize_text(song.artist)
    artist = normalize_text(artist)
    return artist in genius_artist or genius_artist in artist


def get_genius_client(lyrics_key: str = "") -> lyricsgenius.Genius:
    token = lyrics_key or LYRIC_KEY
    if not token:
        raise RuntimeError("Genius API token is missing.")
    if token not in genius_clients:
        genius_clients[token] = lyricsgenius.Genius(token, timeout=15, retries=1)
    return genius_clients[token]


def load_songs(settings: dict[str, str] | None = None, force_refresh: bool = False) -> list[dict[str, Any]]:
    settings = settings or request_settings(StartSessionRequest(mode="album"))
    key = playlist_cache_key(settings)
    cached = playlist_cache.get(key)
    if (
        not force_refresh
        and cached is not None
        and cached["expires_at"] > now_ts()
    ):
        return cached["songs"]

    results = extract(
        playlist_url=settings["playlist_url"],
        client_id=settings["spotify_client_id"] or None,
        client_secret=settings["spotify_client_secret"] or None,
    )
    songs = clean_playlist_data(results=results)
    if not songs:
        raise RuntimeError("No songs found in playlist")

    playlist_cache[key] = {
        "songs": songs,
        "expires_at": now_ts() + PLAYLIST_CACHE_TTL,
    }
    return songs


def get_cached_lyrics(song: dict[str, Any], lyrics_key: str = "") -> str | None:
    key = lyrics_cache_key(song, lyrics_key)
    cached = lyrics_cache.get(key)
    if cached and cached["expires_at"] > now_ts():
        return cached["lyrics"]

    genius = get_genius_client(lyrics_key)
    result = genius.search_song(song["name"], song["artist"])
    if result is None or result.lyrics is None:
        return None
    if not genius_result_matches_artist(result, song["artist"]):
        return None

    lyrics_cache[key] = {
        "lyrics": result.lyrics,
        "expires_at": now_ts() + ROUND_CACHE_TTL,
    }
    return result.lyrics


def get_cached_preview(song: dict[str, Any]) -> str | None:
    key = song_key(song)
    cached = preview_cache.get(key)
    if cached and cached["expires_at"] > now_ts():
        return cached["preview_url"]

    preview = get_itunes_preview(song["name"], song["artist"])
    if preview is None or preview.get("preview_url") is None:
        return None

    preview_cache[key] = {
        "preview_url": preview["preview_url"],
        "expires_at": now_ts() + ROUND_CACHE_TTL,
    }
    return preview["preview_url"]


def scrub_lyrics_for_display(lyrics: str) -> str:
    body = lyrics.split("Lyrics", 1)[-1]
    body = re.sub(r"You might also like.*", "", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"\d*Embed\s*$", "", body).strip()
    return body or lyrics


def build_lyrics_round(song: dict[str, Any], settings: dict[str, str] | None = None) -> dict[str, Any] | None:
    settings = settings or {}
    lyrics = get_cached_lyrics(song, settings.get("lyrics_key", ""))
    if not lyrics:
        return None

    return {
        "mode": "lyrics",
        "prompt": {
            "lyrics": scrub_lyrics_for_display(lyrics),
        },
        "answer": {
            "song_name": song["name"],
            "artist": song["artist"],
            "album_name": song["album"],
        },
        "score_type": "song_artist",
    }


def build_song_round(song: dict[str, Any]) -> dict[str, Any] | None:
    preview_url = get_cached_preview(song)
    if not preview_url:
        return None

    return {
        "mode": "song",
        "prompt": {
            "preview_url": preview_url,
        },
        "answer": {
            "song_name": song["name"],
            "artist": song["artist"],
            "album_name": song["album"],
        },
        "score_type": "song_artist",
    }


def build_album_round(song: dict[str, Any]) -> dict[str, Any] | None:
    if not song.get("album_image"):
        return None

    return {
        "mode": "album",
        "prompt": {
            "image_url": song["album_image"],
        },
        "answer": {
            "song_name": song["name"],
            "artist": song["artist"],
            "album_name": song["album"],
        },
        "score_type": "album_cover",
    }


def lyric_candidate_lines(lyrics: str) -> list[str]:
    cleaned = scrub_lyrics_for_display(lyrics)
    lines = []

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[") or "]" in line:
            continue
        word_count = len(line.split())
        if 5 <= word_count <= 14:
            lines.append(line)

    return lines


def lyric_context_lines(lyrics: str) -> list[str]:
    cleaned = scrub_lyrics_for_display(lyrics)
    lines = []

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[") or "]" in line:
            continue
        lines.append(line)

    return lines


def build_finish_lyric_round(song: dict[str, Any], settings: dict[str, str] | None = None) -> dict[str, Any] | None:
    settings = settings or {}
    lyrics = get_cached_lyrics(song, settings.get("lyrics_key", ""))
    if not lyrics:
        return None

    all_lines = lyric_context_lines(lyrics)
    candidates = lyric_candidate_lines(lyrics)
    if not candidates:
        return None

    full_line = random.choice(candidates)
    try:
        line_index = all_lines.index(full_line)
    except ValueError:
        line_index = -1

    words = full_line.split()
    missing_count = max(2, min(4, len(words) // 2))
    prompt_words = words[:-missing_count]
    missing_words = words[-missing_count:]

    context_pool = []
    if line_index >= 0:
        nearby_indexes = [
            line_index - 2,
            line_index - 1,
            line_index + 1,
            line_index + 2,
        ]
        for idx in nearby_indexes:
            if 0 <= idx < len(all_lines):
                context_pool.append(all_lines[idx])

    return {
        "song_name": song["name"],
        "artist": song["artist"],
        "album_name": song["album"],
        "prompt_text": " ".join(prompt_words),
        "missing_word_count": len(missing_words),
        "blanks": " ".join("_" * len(word) for word in missing_words),
        "context_lines": context_pool,
        "answer_text": " ".join(missing_words),
        "full_line": full_line,
    }


def get_finish_lyric_data_for_frontend(settings: dict[str, str] | None = None) -> dict[str, Any]:
    # Returns one finish-the-lyric round for the frontend.
    #
    # Frontend should expect a Python dict / JSON object with:
    # {
    #   "game_id": str
    #       unique id for this round; send it back when user submits an answer
    #
    #   "prompt_text": str
    #       the visible beginning of the lyric line
    #       frontend can render this directly as normal text
    #
    #   "blanks": str
    #       underscores for the missing words, for example "_ ____ ___"
    #       frontend can show this right after prompt_text
    #
    #   "missing_word_count": int
    #       how many words are missing; useful if you want a hint like
    #       "3 words missing"
    #
    #   "meta": {
    #       "song_name": str,
    #       "artist": str,
    #       "album_name": str | None,
    #   }
    #       optional extra data. if you do not want spoilers in the UI,
    #       do not show this before the round ends. it can still be useful
    #       for debugging or internal state.
    #
    #   "answer": {
    #       "expected_text": str,
    #       "full_line": str,
    #   }
    #       backend/helper-side answer data. frontend should NOT show this
    #       before the user submits. keep it hidden client-side or strip it
    #       out if you expose this through an endpoint.
    # }
    settings = settings or request_settings(StartSessionRequest(mode="finish"))
    songs = load_songs(settings)
    shuffled = songs[:]
    random.shuffle(shuffled)

    for song in shuffled:
        round_data = build_finish_lyric_round(song, settings)
        if round_data is None:
            continue

        game_id = str(uuid4())
        return {
            "game_id": game_id,
            "prompt_text": round_data["prompt_text"],
            "blanks": round_data["blanks"],
            "missing_word_count": round_data["missing_word_count"],
            "meta": {
                "song_name": round_data["song_name"],
                "artist": round_data["artist"],
                "album_name": round_data["album_name"],
            },
            "answer": {
                "expected_text": round_data["answer_text"],
                "full_line": round_data["full_line"],
            },
        }

    raise RuntimeError("Could not prepare a finish-the-lyric round.")


def build_round(mode: str, song: dict[str, Any], settings: dict[str, str] | None = None) -> dict[str, Any] | None:
    settings = settings or {}
    if mode == "lyrics":
        return build_lyrics_round(song, settings)
    if mode == "song":
        return build_song_round(song)
    if mode == "album":
        return build_album_round(song)
    if mode == "finish":
        finish_data = build_finish_lyric_round(song, settings)
        if finish_data is None:
            return None

        return {
            "mode": "finish",
            "prompt": {
                "prompt_text": finish_data["prompt_text"],
                "blanks": finish_data["blanks"],
                "missing_word_count": finish_data["missing_word_count"],
                "context_lines": finish_data["context_lines"],
            },
            "answer": {
                "lyric": finish_data["answer_text"],
                "full_line": finish_data["full_line"],
                "song_name": finish_data["song_name"],
                "artist": finish_data["artist"],
                "album_name": finish_data["album_name"],
            },
            "score_type": "finish_lyric",
        }
    return None


def pick_rounds(mode: str, count: int, settings: dict[str, str] | None = None) -> list[dict[str, Any]]:
    settings = settings or request_settings(StartSessionRequest(mode=mode))
    songs = load_songs(settings)
    if not songs:
        raise RuntimeError("No songs found in playlist")

    shuffled = songs[:]
    random.shuffle(shuffled)
    rounds = []

    for song in shuffled:
        round_data = build_round(mode, song, settings)
        if round_data is not None:
            rounds.append(round_data)
        if len(rounds) >= count:
            break

    if len(rounds) < count:
        raise RuntimeError(f"Could not prepare enough {mode} rounds from your playlist.")

    return rounds


def ensure_session_values(request: StartSessionRequest) -> tuple[int | None, int | None]:
    if request.mode not in SUPPORTED_MODES:
        raise RuntimeError("Unsupported mode.")
    if request.session_type not in SESSION_TYPES:
        raise RuntimeError("Unsupported session type.")

    if request.session_type == "classic":
        return 1, None

    if request.session_type == "arcade":
        round_limit = request.round_limit or 10
        if round_limit not in ARCADE_OPTIONS:
            raise RuntimeError("Arcade mode supports 10, 15, 20, 25, or 30 songs.")
        return round_limit, None

    duration_seconds = request.duration_seconds or 30
    if duration_seconds not in TIMED_OPTIONS:
        raise RuntimeError("Timed mode supports 30, 60, 90, 120, 150, or 180 seconds.")
    return None, duration_seconds


def build_progress(session: dict[str, Any]) -> dict[str, Any]:
    time_remaining = None
    if session["session_type"] == "timed":
        time_remaining = max(0, int(session["ends_at"] - now_ts()))

    total_rounds = session["round_limit"]
    round_index = session["current_index"] + 1 if session["current_round"] else session["current_index"]

    return {
        "round_index": round_index,
        "total_rounds": total_rounds,
        "time_remaining": time_remaining,
        "score": session["score"],
    }


def public_round_payload(session: dict[str, Any]) -> dict[str, Any]:
    current_round = session["current_round"]
    if current_round is None:
        raise RuntimeError("No active round available.")

    payload = {
        "mode": current_round["mode"],
        "prompt": current_round["prompt"],
    }
    progress = build_progress(session)
    payload["progress"] = progress
    return payload


def advance_session(session: dict[str, Any]) -> None:
    if session["session_type"] == "timed":
        if now_ts() >= session["ends_at"]:
            session["current_round"] = None
            return

        if session["current_index"] >= len(session["rounds"]):
            extra_rounds = pick_rounds(session["mode"], 8, session["settings"])
            session["rounds"].extend(extra_rounds)
    elif session["current_index"] >= len(session["rounds"]):
        session["current_round"] = None
        return

    session["current_round"] = session["rounds"][session["current_index"]]


def create_session(request: StartSessionRequest) -> dict[str, Any]:
    round_limit, duration_seconds = ensure_session_values(request)
    settings = request_settings(request)

    if request.session_type == "timed":
        initial_rounds = pick_rounds(request.mode, 12, settings)
    else:
        initial_rounds = pick_rounds(request.mode, round_limit or 1, settings)

    session_id = str(uuid4())
    session = {
        "id": session_id,
        "mode": request.mode,
        "session_type": request.session_type,
        "round_limit": round_limit,
        "duration_seconds": duration_seconds,
        "score": 0,
        "current_index": 0,
        "rounds": initial_rounds,
        "current_round": None,
        "ends_at": now_ts() + duration_seconds if duration_seconds else None,
        "settings": settings,
    }
    advance_session(session)
    sessions[session_id] = session

    if session["current_round"] is None:
        raise RuntimeError("Could not start a round right now.")

    return {
        "session_id": session_id,
        "mode": session["mode"],
        "session_type": session["session_type"],
        "round": public_round_payload(session),
    }


def score_song_artist_round(guess: SessionGuessRequest, answer: dict[str, Any]) -> dict[str, Any]:
    song_correct = normalize_text(guess.song_name) == normalize_text(answer["song_name"])
    artist_correct = normalize_text(guess.artist) == normalize_text(answer["artist"])
    points = (70 if song_correct else 0) + (30 if artist_correct else 0)

    if song_correct and artist_correct:
        message = "Perfect hit."
    elif song_correct or artist_correct:
        message = "Partial hit."
    else:
        message = "Miss."

    return {
        "points": points,
        "success": points > 0,
        "message": message,
        "breakdown": {
            "song": song_correct,
            "artist": artist_correct,
        },
    }


def score_album_round(guess: SessionGuessRequest, answer: dict[str, Any]) -> dict[str, Any]:
    song_correct = normalize_text(guess.song_name) == normalize_text(answer["song_name"])
    album_correct = normalize_text(guess.album_name) == normalize_text(answer["album_name"])
    artist_correct = normalize_text(guess.artist) == normalize_text(answer["artist"])

    points = 0
    points += 50 if song_correct else 0
    points += 30 if album_correct else 0
    points += 20 if artist_correct else 0

    matches = sum([song_correct, album_correct, artist_correct])
    combo_bonus = 0
    if matches == 2:
        combo_bonus = 15
    elif matches == 3:
        combo_bonus = 30
    points += combo_bonus

    if matches == 3:
        message = "Nailed all three."
    elif matches == 2:
        message = "Strong round."
    elif matches == 1:
        message = "One part right."
    else:
        message = "No match."

    return {
        "points": points,
        "success": matches > 0,
        "message": message,
        "breakdown": {
            "song": song_correct,
            "album": album_correct,
            "artist": artist_correct,
            "combo_bonus": combo_bonus,
        },
    }


def score_finish_lyric_round(guess: SessionGuessRequest, answer: dict[str, Any]) -> dict[str, Any]:
    lyric_correct = normalize_text(guess.lyric) == normalize_text(answer["lyric"])

    return {
        "points": 100 if lyric_correct else 0,
        "success": lyric_correct,
        "message": "Perfect line." if lyric_correct else "Not quite.",
        "breakdown": {
            "lyric": lyric_correct,
        },
    }


def score_current_round(session: dict[str, Any], guess: SessionGuessRequest) -> dict[str, Any]:
    current_round = session["current_round"]
    if current_round is None:
        raise RuntimeError("Session is finished. Start a new run.")

    answer = current_round["answer"]
    if current_round["score_type"] == "album_cover":
        return score_album_round(guess, answer)
    if current_round["score_type"] == "finish_lyric":
        return score_finish_lyric_round(guess, answer)
    return score_song_artist_round(guess, answer)


def submit_session_guess(guess: SessionGuessRequest) -> dict[str, Any]:
    session = sessions.get(guess.session_id)
    if session is None:
        raise RuntimeError("Session not found. Start a new game.")

    if session["session_type"] == "timed" and now_ts() >= session["ends_at"]:
        session["current_round"] = None
        return {
            "finished": True,
            "score": session["score"],
            "progress": build_progress(session),
            "round_result": None,
            "next_round": None,
        }

    current_round = session["current_round"]
    if current_round is None:
        raise RuntimeError("Session is already finished.")

    result = score_current_round(session, guess)
    session["score"] += result["points"]

    answer = current_round["answer"]
    session["current_index"] += 1
    advance_session(session)

    finished = session["current_round"] is None
    if session["session_type"] == "timed" and session["ends_at"] is not None and now_ts() >= session["ends_at"]:
        finished = True
        session["current_round"] = None

    return {
        "finished": finished,
        "score": session["score"],
        "progress": build_progress(session),
        "round_result": {
            "message": result["message"],
            "points_awarded": result["points"],
            "success": result["success"],
            "breakdown": result["breakdown"],
            "answer": answer,
        },
        "next_round": None if finished else public_round_payload(session),
    }


def end_session(request: EndSessionRequest) -> dict[str, Any]:
    session = sessions.get(request.session_id)
    if session is None:
        raise RuntimeError("Session not found.")

    session["current_round"] = None
    return {
        "finished": True,
        "score": session["score"],
        "progress": build_progress(session),
        "round_result": None,
        "next_round": None,
    }


def start_finish_lyric_game() -> dict[str, Any]:
    data = get_finish_lyric_data_for_frontend()
    finish_lyric_games[data["game_id"]] = {
        "answer_text": data["answer"]["expected_text"],
        "full_line": data["answer"]["full_line"],
        "song_name": data["meta"]["song_name"],
        "artist": data["meta"]["artist"],
        "album_name": data["meta"]["album_name"],
    }

    return {
        "game_id": data["game_id"],
        "prompt_text": data["prompt_text"],
        "blanks": data["blanks"],
        "missing_word_count": data["missing_word_count"],
    }


def submit_finish_lyric_guess(guess: FinishLyricGuess) -> dict[str, Any]:
    game = finish_lyric_games.get(guess.game_id)
    if game is None:
        raise RuntimeError("Finish-the-lyric game not found.")

    expected = normalize_text(game["answer_text"])
    actual = normalize_text(guess.lyric)
    success = actual == expected

    return {
        "success": success,
        "message": "Perfect line." if success else "Not quite.",
        "answer": {
            "missing_lyric": game["answer_text"],
            "full_line": game["full_line"],
            "song_name": game["song_name"],
            "artist": game["artist"],
            "album_name": game["album_name"],
        },
    }


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/settings/defaults")
def default_settings() -> DefaultSettingsResponse:
    return DefaultSettingsResponse(playlist_url=DEFAULT_PLAYLIST_URL)


@app.post("/api/session/start")
async def start_session(request: StartSessionRequest):
    try:
        return await run_in_threadpool(create_session, request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/session/guess")
async def guess_session(request: SessionGuessRequest):
    try:
        return await run_in_threadpool(submit_session_guess, request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/session/end")
async def finish_session(request: EndSessionRequest):
    try:
        return await run_in_threadpool(end_session, request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/finish-lyric/start")
async def start_finish_lyric():
    try:
        return await run_in_threadpool(start_finish_lyric_game)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/finish-lyric/guess")
async def guess_finish_lyric(request: FinishLyricGuess):
    try:
        return await run_in_threadpool(submit_finish_lyric_guess, request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
