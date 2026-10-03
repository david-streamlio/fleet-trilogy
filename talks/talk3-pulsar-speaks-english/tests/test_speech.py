import subprocess

import pytest
from talk3_pulsar_speaks_english import speech
from talk3_pulsar_speaks_english.speech import PiperSpeaker, normalize_for_speech


@pytest.mark.parametrize(
    ("raw", "spoken"),
    [
        # Piper reads a bare direction letter as a letter: "eye ninety-five en".
        ("Approaching I-95N, slow down.", "Approaching I-95 North, slow down."),
        ("Traffic on I-95 N.", "Traffic on I-95 North."),
        ("I-75S and I-285E", "I-75 South and I-285 East"),
        # ...and ETA as the word "ee-ta", in either case.
        ("a potential 8-minute eta impact", "a potential 8-minute E T A impact"),
        ("ETA slipping", "E T A slipping"),
        # Already-speakable text, and words that merely contain the patterns, pass through.
        ("I-95 North is clear", "I-95 North is clear"),
        ("I-95 Northbound beta testers", "I-95 Northbound beta testers"),
        ("  extra   spaces\n", "extra spaces"),
    ],
)
def test_normalize_for_speech(raw, spoken):
    assert normalize_for_speech(raw) == spoken


def test_speaker_without_paths_is_mock_and_prints(monkeypatch, capsys):
    monkeypatch.delenv("PIPER_BINARY_PATH", raising=False)
    monkeypatch.delenv("PIPER_VOICE_PATH", raising=False)
    speaker = PiperSpeaker()
    assert speaker.mock
    assert speaker.speak("Approaching I-95N") is None
    assert "[speak:mock] Approaching I-95 North" in capsys.readouterr().out


def test_speak_runs_piper_on_normalized_text_then_plays(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        speech.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw))
    )
    speaker = PiperSpeaker(
        piper_binary="/bin/piper", voice_path="/v/joe.onnx", player=["afplay"]
    )
    wav = speaker.speak("Approaching I-95N", save_to=tmp_path / "w.wav")

    assert wav == tmp_path / "w.wav"
    (piper_cmd, piper_kw), (play_cmd, _) = calls
    assert piper_cmd == [
        "/bin/piper",
        "--model",
        "/v/joe.onnx",
        "--output-file",
        str(wav),
    ]
    assert piper_kw["input"] == "Approaching I-95 North"
    assert play_cmd == ["afplay", str(wav)]


def test_speak_without_player_fails_loudly(monkeypatch):
    monkeypatch.setattr(
        speech.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0)
    )
    speaker = PiperSpeaker(
        piper_binary="/bin/piper", voice_path="/v/joe.onnx", player=None
    )
    speaker.player = None
    with pytest.raises(RuntimeError, match="no audio player"):
        speaker.speak("hello")
