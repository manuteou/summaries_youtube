from summarize_video.utils import slugify

def test_slugify_basic():
    assert slugify("Introduction à Whisper") == "introduction_a_whisper"

def test_slugify_special_chars():
    assert slugify("Vidéo !!! test ???") == "video_test"

def test_slugify_spaces():
    assert slugify("Résumé   vidéo") == "resume_video"