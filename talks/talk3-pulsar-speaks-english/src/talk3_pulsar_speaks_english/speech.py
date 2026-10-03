"""Text-to-speech for Tier 2's spoken warning: the last hop from text to voice.

Two pieces, kept separate for the same reason synthesizer.py keeps decisions out
of the LLM:

- `normalize_for_speech(text)` — plain code, no TTS involved. Rewrites the few
  tokens a TTS engine reads wrong, checked against Piper's own phonemizer
  rather than guessed: "I-95N" comes out as "eye ninety-five *en*" (the direction
  read as a letter), and "ETA"/"eta" as the word "ee-ta". Corridors become
  "I-95 North"; ETA is spelled out letter by letter.
- `PiperSpeaker` — synthesizes a WAV with Piper and plays it. Piper
  (https://github.com/OHF-Voice/piper1-gpl, `piper-tts` on PyPI) is GPL-3.0, so
  it's deliberately invoked as a separate process — the same arm's-length
  subprocess pattern llm_inference uses for llama.cpp — and never imported or
  added as a dependency of this package. Paths come from arguments or
  PIPER_BINARY_PATH / PIPER_VOICE_PATH; with neither set it runs in mock mode
  (prints instead of speaking), mirroring SubprocessLlmBackend(mock=True), so
  tests and dry runs never need a TTS install. Voice models carry their own
  licenses (see each voice's MODEL_CARD); the demo uses CC0/public-domain ones.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_DIRECTIONS = {"N": "North", "S": "South", "E": "East", "W": "West"}
# "I-95N" / "I-95 N" — a bare direction letter right after an interstate number.
_CORRIDOR = re.compile(r"\b(I-\d+)\s?([NSEW])\b")
_ETA = re.compile(r"\beta\b", re.IGNORECASE)


def normalize_for_speech(text: str) -> str:
    """Rewrite tokens TTS mispronounces; collapse whitespace. Pure, no I/O."""
    text = _CORRIDOR.sub(lambda m: f"{m.group(1)} {_DIRECTIONS[m.group(2)]}", text)
    text = _ETA.sub("E T A", text)
    return " ".join(text.split())


def default_player() -> list[str] | None:
    """The local command that plays a WAV file: afplay on macOS, aplay on Linux (Pi)."""
    candidates = ["afplay"] if sys.platform == "darwin" else ["aplay", "paplay"]
    for name in candidates:
        if path := shutil.which(name):
            return [path, "-q"] if name == "aplay" else [path]
    return None


class PiperSpeaker:
    def __init__(
        self,
        *,
        piper_binary: str | Path | None = None,
        voice_path: str | Path | None = None,
        player: list[str] | None = None,
        mock: bool = False,
    ) -> None:
        binary = piper_binary or os.environ.get("PIPER_BINARY_PATH")
        voice = voice_path or os.environ.get("PIPER_VOICE_PATH")
        self.piper_binary = Path(binary).expanduser() if binary else None
        self.voice_path = Path(voice).expanduser() if voice else None
        self.mock = mock or self.piper_binary is None or self.voice_path is None
        self.player = player if player is not None else default_player()

    def synthesize(self, text: str, wav_path: str | Path) -> Path:
        """Normalize `text` and write it as speech to `wav_path` via the Piper CLI."""
        wav_path = Path(wav_path)
        subprocess.run(
            [
                str(self.piper_binary),
                "--model",
                str(self.voice_path),
                "--output-file",
                str(wav_path),
            ],
            input=normalize_for_speech(text),
            text=True,
            capture_output=True,
            check=True,
        )
        return wav_path

    def speak(self, text: str, *, save_to: str | Path | None = None) -> Path | None:
        """Synthesize and play `text`. Keeps the WAV at `save_to` if given (e.g. to
        cut into a recorded demo); otherwise uses a temp file. Returns the kept WAV's
        path, or None (temp file, or mock mode)."""
        if self.mock:
            print(f"[speak:mock] {normalize_for_speech(text)}")
            return None
        if save_to is not None:
            wav = self.synthesize(text, save_to)
            self._play(wav)
            return wav
        with tempfile.TemporaryDirectory() as tmp:
            wav = self.synthesize(text, Path(tmp) / "warning.wav")
            self._play(wav)
        return None

    def _play(self, wav: Path) -> None:
        if self.player is None:
            raise RuntimeError(
                "no audio player found (expected afplay on macOS, aplay on Linux)"
            )
        subprocess.run([*self.player, str(wav)], check=True)
