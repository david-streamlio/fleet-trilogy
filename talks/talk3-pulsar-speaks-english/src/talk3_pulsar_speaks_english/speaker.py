"""The voice at the end of the pipeline: consume IncidentSyntheses, speak each warning.

A plain `pulsar.Client` consumer (same shape as pulsar_adapter.py), not a Pulsar
Function: playing audio is a side effect on whichever machine has the speakers —
the laptop in the demo, a truck's cab in the story — not a stream transformation
whose output belongs on another topic. Subscribes to INCIDENTS_TOPIC, which
GlobalSynthesisFunction / pulsar_adapter.run publish to, and hands each
`spoken_warning` to speech.PiperSpeaker.

`--text` speaks one warning without Pulsar at all (for checking a voice);
`--save-dir` keeps every WAV, numbered in arrival order, plus a `playback.log`
line (`<epoch seconds> <wav name>`) stamped the instant each one starts playing —
deploy/record-talk3-demo.sh lays the WAVs back onto the screen recording at those
offsets, since macOS screen capture can't record system audio on its own.
"""

from __future__ import annotations

import argparse
import logging
import threading
import time
from pathlib import Path

import pulsar
from fleet_telemetry_model import INCIDENTS_TOPIC, IncidentSynthesis, from_json

from talk3_pulsar_speaks_english.speech import PiperSpeaker, normalize_for_speech

logger = logging.getLogger("talk3_pulsar_speaks_english.speaker")

DEFAULT_SUBSCRIPTION_NAME = "tier2-speaker"


def run(
    *,
    service_url: str,
    speaker: PiperSpeaker,
    input_topic: str = INCIDENTS_TOPIC,
    subscription_name: str = DEFAULT_SUBSCRIPTION_NAME,
    stop_event: threading.Event | None = None,
    receive_timeout_millis: int = 1000,
    save_dir: Path | None = None,
) -> None:
    """Speak every IncidentSynthesis arriving on input_topic until stop_event is set."""
    stop_event = stop_event or threading.Event()
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
    spoken = 0
    # Warn, not the client's default Info: this process's output is the on-camera
    # transcript in the recorded demo (deploy/talk3-windows/spoken.sh).
    client = pulsar.Client(
        service_url, logger=pulsar.ConsoleLogger(pulsar.LoggerLevel.Warn)
    )
    try:
        consumer = client.subscribe(input_topic, subscription_name)
        try:
            while not stop_event.is_set():
                try:
                    msg = consumer.receive(timeout_millis=receive_timeout_millis)
                except pulsar.Timeout:
                    continue
                try:
                    synthesis = from_json(IncidentSynthesis, msg.data())
                    spoken += 1
                    save_to = (
                        save_dir / f"{spoken:03d}-{synthesis.corridor}.wav"
                        if save_dir
                        else None
                    )
                    print(
                        f"[{synthesis.corridor} / {synthesis.scope}] {normalize_for_speech(synthesis.spoken_warning)}",
                        flush=True,  # visible live even when stdout is a pipe/log
                    )
                    speaker.speak(
                        synthesis.spoken_warning,
                        save_to=save_to,
                        on_play=_log_playback(save_dir) if save_dir else None,
                    )
                    consumer.acknowledge(msg)
                except Exception:
                    logger.exception("failed to speak message %s", msg.message_id())
                    consumer.negative_acknowledge(msg)
        finally:
            consumer.close()
    finally:
        client.close()


def _log_playback(save_dir: Path):
    def log(wav: Path) -> None:
        with (save_dir / "playback.log").open("a") as f:
            f.write(f"{time.time():.3f} {wav.name}\n")

    return log


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Speak Tier 2 incident warnings aloud with Piper TTS."
    )
    parser.add_argument("--service-url", default="pulsar://localhost:6650")
    parser.add_argument("--input-topic", default=INCIDENTS_TOPIC)
    parser.add_argument("--subscription", default=DEFAULT_SUBSCRIPTION_NAME)
    parser.add_argument(
        "--piper-binary", help="Piper CLI (default: $PIPER_BINARY_PATH)"
    )
    parser.add_argument(
        "--voice", help="Piper .onnx voice model (default: $PIPER_VOICE_PATH)"
    )
    parser.add_argument("--save-dir", type=Path, help="keep every spoken WAV here")
    parser.add_argument("--text", help="speak this one warning and exit (no Pulsar)")
    parser.add_argument("--mock", action="store_true", help="print instead of speaking")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)

    speaker = PiperSpeaker(
        piper_binary=args.piper_binary, voice_path=args.voice, mock=args.mock
    )
    if args.text is not None:
        save_to = args.save_dir / "warning.wav" if args.save_dir else None
        if args.save_dir:
            args.save_dir.mkdir(parents=True, exist_ok=True)
        speaker.speak(args.text, save_to=save_to)
        return
    try:
        run(
            service_url=args.service_url,
            speaker=speaker,
            input_topic=args.input_topic,
            subscription_name=args.subscription,
            save_dir=args.save_dir,
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
