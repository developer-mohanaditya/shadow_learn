from shadowlearn.text import normalize_text, speech_text, split_phrases


def test_normalization_preserves_punctuation():
    assert normalize_text("  Hello,\tworld!\r\nHow are you?  ") == "Hello, world!\nHow are you?"


def test_cues_are_not_spoken_and_pause_is_retained():
    source = "This matters. [pause:long] [emphasis]Say it clearly[/emphasis]. Then continue."
    phrases = split_phrases(source, minimum=1)
    assert "[pause" not in " ".join(item.text for item in phrases)
    assert "[emphasis]" not in " ".join(item.text for item in phrases)
    assert any(item.pause_after_ms == 900 for item in phrases)
    assert phrases[0].text == "This matters."
    assert speech_text(source) == "This matters. Say it clearly. Then continue."


def test_chunks_respect_soft_maximum():
    source = " ".join(f"Sentence number {i} is clear." for i in range(30))
    phrases = split_phrases(source, minimum=80, maximum=250)
    assert len(phrases) > 1
    assert all(len(item.text) <= 280 for item in phrases)
