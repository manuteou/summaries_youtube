from downloader import download_audio

def test_download_audio(monkeypatch):
    class DummyStream:
        def download(self):
            return "fake_audio.mp3"

    class DummyYT:
        title = "Fake Video"
        streams = type("s", (), {"get_audio_only": lambda self: DummyStream()})()

    monkeypatch.setattr("pytubefix.YouTube", lambda url, on_progress_callback=None: DummyYT())
    audio_file, title = download_audio("http://fake.url")
    assert audio_file == "fake_audio.mp3"
    assert title == "Fake Video"