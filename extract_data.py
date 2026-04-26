# '''
# api keys here
# https://developer.spotify.com/dashboard/

# documentation here
# https://developer.spotify.com/documentation/web-api
# '''


import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

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

    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    ))
    # https://open.spotify.com/playlist/10VrveaTL07KKG2f4qeTYy?si=BFAwuHxhRv-638Qux_aekg HINDI PARTY
    # https://open.spotify.com/playlist/37i9dQZF1DWWylYLMvjuRG?si=hIxM49QcRii6tNXv46KXJA POP
    # https://open.spotify.com/playlist/3JXeBOl0C7b55w1Y8IiwSx?si=5b7QQXAbS1qUuOxjvs8yvg ROCKAFELLAS
    # https://open.spotify.com/playlist/1Y50zhgUXm0LytYnNYsRZo?si=tqwN-4F7QAyFapIet8JAfA MINE
    results = sp.playlist_tracks("10VrveaTL07KKG2f4qeTYy")
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
