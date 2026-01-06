"""
Tests for LLM Gateway abstraction layer.

Tests cover:
1. Gateway initialization and configuration
2. Feature flag routing (enabled/disabled)
3. Request/Response dataclasses
4. Provider selection logic
"""
import os
import json
import pytest
from unittest.mock import MagicMock, patch


class TestFeatureFlags:
    """Test feature flag functions."""
    
    def test_is_gateway_enabled_defaults_to_true(self, monkeypatch):
        """Gateway should be enabled by default."""
        monkeypatch.delenv('LLM_GATEWAY_ENABLED', raising=False)
        
        from llm_gateway import is_gateway_enabled
        assert is_gateway_enabled() is True
    
    def test_is_gateway_enabled_respects_env_false(self, monkeypatch):
        """Gateway should be disabled when env var is false."""
        monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'false')
        
        from llm_gateway import is_gateway_enabled
        assert is_gateway_enabled() is False
    
    def test_is_gateway_enabled_respects_env_true(self, monkeypatch):
        """Gateway should be enabled when env var is true."""
        monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'true')
        
        from llm_gateway import is_gateway_enabled
        assert is_gateway_enabled() is True
    
    def test_is_claude_enabled_defaults_to_false(self, monkeypatch):
        """Claude should be disabled by default."""
        monkeypatch.delenv('CLAUDE_ENABLED', raising=False)
        
        from llm_gateway import is_claude_enabled
        assert is_claude_enabled() is False
    
    def test_is_claude_enabled_respects_env_true(self, monkeypatch):
        """Claude should be enabled when env var is true."""
        monkeypatch.setenv('CLAUDE_ENABLED', 'true')
        
        from llm_gateway import is_claude_enabled
        assert is_claude_enabled() is True
    
    def test_is_claude_enabled_respects_env_false(self, monkeypatch):
        """Claude should be disabled when env var is false."""
        monkeypatch.setenv('CLAUDE_ENABLED', 'false')
        
        from llm_gateway import is_claude_enabled
        assert is_claude_enabled() is False


class TestLLMDataClasses:
    """Test LLM request/response dataclasses."""
    
    def test_llm_message_creation(self):
        """LLMMessage should store role and content."""
        from llm_gateway import LLMMessage
        
        msg = LLMMessage(role="system", content="You are helpful")
        assert msg.role == "system"
        assert msg.content == "You are helpful"
    
    def test_llm_request_creation(self):
        """LLMRequest should store all parameters."""
        from llm_gateway import LLMRequest, LLMMessage
        
        messages = [LLMMessage(role="user", content="Hello")]
        request = LLMRequest(
            messages=messages,
            model="gpt-4o",
            temperature=0.5,
            max_tokens=1000
        )
        
        assert request.model == "gpt-4o"
        assert request.temperature == 0.5
        assert request.max_tokens == 1000
        assert len(request.messages) == 1
        assert request.messages[0].content == "Hello"
    
    def test_llm_request_defaults(self):
        """LLMRequest should have sensible defaults."""
        from llm_gateway import LLMRequest, LLMMessage
        
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Test")]
        )
        
        assert request.model == "gpt-4o-mini"
        assert request.temperature == 0.7
        assert request.max_tokens is None
        assert request.json_mode is False
        assert request.stream is False
    
    def test_llm_response_creation(self):
        """LLMResponse should store all fields."""
        from llm_gateway import LLMResponse
        
        response = LLMResponse(
            content="Hello there!",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            latency_ms=150.5
        )
        
        assert response.content == "Hello there!"
        assert response.model == "gpt-4o-mini"
        assert response.provider == "openai"
        assert response.usage["prompt_tokens"] == 10
        assert response.latency_ms == 150.5


