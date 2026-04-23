import requests

#https://itunes.apple.com/search?term=SONG+ARTIST&media=music&entity=song&limit=1

def get_itunes_preview(name,artist):
    query = f"{name} {artist}"

    response = requests.get(
        "https://itunes.apple.com/search",
        params={
            "term":query,
            "media":"music",
            "entity":"song",
            "limit":1,
        },
        timeout=10,
    )

    data = response.json()
    if data["resultCount"] == 0:
        return None
    result = data["results"][0]

    return {
        "track_name":result.get("trackName"),
        "artist":result.get("artistName"),
        "preview_url":result.get("previewUrl")
    }