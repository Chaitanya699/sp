"""
Tests for Riva ASR/TTS Adapter
"""

from unittest.mock import MagicMock, patch

import pytest
from nim_sentinel.llm.riva_adapter import (
    RivaASRAdapter,
    RivaConfig,
    RivaTTSAdapter,
    create_riva_config_from_env,
    get_riva_asr,
    get_riva_tts,
    reset_riva_adapters,
)


class TestRivaConfig:
    """Tests for RivaConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RivaConfig()
        assert config.uri == "localhost:50051"
        assert config.use_ssl is False
        assert config.ssl_root_cert is None
        assert config.api_key is None
        assert config.language_code == "en-US"
        assert config.sample_rate_hz == 16000

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RivaConfig(
            uri="custom:50051",
            use_ssl=True,
            api_key="test-key",
            language_code="es-ES",
            sample_rate_hz=22050,
        )
        assert config.uri == "custom:50051"
        assert config.use_ssl is True
        assert config.api_key == "test-key"
        assert config.language_code == "es-ES"
        assert config.sample_rate_hz == 22050


class TestRivaASRAdapter:
    """Tests for RivaASRAdapter."""

    def setup_method(self):
        """Reset global adapters before each test."""
        reset_riva_adapters()

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        adapter = RivaASRAdapter()
        assert adapter.config.uri == "localhost:50051"
        assert adapter._initialized is False

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = RivaConfig(uri="test:50051", api_key="test-key")
        adapter = RivaASRAdapter(config)
        assert adapter.config.uri == "test:50051"
        assert adapter.config.api_key == "test-key"

    @patch("nim_sentinel.llm.riva_adapter.Auth")
    @patch("nim_sentinel.llm.riva_adapter.ASRService")
    def test_initialize(self, mock_asr_service, mock_auth):
        """Test adapter initialization."""
        adapter = RivaASRAdapter(RivaConfig(uri="test:50051"))
        adapter._initialize()

        mock_auth.assert_called_once_with(
            uri="test:50051",
            use_ssl=False,
            ssl_root_cert=None,
            metadata_args=None,
        )
        mock_asr_service.assert_called_once()
        assert adapter._initialized is True

    @patch("nim_sentinel.llm.riva_adapter.Auth")
    @patch("nim_sentinel.llm.riva_adapter.ASRService")
    def test_initialize_with_api_key(self, mock_asr_service, mock_auth):
        """Test adapter initialization with API key."""
        adapter = RivaASRAdapter(RivaConfig(uri="test:50051", api_key="test-key"))
        adapter._initialize()

        mock_auth.assert_called_once_with(
            uri="test:50051",
            use_ssl=False,
            ssl_root_cert=None,
            metadata_args=[["authorization", "Bearer test-key"]],
        )

    @patch("nim_sentinel.llm.riva_adapter.Auth")
    @patch("nim_sentinel.llm.riva_adapter.ASRService")
    def test_transcribe_offline_success(self, mock_asr_service, mock_auth):
        """Test successful offline transcription."""
        # Setup mock response
        mock_result = MagicMock()
        mock_result.alternatives = [MagicMock(transcript="Hello world")]
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_asr_service.return_value.offline_recognize.return_value = mock_response

        adapter = RivaASRAdapter(RivaConfig(uri="test:50051"))
        result = adapter.transcribe_offline(b"audio_data")

        assert result == "Hello world"
        mock_asr_service.return_value.offline_recognize.assert_called_once()

    @patch("nim_sentinel.llm.riva_adapter.Auth")
    @patch("nim_sentinel.llm.riva_adapter.ASRService")
    def test_transcribe_offline_empty_result(self, mock_asr_service, mock_auth):
        """Test offline transcription with empty results."""
        mock_response = MagicMock()
        mock_response.results = []
        mock_asr_service.return_value.offline_recognize.return_value = mock_response

        adapter = RivaASRAdapter(RivaConfig(uri="test:50051"))
        result = adapter.transcribe_offline(b"audio_data")

        assert result == ""

    @patch("nim_sentinel.llm.riva_adapter.Auth")
    @patch("nim_sentinel.llm.riva_adapter.ASRService")
    def test_transcribe_offline_error(self, mock_asr_service, mock_auth):
        """Test offline transcription error handling."""
        import grpc
        from nim_sentinel.core import ModelUnavailableError

        mock_asr_service.return_value.offline_recognize.side_effect = grpc.RpcError()

        adapter = RivaASRAdapter(RivaConfig(uri="test:50051"))
        with pytest.raises(ModelUnavailableError):
            adapter.transcribe_offline(b"audio_data")


class TestRivaTTSAdapter:
    """Tests for RivaTTSAdapter."""

    def setup_method(self):
        """Reset global adapters before each test."""
        reset_riva_adapters()

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        adapter = RivaTTSAdapter()
        assert adapter.config.uri == "localhost:50051"
        assert adapter._initialized is False

    @patch("nim_sentinel.llm.riva_adapter.Auth")
    @patch("nim_sentinel.llm.riva_adapter.SpeechSynthesisService")
    def test_initialize(self, mock_tts_service, mock_auth):
        """Test adapter initialization."""
        adapter = RivaTTSAdapter(RivaConfig(uri="test:50051"))
        adapter._initialize()

        mock_auth.assert_called_once_with(
            uri="test:50051",
            use_ssl=False,
            ssl_root_cert=None,
            metadata_args=None,
        )
        mock_tts_service.assert_called_once()
        assert adapter._initialized is True

    @patch("nim_sentinel.llm.riva_adapter.Auth")
    @patch("nim_sentinel.llm.riva_adapter.SpeechSynthesisService")
    def test_synthesize_success(self, mock_tts_service, mock_auth):
        """Test successful speech synthesis."""
        mock_response = MagicMock()
        mock_response.audio = b"audio_data"
        mock_tts_service.return_value.synthesize.return_value = mock_response

        adapter = RivaTTSAdapter(RivaConfig(uri="test:50051"))
        result = adapter.synthesize("Hello world")

        assert result == b"audio_data"
        mock_tts_service.return_value.synthesize.assert_called_once()

    @patch("nim_sentinel.llm.riva_adapter.Auth")
    @patch("nim_sentinel.llm.riva_adapter.SpeechSynthesisService")
    def test_synthesize_error(self, mock_tts_service, mock_auth):
        """Test speech synthesis error handling."""
        import grpc
        from nim_sentinel.core import ModelUnavailableError

        mock_tts_service.return_value.synthesize.side_effect = grpc.RpcError()

        adapter = RivaTTSAdapter(RivaConfig(uri="test:50051"))
        with pytest.raises(ModelUnavailableError):
            adapter.synthesize("Hello world")


class TestGlobalAdapters:
    """Tests for global adapter instances."""

    def setup_method(self):
        """Reset global adapters before each test."""
        reset_riva_adapters()

    def test_get_riva_asr_singleton(self):
        """Test get_riva_asr returns singleton."""
        with patch("nim_sentinel.llm.riva_adapter.create_riva_config_from_env") as mock_config:
            mock_config.return_value = RivaConfig(uri="test:50051")
            asr1 = get_riva_asr()
            asr2 = get_riva_asr()
            assert asr1 is asr2

    def test_get_riva_tts_singleton(self):
        """Test get_riva_tts returns singleton."""
        with patch("nim_sentinel.llm.riva_adapter.create_riva_config_from_env") as mock_config:
            mock_config.return_value = RivaConfig(uri="test:50051")
            tts1 = get_riva_tts()
            tts2 = get_riva_tts()
            assert tts1 is tts2

    def test_reset_riva_adapters(self):
        """Test reset_riva_adapters clears singletons."""
        with patch("nim_sentinel.llm.riva_adapter.create_riva_config_from_env") as mock_config:
            mock_config.return_value = RivaConfig(uri="test:50051")
            asr1 = get_riva_asr()
            tts1 = get_riva_tts()
            reset_riva_adapters()
            asr2 = get_riva_asr()
            tts2 = get_riva_tts()
            assert asr1 is not asr2
            assert tts1 is not tts2


class TestCreateRivaConfigFromEnv:
    """Tests for create_riva_config_from_env function."""

    @patch.dict(
        "os.environ",
        {
            "RIVA_URI": "env:50051",
            "RIVA_USE_SSL": "true",
            "RIVA_API_KEY": "env-key",
            "RIVA_LANGUAGE_CODE": "fr-FR",
            "RIVA_SAMPLE_RATE": "22050",
        },
    )
    def test_create_from_env(self):
        """Test creating config from environment variables."""
        config = create_riva_config_from_env()
        assert config.uri == "env:50051"
        assert config.use_ssl is True
        assert config.api_key == "env-key"
        assert config.language_code == "fr-FR"
        assert config.sample_rate_hz == 22050

    @patch.dict("os.environ", {}, clear=True)
    def test_create_from_env_defaults(self):
        """Test creating config with defaults when env vars not set."""
        config = create_riva_config_from_env()
        assert config.uri == "localhost:50051"
        assert config.use_ssl is False
        assert config.api_key is None
        assert config.language_code == "en-US"
        assert config.sample_rate_hz == 16000
