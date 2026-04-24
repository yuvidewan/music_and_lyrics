# '''
# api keys here
# https://developer.spotify.com/dashboard/

# documentation here
# https://developer.spotify.com/documentation/web-api
# '''


import spotipy
from spotipy.oauth2 import SpotifyOAuth

from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

def extract():
    if not CLIENT_ID:
        raise RuntimeError("SPOTIFY_CLIENT_ID is missing from .env")
    if not CLIENT_SECRET:
        raise RuntimeError("SPOTIFY_CLIENT_SECRET is missing from .env")

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id = CLIENT_ID,
        client_secret = CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="playlist-read-private",
        cache_path=".cache"
    ))
    # https://open.spotify.com/playlist/3JXeBOl0C7b55w1Y8IiwSx?si=5b7QQXAbS1qUuOxjvs8yvg ROCKAFELLAS
    # https://open.spotify.com/playlist/1Y50zhgUXm0LytYnNYsRZo?si=tqwN-4F7QAyFapIet8JAfA MINE
    results = sp.playlist_tracks("3JXeBOl0C7b55w1Y8IiwSx")
    items = list(results.get("items", []))

    while results.get("next"):
        results = sp.next(results)
        items.extend(results.get("items", []))

    return {"items": items}
    # print(type(results))
    # print(results.keys())
    # data = results['items']
    # # print(type(data))
    # for i in data:
    #     print(i)
    #     print("\n")
