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


def playlist_id_from_url(value: str | None) -> str:
    if not value:
        return ""

    value = value.strip()
    if not value:
        return ""

    if "open.spotify.com/playlist/" in value:
        playlist_id = value.split("open.spotify.com/playlist/", 1)[1]
        return playlist_id.split("?", 1)[0].split("/", 1)[0]

    if "spotify:playlist:" in value:
        return value.rsplit(":", 1)[-1]

    return value


def extract(
    playlist_url: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
):
    spotify_client_id = client_id or CLIENT_ID
    spotify_client_secret = client_secret or CLIENT_SECRET

    if not spotify_client_id:
        raise RuntimeError("Spotify client ID is missing.")
    if not spotify_client_secret:
        raise RuntimeError("Spotify client secret is missing.")
    playlist_id = playlist_id_from_url(playlist_url)
    if not playlist_id:
        raise RuntimeError("Spotify playlist URL is missing.")

    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
    ))
    results = sp.playlist_tracks(playlist_id)
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
