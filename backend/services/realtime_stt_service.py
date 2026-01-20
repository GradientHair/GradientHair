import asyncio
import json
import logging
import os
import time
from enum import Enum
from typing import Callable, Optional

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
    InvalidStatusCode,
    WebSocketException,
)

# Configure module logger
logger = logging.getLogger(__name__)

# OpenAI Realtime API endpoint with model parameter
REALTIME_API_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"

# Connection configuration
DEFAULT_CONNECT_TIMEOUT = 30.0  # seconds
DEFAULT_PING_INTERVAL = 20.0  # seconds
DEFAULT_PING_TIMEOUT = 10.0  # seconds
MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_DELAY_BASE = 1.0  # seconds (exponential backoff base)


class ConnectionState(Enum):
    """Connection state for the STT service."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class STTError(Exception):
    """Base exception for STT service errors."""
    pass


class STTConnectionError(STTError):
    """Raised when connection to the Realtime API fails."""
    pass


class STTConfigurationError(STTError):
    """Raised when the service is misconfigured."""
    pass


class RealtimeSTTService:
    """
    Production-ready service for OpenAI Realtime API speech-to-text.

    Features:
    - Automatic reconnection with exponential backoff
    - Proper error handling and logging
    - Graceful cleanup on disconnect
    - Connection state tracking
    - Thread-safe operations
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = MAX_RECONNECT_ATTEMPTS,
    ):
        """
        Initialize the Realtime STT service.

        Args:
            api_key: OpenAI API key. If not provided, reads from OPENAI_API_KEY env var.
            auto_reconnect: Whether to automatically reconnect on connection loss.
            max_reconnect_attempts: Maximum number of reconnection attempts.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._state = ConnectionState.DISCONNECTED
        self._reconnect_count = 0
        self._should_reconnect = False
        self._lock = asyncio.Lock()
        self._last_speech_end_at: float | None = None
        self._response_transcripts: dict[str, str] = {}
        self._partial_transcripts: dict[str, str] = {}
        self._callback_semaphore = asyncio.Semaphore(
            int(os.getenv("REALTIME_CALLBACK_CONCURRENCY", "4"))
        )

        # Callbacks
        self._on_transcript: Optional[Callable] = None
        self._on_partial_transcript: Optional[Callable] = None
        self._on_speech_end: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        self._on_connection_state_change: Optional[Callable] = None

    @property
    def state(self) -> ConnectionState:
        """Get the current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if the service is currently connected."""
        return self._state == ConnectionState.CONNECTED and self._ws is not None

    def _set_state(self, new_state: ConnectionState) -> None:
        """Update connection state and notify callback if registered."""
        old_state = self._state
        self._state = new_state
        logger.debug(f"Connection state changed: {old_state.value} -> {new_state.value}")

        if self._on_connection_state_change:
            try:
                # Handle both sync and async callbacks
                result = self._on_connection_state_change(old_state, new_state)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.error(f"Error in connection state change callback: {e}")

    def _validate_configuration(self) -> None:
        """Validate service configuration before connecting."""
        if not self.api_key:
            raise STTConfigurationError(
                "OpenAI API key not configured. Set OPENAI_API_KEY environment variable "
                "or pass api_key to the constructor."
            )

    async def connect(
        self,
        on_transcript: Callable,
        on_speech_end: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_connection_state_change: Optional[Callable] = None,
        on_partial_transcript: Optional[Callable] = None,
    ) -> None:
        """
        Connect to the OpenAI Realtime API.

        Args:
            on_transcript: Async callback called with transcript text when speech is recognized.
            on_speech_end: Optional async callback called when speech ends (VAD detected silence).
            on_error: Optional async callback called when an error occurs.
            on_connection_state_change: Optional callback for connection state changes.
            on_partial_transcript: Optional async callback called with partial transcript updates.

        Raises:
            STTConfigurationError: If API key is not configured.
            STTConnectionError: If connection to the API fails.
        """
        self._validate_configuration()

        async with self._lock:
            if self._state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
                logger.warning("Already connected or connecting, ignoring connect request")
                return

            self._on_transcript = on_transcript
            self._on_partial_transcript = on_partial_transcript
            self._on_speech_end = on_speech_end
            self._on_error = on_error
            self._on_connection_state_change = on_connection_state_change
            self._should_reconnect = self.auto_reconnect
            self._reconnect_count = 0

            await self._establish_connection()

    async def _establish_connection(self) -> None:
        """Establish WebSocket connection to the Realtime API."""
        self._set_state(ConnectionState.CONNECTING)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        try:
            logger.info(f"Connecting to OpenAI Realtime API...")

            self._ws = await asyncio.wait_for(
                websockets.connect(
                    REALTIME_API_URL,
                    additional_headers=headers,
                    ping_interval=DEFAULT_PING_INTERVAL,
                    ping_timeout=DEFAULT_PING_TIMEOUT,
                ),
                timeout=DEFAULT_CONNECT_TIMEOUT,
            )

            logger.info("WebSocket connection established, configuring session...")

            # Configure the session for STT
            vad_threshold = float(os.getenv("REALTIME_VAD_THRESHOLD", "0.7"))
            vad_prefix_ms = int(os.getenv("REALTIME_VAD_PREFIX_MS", "300"))
            vad_silence_ms = int(os.getenv("REALTIME_VAD_SILENCE_MS", "1200"))
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "input_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": os.getenv("REALTIME_TRANSCRIBE_MODEL", "gpt-4o-transcribe"),
                        "language": os.getenv("REALTIME_TRANSCRIBE_LANGUAGE", "ko"),
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": vad_threshold,
                        "prefix_padding_ms": vad_prefix_ms,
                        "silence_duration_ms": vad_silence_ms,
                        "create_response": False,
                        "interrupt_response": False,
                    },
                },
            }

            await self._ws.send(json.dumps(session_config))
            logger.debug("Session configuration sent")

            self._set_state(ConnectionState.CONNECTED)
            self._reconnect_count = 0

            # Start the receive loop
            self._receive_task = asyncio.create_task(
                self._receive_loop(),
                name="realtime_stt_receive_loop"
            )

            logger.info("Successfully connected to OpenAI Realtime API")

        except asyncio.TimeoutError as e:
            self._set_state(ConnectionState.FAILED)
            error_msg = f"Connection timeout after {DEFAULT_CONNECT_TIMEOUT}s"
            logger.error(error_msg)
            await self._handle_error(STTConnectionError(error_msg))
            raise STTConnectionError(error_msg) from e

        except InvalidStatusCode as e:
            self._set_state(ConnectionState.FAILED)
            error_msg = f"API rejected connection with status {e.status_code}"
            if e.status_code == 401:
                error_msg = "Invalid API key or unauthorized access"
            elif e.status_code == 429:
                error_msg = "Rate limited - too many requests"
            logger.error(error_msg)
            await self._handle_error(STTConnectionError(error_msg))
            raise STTConnectionError(error_msg) from e

        except WebSocketException as e:
            self._set_state(ConnectionState.FAILED)
            error_msg = f"WebSocket error: {e}"
            logger.error(error_msg)
            await self._handle_error(STTConnectionError(error_msg))
            raise STTConnectionError(error_msg) from e

        except Exception as e:
            self._set_state(ConnectionState.FAILED)
            error_msg = f"Unexpected error during connection: {e}"
            logger.error(error_msg, exc_info=True)
            await self._handle_error(STTConnectionError(error_msg))
            raise STTConnectionError(error_msg) from e

    async def _receive_loop(self) -> None:
        """Main loop for receiving and processing messages from the API."""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse message as JSON: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
                    await self._handle_error(e)

        except ConnectionClosedOK:
            logger.info("Connection closed normally")
            self._set_state(ConnectionState.DISCONNECTED)

        except ConnectionClosedError as e:
            logger.warning(f"Connection closed with error: code={e.code}, reason={e.reason}")
            await self._handle_connection_loss()

        except ConnectionClosed as e:
            logger.warning(f"Connection closed: {e}")
            await self._handle_connection_loss()

        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
            raise

        except Exception as e:
            logger.error(f"Unexpected error in receive loop: {e}", exc_info=True)
            await self._handle_error(e)
            await self._handle_connection_loss()

    async def _handle_message(self, data: dict) -> None:
        """Process a message received from the API."""
        event_type = data.get("type", "")

        # Log ALL events for debugging
        if "error" in event_type or "failed" in event_type:
            logger.error(f"OpenAI Event: {event_type} | FULL Data: {json.dumps(data, ensure_ascii=False)}")
        else:
            logger.info(f"OpenAI Event: {event_type} | Data: {str(data)[:200]}")

        if event_type == "error":
            error_info = data.get("error", {})
            error_msg = error_info.get("message", "Unknown API error")
            error_code = error_info.get("code", "unknown")
            logger.error(f"API error [{error_code}]: {error_msg}")
            await self._handle_error(STTError(f"API error [{error_code}]: {error_msg}"))
            return

        if event_type == "session.created":
            logger.info("Session created successfully")
            return

        if event_type == "session.updated":
            logger.debug("Session configuration updated")
            return

        if event_type == "response.audio_transcript.delta":
            key = data.get("response_id") or data.get("item_id") or "unknown"
            delta = data.get("delta") or data.get("text") or data.get("content") or ""
            if delta:
                self._response_transcripts[key] = self._response_transcripts.get(key, "") + delta
                if self._on_partial_transcript:
                    asyncio.create_task(
                        self._run_callback(self._on_partial_transcript, key, self._response_transcripts[key])
                    )
            return

        if event_type == "response.audio_transcript.done":
            key = data.get("response_id") or data.get("item_id") or "unknown"
            transcript = data.get("transcript") or data.get("text") or self._response_transcripts.pop(key, "")
            transcript = (transcript or "").strip()
            logger.info(f"Transcription completed: '{transcript}'")
            if transcript and self._on_transcript:
                latency_ms = None
                if self._last_speech_end_at is not None:
                    latency_ms = max(0.0, (time.perf_counter() - self._last_speech_end_at) * 1000)
                    self._last_speech_end_at = None
                asyncio.create_task(self._run_callback(self._on_transcript, transcript, latency_ms, key))
            return

        if event_type == "conversation.item.input_audio_transcription.completed":
            transcript = data.get("transcript", "").strip()
            item_id = data.get("item_id")
            logger.info(f"Transcription completed: '{transcript}'")
            if transcript and self._on_transcript:
                latency_ms = None
                if self._last_speech_end_at is not None:
                    latency_ms = max(0.0, (time.perf_counter() - self._last_speech_end_at) * 1000)
                    self._last_speech_end_at = None
                asyncio.create_task(self._run_callback(self._on_transcript, transcript, latency_ms, item_id))
            return

        if event_type == "conversation.item.input_audio_transcription.delta":
            delta = data.get("delta", "")
            item_id = data.get("item_id")
            if delta and item_id:
                self._partial_transcripts[item_id] = self._partial_transcripts.get(item_id, "") + delta
                if self._on_partial_transcript:
                    asyncio.create_task(
                        self._run_callback(self._on_partial_transcript, item_id, self._partial_transcripts[item_id])
                    )
            return

        if event_type == "conversation.item.input_audio_transcription.failed":
            error_info = data.get("error", {})
            logger.error(f"=== TRANSCRIPTION FAILED ===")
            logger.error(f"Error Type: {error_info.get('type', 'unknown')}")
            logger.error(f"Error Code: {error_info.get('code', 'unknown')}")
            logger.error(f"Error Message: {error_info.get('message', 'unknown')}")
            logger.error(f"Full Error Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return

        if event_type == "input_audio_buffer.speech_started":
            logger.debug("Speech started")
            return

        if event_type == "input_audio_buffer.speech_stopped":
            logger.debug("Speech stopped")
            self._last_speech_end_at = time.perf_counter()
            if self._on_speech_end:
                asyncio.create_task(self._run_callback(self._on_speech_end))
            return

        if event_type == "input_audio_buffer.committed":
            logger.debug("Audio buffer committed")
            return

        # Log unhandled event types at debug level
        logger.debug(f"Unhandled event type: {event_type}")

    async def _run_callback(self, callback: Callable, *args) -> None:
        async with self._callback_semaphore:
            try:
                await callback(*args)
            except Exception as e:
                logger.error(f"Error in callback: {e}", exc_info=True)

    async def _handle_error(self, error: Exception) -> None:
        """Handle an error by notifying the callback if registered."""
        if self._on_error:
            try:
                await self._on_error(error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}", exc_info=True)

    async def _handle_connection_loss(self) -> None:
        """Handle unexpected connection loss with optional reconnection."""
        if not self._should_reconnect:
            self._set_state(ConnectionState.DISCONNECTED)
            return

        if self._reconnect_count >= self.max_reconnect_attempts:
            logger.error(
                f"Max reconnection attempts ({self.max_reconnect_attempts}) reached, giving up"
            )
            self._set_state(ConnectionState.FAILED)
            await self._handle_error(
                STTConnectionError("Connection lost and max reconnection attempts exceeded")
            )
            return

        self._reconnect_count += 1
        delay = RECONNECT_DELAY_BASE * (2 ** (self._reconnect_count - 1))  # Exponential backoff

        logger.info(
            f"Attempting reconnection {self._reconnect_count}/{self.max_reconnect_attempts} "
            f"in {delay:.1f}s..."
        )

        self._set_state(ConnectionState.RECONNECTING)

        await asyncio.sleep(delay)

        try:
            await self._establish_connection()
            logger.info("Reconnection successful")
        except STTConnectionError as e:
            logger.warning(f"Reconnection attempt {self._reconnect_count} failed: {e}")
            # The _establish_connection method will call _handle_connection_loss again
            # via the receive loop if needed

    async def send_audio(self, audio_base64: str) -> bool:
        """
        Send audio data to the Realtime API.

        Args:
            audio_base64: Base64-encoded PCM16 audio data.

        Returns:
            True if audio was sent successfully, False otherwise.
        """
        if not self.is_connected:
            logger.warning("Cannot send audio: not connected")
            return False

        if not audio_base64:
            logger.warning("Cannot send empty audio data")
            return False

        try:
            await self._ws.send(
                json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64,
                })
            )
            return True
        except ConnectionClosed:
            logger.warning("Cannot send audio: connection closed")
            return False
        except Exception as e:
            logger.error(f"Error sending audio: {e}", exc_info=True)
            return False

    async def commit_audio(self) -> bool:
        """
        Commit the current audio buffer, triggering transcription.

        Returns:
            True if commit was sent successfully, False otherwise.
        """
        if not self.is_connected:
            logger.warning("Cannot commit audio: not connected")
            return False

        try:
            await self._ws.send(
                json.dumps({"type": "input_audio_buffer.commit"})
            )
            return True
        except ConnectionClosed:
            logger.warning("Cannot commit audio: connection closed")
            return False
        except Exception as e:
            logger.error(f"Error committing audio: {e}", exc_info=True)
            return False

    async def clear_audio_buffer(self) -> bool:
        """
        Clear the current audio buffer.

        Returns:
            True if clear was sent successfully, False otherwise.
        """
        if not self.is_connected:
            logger.warning("Cannot clear audio buffer: not connected")
            return False

        try:
            await self._ws.send(
                json.dumps({"type": "input_audio_buffer.clear"})
            )
            return True
        except ConnectionClosed:
            logger.warning("Cannot clear audio buffer: connection closed")
            return False
        except Exception as e:
            logger.error(f"Error clearing audio buffer: {e}", exc_info=True)
            return False

    async def disconnect(self) -> None:
        """
        Disconnect from the Realtime API and clean up resources.

        This method is safe to call multiple times.
        """
        async with self._lock:
            self._should_reconnect = False  # Prevent reconnection attempts

            # Cancel the receive task
            if self._receive_task and not self._receive_task.done():
                logger.debug("Cancelling receive loop task")
                self._receive_task.cancel()
                try:
                    await asyncio.wait_for(self._receive_task, timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("Receive task did not complete within timeout")
                except asyncio.CancelledError:
                    pass  # Expected
                except Exception as e:
                    logger.error(f"Error waiting for receive task: {e}")
                self._receive_task = None

            # Close the WebSocket connection
            if self._ws:
                logger.debug("Closing WebSocket connection")
                try:
                    await asyncio.wait_for(self._ws.close(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("WebSocket close did not complete within timeout")
                except Exception as e:
                    logger.error(f"Error closing WebSocket: {e}")
                self._ws = None

            self._set_state(ConnectionState.DISCONNECTED)
            logger.info("Disconnected from OpenAI Realtime API")

    async def __aenter__(self) -> "RealtimeSTTService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - ensures cleanup."""
        await self.disconnect()
