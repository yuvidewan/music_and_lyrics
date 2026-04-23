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
            "url": track.get('external_urls')['spotify']
        }

        songs.append(song_data)

    return songs