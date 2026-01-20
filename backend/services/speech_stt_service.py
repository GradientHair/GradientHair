import asyncio
import base64
import io
import logging
import os
import wave
from dataclasses import dataclass
from typing import Callable, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class DiarizedSegment:
    speaker: str
    text: str
    start: float | None = None
    end: float | None = None


class SpeechSTTService:
    """Chunked Speech-to-Text using the Audio Transcriptions API."""

    def __init__(
        self,
        sample_rate: int = 24000,
        chunk_seconds: float = 5.0,
        language: str | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds
        self.language = language or os.getenv("AUDIO_TRANSCRIBE_LANGUAGE", "ko")
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.model = os.getenv("AUDIO_TRANSCRIBE_MODEL", "gpt-4o-transcribe-diarize")
        self.response_format = os.getenv("AUDIO_TRANSCRIBE_FORMAT", "diarized_json")
        self.chunking_strategy = os.getenv("AUDIO_TRANSCRIBE_CHUNKING", "auto")

        self._buffer = bytearray()
        self._lock = asyncio.Lock()
        self._closed = False
        self._transcribe_task: Optional[asyncio.Task] = None
        self._on_segments: Optional[Callable[[list[DiarizedSegment]], asyncio.Future]] = None
        self._on_error: Optional[Callable[[Exception], asyncio.Future]] = None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    async def ingest_audio(self, audio_base64: str) -> None:
        if not self.enabled or self._closed:
            return

        try:
            data = base64.b64decode(audio_base64)
        except Exception as e:
            logger.warning(f"Failed to decode audio chunk: {e}")
            return

        async with self._lock:
            self._buffer.extend(data)
            if self._buffer_size_seconds() >= self.chunk_seconds:
                self._schedule_transcription_locked()

    async def flush(self) -> None:
        if not self.enabled or self._closed:
            return
        async with self._lock:
            if self._buffer:
                self._schedule_transcription_locked()
        if self._transcribe_task:
            await self._transcribe_task

    async def close(self) -> None:
        self._closed = True
        await self.flush()

    def _buffer_size_seconds(self) -> float:
        # 16-bit PCM mono: 2 bytes per sample
        return len(self._buffer) / (self.sample_rate * 2)

    def _schedule_transcription_locked(self) -> None:
        if self._transcribe_task and not self._transcribe_task.done():
            return
        pcm = bytes(self._buffer)
        self._buffer.clear()
        self._transcribe_task = asyncio.create_task(self._transcribe_pcm(pcm))

    async def _transcribe_pcm(self, pcm: bytes) -> None:
        if not pcm or not self.client:
            return

        try:
            wav_bytes = self._pcm_to_wav_bytes(pcm)
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"

            transcription = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                response_format=self.response_format,
                language=self.language,
                chunking_strategy=self.chunking_strategy,
            )

            segments = self._parse_diarized_response(transcription)
            if self._on_segments:
                await self._on_segments(segments)
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}", exc_info=True)
            if self._on_error:
                await self._on_error(e)

    def _pcm_to_wav_bytes(self, pcm: bytes) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()

    def _parse_diarized_response(self, transcription) -> list[DiarizedSegment]:
        segments = []
        payload = getattr(transcription, "segments", None) or getattr(transcription, "data", None)
        if isinstance(payload, dict):
            payload = payload.get("segments")
        if not payload:
            text = getattr(transcription, "text", None) or ""
            if text.strip():
                segments.append(DiarizedSegment(speaker="Speaker 1", text=text.strip()))
            return segments

        for seg in payload:
            speaker = seg.get("speaker") or seg.get("speaker_label") or "Speaker"
            text = seg.get("text") or ""
            if not text.strip():
                continue
            segments.append(
                DiarizedSegment(
                    speaker=str(speaker),
                    text=text.strip(),
                    start=seg.get("start"),
                    end=seg.get("end"),
                )
            )
        return segments

    def set_handlers(
        self,
        on_segments: Callable[[list[DiarizedSegment]], asyncio.Future],
        on_error: Optional[Callable[[Exception], asyncio.Future]] = None,
    ) -> None:
        self._on_segments = on_segments
        self._on_error = on_error
