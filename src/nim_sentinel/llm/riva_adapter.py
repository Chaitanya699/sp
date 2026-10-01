"""
NIM Sentinel Riva ASR/TTS Adapter

Provides gRPC-based adapters for NVIDIA Riva Speech Recognition (ASR)
and Text-to-Speech (TTS) services. These are separate from ChatNVIDIA
REST API and require a dedicated Riva NIM deployment.
"""

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path

import grpc
from riva.client import (
    ASRService,
    AudioEncoding,
    Auth,
    RecognitionConfig,
    SpeechSynthesisService,
    StreamingRecognitionConfig,
)

from nim_sentinel.core import ModelRole, ModelUnavailableError
from nim_sentinel.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RivaConfig:
    """Configuration for Riva gRPC connection."""
    uri: str = "localhost:50051"
    use_ssl: bool = False
    ssl_root_cert: str | None = None
    api_key: str | None = None
    language_code: str = "en-US"
    sample_rate_hz: int = 16000
    audio_encoding: AudioEncoding = AudioEncoding.LINEAR_PCM


class RivaASRAdapter:
    """
    Adapter for NVIDIA Riva Automatic Speech Recognition (ASR) via gRPC.

    Requires a running Riva NIM deployment with ASR models (e.g., Parakeet).
    Not available via ChatNVIDIA REST API.
    """

    def __init__(self, config: RivaConfig | None = None):
        self.config = config or RivaConfig()
        self._auth: Auth | None = None
        self._service: ASRService | None = None
        self._initialized = False

    def _initialize(self) -> None:
        """Initialize Riva ASR service connection."""
        if self._initialized:
            return

        metadata_args = None
        if self.config.api_key:
            metadata_args = [["authorization", f"Bearer {self.config.api_key}"]]

        self._auth = Auth(
            uri=self.config.uri,
            use_ssl=self.config.use_ssl,
            ssl_root_cert=self.config.ssl_root_cert,
            metadata_args=metadata_args,
        )
        self._service = ASRService(self._auth)
        self._initialized = True
        logger.info("Riva ASR adapter initialized", uri=self.config.uri)

    def transcribe_offline(
        self,
        audio_bytes: bytes,
        enable_automatic_punctuation: bool = True,
        enable_word_time_offsets: bool = False,
    ) -> str:
        """
        Transcribe audio using offline (batch) recognition.

        Args:
            audio_bytes: Raw audio data (LINEAR_PCM, 16kHz)
            enable_automatic_punctuation: Add punctuation to transcript
            enable_word_time_offsets: Include word-level timestamps

        Returns:
            Transcribed text
        """
        self._initialize()

        config = RecognitionConfig(
            encoding=self.config.audio_encoding,
            sample_rate_hertz=self.config.sample_rate_hz,
            language_code=self.config.language_code,
            enable_automatic_punctuation=enable_automatic_punctuation,
            enable_word_time_offsets=enable_word_time_offsets,
        )

        try:
            assert self._service is not None
            response = self._service.offline_recognize(audio_bytes, config)
            if response.results:
                return " ".join(
                    result.alternatives[0].transcript
                    for result in response.results
                    if result.alternatives
                )
            return ""
        except grpc.RpcError as e:
            logger.error("Riva ASR offline recognition failed", error=str(e))
            raise ModelUnavailableError(ModelRole.ASR.value, "riva-asr") from e

    async def transcribe_streaming(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        enable_automatic_punctuation: bool = True,
        interim_results: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Transcribe audio using streaming recognition.

        Args:
            audio_chunks: Async generator yielding audio chunks
            enable_automatic_punctuation: Add punctuation to transcript
            interim_results: Yield interim results

        Yields:
            Transcribed text chunks (interim or final)
        """
        self._initialize()

        config = RecognitionConfig(
            encoding=self.config.audio_encoding,
            sample_rate_hertz=self.config.sample_rate_hz,
            language_code=self.config.language_code,
            enable_automatic_punctuation=enable_automatic_punctuation,
        )
        streaming_config = StreamingRecognitionConfig(
            config=config,
            interim_results=interim_results,
        )

        # Collect all chunks first (async)
        chunks: list[bytes] = []
        async for chunk in audio_chunks:
            chunks.append(chunk)

        def chunk_generator() -> list[bytes]:
            return chunks

        try:
            # Run in thread pool since Riva client is synchronous
            loop = asyncio.get_event_loop()
            assert self._service is not None
            responses = await loop.run_in_executor(
                None,
                lambda: list(self._service.streaming_response_generator(  # type: ignore[union-attr]
                    chunk_generator(), streaming_config
                ))
            )

            for response in responses:
                for result in response.results:
                    if result.alternatives:
                        transcript = result.alternatives[0].transcript
                        if transcript:
                            yield transcript

        except grpc.RpcError as e:
            logger.error("Riva ASR streaming recognition failed", error=str(e))
            raise ModelUnavailableError(ModelRole.ASR.value, "riva-asr") from e

    def transcribe_file(
        self,
        file_path: str | Path,
        enable_automatic_punctuation: bool = True,
    ) -> str:
        """
        Transcribe audio from a WAV file.

        Args:
            file_path: Path to WAV file
            enable_automatic_punctuation: Add punctuation to transcript

        Returns:
            Transcribed text
        """
        import wave

        with wave.open(str(file_path), "rb") as wav_file:
            # Verify format
            if wav_file.getframerate() != self.config.sample_rate_hz:
                logger.warning(
                    "Sample rate mismatch",
                    expected=self.config.sample_rate_hz,
                    actual=wav_file.getframerate(),
                )
            if wav_file.getsampwidth() != 2:  # 16-bit
                logger.warning("Expected 16-bit audio, got %d-bit", wav_file.getsampwidth() * 8)

            audio_bytes = wav_file.readframes(wav_file.getnframes())

        return self.transcribe_offline(audio_bytes, enable_automatic_punctuation)


class RivaTTSAdapter:
    """
    Adapter for NVIDIA Riva Text-to-Speech (TTS) via gRPC.

    Requires a running Riva NIM deployment with TTS models (e.g., FastPitch).
    Not available via ChatNVIDIA REST API.
    """

    def __init__(self, config: RivaConfig | None = None):
        self.config = config or RivaConfig()
        self._auth: Auth | None = None
        self._service: SpeechSynthesisService | None = None
        self._initialized = False

    def _initialize(self) -> None:
        """Initialize Riva TTS service connection."""
        if self._initialized:
            return

        metadata_args = None
        if self.config.api_key:
            metadata_args = [["authorization", f"Bearer {self.config.api_key}"]]

        self._auth = Auth(
            uri=self.config.uri,
            use_ssl=self.config.use_ssl,
            ssl_root_cert=self.config.ssl_root_cert,
            metadata_args=metadata_args,
        )
        self._service = SpeechSynthesisService(self._auth)
        self._initialized = True
        logger.info("Riva TTS adapter initialized", uri=self.config.uri)

    def synthesize(
        self,
        text: str,
        voice_name: str | None = None,
        language_code: str | None = None,
        sample_rate_hz: int | None = None,
        audio_encoding: AudioEncoding | None = None,
    ) -> bytes:
        """
        Synthesize speech from text (offline/batch).

        Args:
            text: Text to synthesize
            voice_name: Voice name (e.g., "English-US-Female-1")
            language_code: Language code (default from config)
            sample_rate_hz: Output sample rate (default from config)
            audio_encoding: Output encoding (default from config)

        Returns:
            Audio bytes (LINEAR_PCM by default)
        """
        self._initialize()

        try:
            assert self._service is not None
            response = self._service.synthesize(
                text=text,
                voice_name=voice_name,
                language_code=language_code or self.config.language_code,
                encoding=audio_encoding or self.config.audio_encoding,
                sample_rate_hz=sample_rate_hz or self.config.sample_rate_hz,
            )
            return response.audio  # type: ignore[no-any-return]
        except grpc.RpcError as e:
            logger.error("Riva TTS synthesis failed", error=str(e))
            raise ModelUnavailableError(ModelRole.TTS.value, "riva-tts") from e

    async def synthesize_streaming(
        self,
        text: str | list[str],
        voice_name: str | None = None,
        language_code: str | None = None,
        sample_rate_hz: int | None = None,
        audio_encoding: AudioEncoding | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize speech with streaming output (online).

        Args:
            text: Text or list of texts to synthesize
            voice_name: Voice name
            language_code: Language code
            sample_rate_hz: Output sample rate
            audio_encoding: Output encoding

        Yields:
            Audio chunks as they become available
        """
        self._initialize()

        try:
            loop = asyncio.get_event_loop()
            assert self._service is not None
            responses = await loop.run_in_executor(
                None,
                lambda: list(self._service.synthesize_online(  # type: ignore[union-attr]
                    text=text,
                    voice_name=voice_name,
                    language_code=language_code or self.config.language_code,
                    encoding=audio_encoding or self.config.audio_encoding,
                    sample_rate_hz=sample_rate_hz or self.config.sample_rate_hz,
                ))
            )

            for response in responses:
                if response.audio:
                    yield response.audio

        except grpc.RpcError as e:
            logger.error("Riva TTS streaming synthesis failed", error=str(e))
            raise ModelUnavailableError(ModelRole.TTS.value, "riva-tts") from e

    def save_to_file(
        self,
        text: str,
        output_path: str | Path,
        voice_name: str | None = None,
        language_code: str | None = None,
        sample_rate_hz: int | None = None,
    ) -> None:
        """
        Synthesize speech and save to WAV file.

        Args:
            text: Text to synthesize
            output_path: Output WAV file path
            voice_name: Voice name
            language_code: Language code
            sample_rate_hz: Output sample rate
        """
        audio_bytes = self.synthesize(
            text=text,
            voice_name=voice_name,
            language_code=language_code,
            sample_rate_hz=sample_rate_hz,
        )

        import wave
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate_hz or self.config.sample_rate_hz)
            wav_file.writeframes(audio_bytes)

        logger.info("TTS audio saved", path=str(output_path))