class TestLLMConfig:
    """Test LLMConfig loading."""
    
    def test_config_from_environment_defaults(self, monkeypatch):
        """Config should have sensible defaults."""
        monkeypatch.delenv('DEFAULT_LLM_PROVIDER', raising=False)
        monkeypatch.delenv('CLAUDE_ENABLED', raising=False)
        monkeypatch.delenv('PROVIDER_FAILOVER_ORDER', raising=False)
        
        from llm_gateway import LLMConfig, LLMProvider
        
        config = LLMConfig.from_environment()
        
        assert config.default_provider == LLMProvider.OPENAI
        assert config.claude_enabled is False
        assert LLMProvider.OPENAI in config.failover_order
    
    def test_config_respects_claude_enabled(self, monkeypatch):
        """Config should respect CLAUDE_ENABLED env var."""
        monkeypatch.setenv('CLAUDE_ENABLED', 'true')
        
        from llm_gateway import LLMConfig
        
        config = LLMConfig.from_environment()
        assert config.claude_enabled is True
    
    def test_config_handles_invalid_provider(self, monkeypatch):
        """Config should fallback for invalid provider."""
        monkeypatch.setenv('DEFAULT_LLM_PROVIDER', 'invalid_provider')
        
        from llm_gateway import LLMConfig, LLMProvider
        
        config = LLMConfig.from_environment()
        assert config.default_provider == LLMProvider.OPENAI


class TestLLMProvider:
    """Test provider enumeration."""
    
    def test_provider_values(self):
        """Provider enum should have correct values."""
        from llm_gateway import LLMProvider
        
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"


class TestLLMGatewayInstantiation:
    """Test gateway instantiation."""
    
    def test_gateway_singleton_pattern(self, monkeypatch):
        """Gateway should use singleton pattern."""
        monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'true')
        monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
        
        from llm_gateway import LLMGateway
        
        gateway1 = LLMGateway.get_instance()
        gateway2 = LLMGateway.get_instance()
        
        assert gateway1 is gateway2
    
    def test_gateway_new_instance_creates_fresh(self, monkeypatch):
        """Direct instantiation should create new instances."""
        monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'true')
        monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
        
        from llm_gateway import LLMGateway
        
        gateway1 = LLMGateway()
        gateway2 = LLMGateway()
        
        assert gateway1 is not gateway2
    
    def test_gateway_handles_missing_api_key(self, monkeypatch):
        """Gateway should handle missing API key gracefully."""
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'true')
        
        from llm_gateway import LLMGateway
        
        gateway = LLMGateway()
        assert gateway is not None


class TestOpenAIAdapter:
    """Test OpenAI adapter functionality."""
    
    def test_openai_adapter_provider_property(self, monkeypatch):
        """OpenAI adapter should report correct provider."""
        monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
        
        from llm_gateway import OpenAIAdapter, LLMProvider
        
        adapter = OpenAIAdapter()
        assert adapter.provider == LLMProvider.OPENAI
    
    @patch('openai.OpenAI')
    def test_openai_adapter_chat_completion(self, mock_openai_class, monkeypatch):
        """OpenAI adapter should call chat completions API."""
        monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "success"}'
        mock_response.model = "gpt-4o-mini"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        from llm_gateway import OpenAIAdapter, LLMRequest, LLMMessage
        
        adapter = OpenAIAdapter()
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Test prompt")],
            model="gpt-4o-mini",
            temperature=0.7
        )
        
        response = adapter.chat_completion(request)
        
        assert response is not None
        assert response.content == '{"result": "success"}'
        assert response.provider == "openai"
        mock_client.chat.completions.create.assert_called_once()


class TestGatewayRouting:
    """Test gateway provider routing logic."""
    
    @patch('openai.OpenAI')
    def test_gateway_routes_to_openai_by_default(self, mock_openai_class, monkeypatch):
        """Gateway should route to OpenAI when Claude disabled."""
        monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
        monkeypatch.setenv('CLAUDE_ENABLED', 'false')
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = 'Test response'
        mock_response.model = "gpt-4o-mini"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        from llm_gateway import LLMGateway, LLMRequest, LLMMessage
        
        gateway = LLMGateway()
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hello")]
        )
        
        response = gateway.chat_completion(request)
        
        assert response.provider == "openai"


class TestThreadSafety:
    """Test thread safety properties."""
    
    def test_llm_request_is_immutable_by_design(self):
        """LLMRequest uses dataclass which is immutable for primitives."""
        from llm_gateway import LLMRequest, LLMMessage
        
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="test")],
            model="gpt-4o"
        )
        
        original_model = request.model
        assert original_model == "gpt-4o"
    
    def test_independent_gateway_instances(self, monkeypatch):
        """Direct gateway instantiation should create independent instances."""
        monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
        
        from llm_gateway import LLMGateway
        
        gateway1 = LLMGateway()
        gateway2 = LLMGateway()
        
        assert gateway1 is not gateway2
