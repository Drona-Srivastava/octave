from apple_music_tui.library import Library


def test_library_schema_and_playlist(tmp_path):
    library = Library(tmp_path)
    library.register_playlist("My Playlist", "https://music.apple.com/us/playlist/x/pl.1")
    assert library.playlists() == ["My Playlist"]
    assert (tmp_path / "Playlists" / "My Playlist" / "playlist.toml").exists()


def test_scan_ignores_non_audio(tmp_path):
    (tmp_path / "notes.txt").write_text("not music")
    assert Library(tmp_path).scan() == 0


def test_playlist_tracks_can_be_edited_in_toml(tmp_path):
    library = Library(tmp_path)
    with library.connect() as db:
        db.execute("INSERT INTO tracks VALUES (?,?,?,?,?,?)", ("song.mp3", "Song", "Artist", "Album", None, None))
    library.register_playlist("Editable", "")
    playlist_file = tmp_path / "Playlists" / "Editable" / "playlist.toml"
    playlist_file.write_text('name = "Editable"\ntracks = ["song.mp3"]\n')
    assert [track.path for track in library.tracks_for_playlist("Editable")] == ["song.mp3"]
