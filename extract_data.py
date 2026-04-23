# '''
# api keys here
# https://developer.spotify.com/dashboard/4a6473d6534b46c088b34b350e6eb2e8

# documentation here
# https://developer.spotify.com/documentation/web-api
# '''

# import spotipy
# from spotipy.oauth2 import SpotifyClientCredentials


# sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
#     client_id=client_id,
#     client_secret=client_secret
# ))

# def get_playlist_data(url):
#     playlist_id = "0XLpyAsUlAZaCfYZnGq2xL"
#     sp.playlist_tracks(playlist_id, market="IN")
#     result = sp.playlist_tracks(url)
#     print(result)

# url = "https://open.spotify.com/playlist/0XLpyAsUlAZaCfYZnGq2xL"
# get_playlist_data(url)


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
    results = sp.playlist_tracks("1Y50zhgUXm0LytYnNYsRZo")
    return results
    # print(type(results))
    # print(results.keys())
    # data = results['items']
    # # print(type(data))
    # for i in data:
    #     print(i)
    #     print("\n")
