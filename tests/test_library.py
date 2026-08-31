from apple_music_tui.library import Library


def test_library_schema_and_playlist(tmp_path):
    library = Library(tmp_path)
    library.register_playlist("My Playlist", "https://music.apple.com/us/playlist/x/pl.1")
    assert library.playlists() == ["My Playlist"]
    assert (tmp_path / "Playlists" / "My Playlist" / "playlist.toml").exists()


def test_scan_ignores_non_audio(tmp_path):
    (tmp_path / "notes.txt").write_text("not music")
    assert Library(tmp_path).scan() == 0