def create_riva_config_from_env() -> RivaConfig:
    """Create RivaConfig from environment variables."""
    import os

    return RivaConfig(
        uri=os.getenv("RIVA_URI", "localhost:50051"),
        use_ssl=os.getenv("RIVA_USE_SSL", "false").lower() == "true",
        ssl_root_cert=os.getenv("RIVA_SSL_ROOT_CERT"),
        api_key=os.getenv("RIVA_API_KEY"),
        language_code=os.getenv("RIVA_LANGUAGE_CODE", "en-US"),
        sample_rate_hz=int(os.getenv("RIVA_SAMPLE_RATE", "16000")),
    )


# Global adapter instances (lazy initialization)
_asr_adapter: RivaASRAdapter | None = None
_tts_adapter: RivaTTSAdapter | None = None


def get_riva_asr() -> RivaASRAdapter:
    """Get global Riva ASR adapter instance."""
    global _asr_adapter
    if _asr_adapter is None:
        _asr_adapter = RivaASRAdapter(create_riva_config_from_env())
    return _asr_adapter


def get_riva_tts() -> RivaTTSAdapter:
    """Get global Riva TTS adapter instance."""
    global _tts_adapter
    if _tts_adapter is None:
        _tts_adapter = RivaTTSAdapter(create_riva_config_from_env())
    return _tts_adapter


def reset_riva_adapters() -> None:
    """Reset global Riva adapters (for testing)."""
    global _asr_adapter, _tts_adapter
    _asr_adapter = None
    _tts_adapter = None

