def clean_playlist_data(results):
    songs = []

    for entry in results['items']:
        track = entry.get('item')
        
        if track is None:
            continue

        song_data = {
            "name": track.get('name'),
            "artist": track.get('artists')[0]['name'] if track.get('artists') else None,
            "album": track.get('album')['name'] if track.get('album') else None,
            "duration_sec": track.get('duration_ms') // 1000 if track.get('duration_ms') else None,
            "url": track.get('external_urls', {}).get('spotify'),
            "album_image": (
                track.get('album', {}).get('images', [{}])[0].get('url')
                if track.get('album', {}).get('images')
                else None
            ),
            "track_id": track.get('id'),
        }

        if song_data["name"] and song_data["artist"]:
            songs.append(song_data)

    return songs
