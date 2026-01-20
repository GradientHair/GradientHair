import argparse
import io
import queue
import sys
import threading
import wave
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd
from openai import OpenAI


@dataclass
class AudioConfig:
    samplerate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    device: Optional[str] = None


def list_input_devices() -> str:
    return sd.query_devices()


def _audio_to_wav_bytes(audio: np.ndarray, samplerate: int, channels: int) -> bytes:
    if audio.size == 0:
        raise ValueError("No audio captured. Try again with a longer recording.")
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # int16
            wf.setframerate(samplerate)
            wf.writeframes(audio.tobytes())
        return buffer.getvalue()


def record_until_enter(config: AudioConfig) -> bytes:
    print("Press Enter to start recording.")
    input()

    q: queue.Queue[np.ndarray] = queue.Queue()
    stop_event = threading.Event()

    def callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())
        if stop_event.is_set():
            raise sd.CallbackStop()

    print("Recording... Press Enter to stop.")
    with sd.InputStream(
        samplerate=config.samplerate,
        channels=config.channels,
        dtype=config.dtype,
        device=config.device,
        callback=callback,
    ):
        input()
        stop_event.set()

    frames = []
    while not q.empty():
        frames.append(q.get())

    if not frames:
        raise ValueError("No audio captured. Try again.")

    audio = np.concatenate(frames, axis=0)
    return _audio_to_wav_bytes(audio, config.samplerate, config.channels)


def record_for_seconds(config: AudioConfig, seconds: float) -> bytes:
    if seconds <= 0:
        raise ValueError("Seconds must be > 0.")
    print(f"Recording for {seconds:.1f} seconds...")
    audio = sd.rec(
        int(seconds * config.samplerate),
        samplerate=config.samplerate,
        channels=config.channels,
        dtype=config.dtype,
        device=config.device,
    )
    sd.wait()
    return _audio_to_wav_bytes(audio, config.samplerate, config.channels)


def transcribe_wav_bytes(
    api_key: str,
    wav_bytes: bytes,
    model: str = "gpt-4o-mini-transcribe",
    language: Optional[str] = None,
) -> str:
    client = OpenAI(api_key=api_key)
    audio_file = io.BytesIO(wav_bytes)
    audio_file.name = "speech.wav"

    params = {
        "model": model,
        "file": audio_file,
    }
    if language:
        params["language"] = language

    result = client.audio.transcriptions.create(**params)
    return getattr(result, "text", None) or str(result)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenAI Whisper Speech-to-Text PoC")
    parser.add_argument("--api-key", required=True, help="OpenAI API key")
    parser.add_argument(
        "--model",
        default="gpt-4o-mini-transcribe",
        help="Transcription model",
    )
    parser.add_argument(
        "--language",
        default="ko",
        help="Optional language hint, e.g. 'ko' for Korean",
    )
    parser.add_argument("--samplerate", type=int, default=16000)
    parser.add_argument("--device", default=None, help="Input device name or index")
    parser.add_argument("--seconds", type=float, default=0.0, help="Fixed recording length")
    parser.add_argument("--list-devices", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    if args.list_devices:
        print(list_input_devices())
        return 0

    config = AudioConfig(
        samplerate=args.samplerate,
        channels=1,
        dtype="int16",
        device=args.device,
    )

    try:
        if args.seconds and args.seconds > 0:
            wav_bytes = record_for_seconds(config, args.seconds)
        else:
            wav_bytes = record_until_enter(config)
        text = transcribe_wav_bytes(
            api_key=args.api_key,
            wav_bytes=wav_bytes,
            model=args.model,
            language=args.language,
        )
        print(text)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
