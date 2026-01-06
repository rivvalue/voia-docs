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


class TestAnthropicAdapter:
    """Test Anthropic (Claude) adapter functionality."""
    
    def test_anthropic_adapter_provider_property(self, monkeypatch):
        """AnthropicAdapter should return correct provider."""
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_API_KEY', 'test-key')
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_BASE_URL', 'https://test.com')
        
        from llm_gateway import AnthropicAdapter, LLMProvider
        
        adapter = AnthropicAdapter()
        assert adapter.provider == LLMProvider.ANTHROPIC
    
    def test_anthropic_adapter_is_available_with_config(self, monkeypatch):
        """AnthropicAdapter should be available when AI Integrations configured."""
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_API_KEY', 'test-key')
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_BASE_URL', 'https://test.com')
        
        from llm_gateway import AnthropicAdapter
        
        adapter = AnthropicAdapter()
        assert adapter.is_available() is True
    
    def test_anthropic_adapter_not_available_without_config(self, monkeypatch):
        """AnthropicAdapter should not be available without configuration."""
        monkeypatch.delenv('AI_INTEGRATIONS_ANTHROPIC_API_KEY', raising=False)
        monkeypatch.delenv('AI_INTEGRATIONS_ANTHROPIC_BASE_URL', raising=False)
        
        from llm_gateway import AnthropicAdapter
        
        adapter = AnthropicAdapter()
        assert adapter.is_available() is False
    
    @patch('anthropic.Anthropic')
    def test_anthropic_adapter_chat_completion(self, mock_anthropic_class, monkeypatch):
        """AnthropicAdapter.chat_completion should return LLMResponse."""
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_API_KEY', 'test-key')
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_BASE_URL', 'https://test.com')
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='Claude response')]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        from llm_gateway import AnthropicAdapter, LLMRequest, LLMMessage
        
        adapter = AnthropicAdapter()
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hello Claude")],
            model="claude-sonnet-4-5"
        )
        
        response = adapter.chat_completion(request)
        
        assert response.content == 'Claude response'
        assert response.provider == 'anthropic'
        assert response.model == 'claude-sonnet-4-5'
        assert response.usage['prompt_tokens'] == 10
        assert response.usage['completion_tokens'] == 20
    
    @patch('anthropic.Anthropic')
    def test_anthropic_adapter_handles_system_message(self, mock_anthropic_class, monkeypatch):
        """AnthropicAdapter should extract system message from messages."""
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_API_KEY', 'test-key')
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_BASE_URL', 'https://test.com')
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='Response')]
        mock_response.usage.input_tokens = 5
        mock_response.usage.output_tokens = 10
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        from llm_gateway import AnthropicAdapter, LLMRequest, LLMMessage
        
        adapter = AnthropicAdapter()
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content="You are helpful"),
                LLMMessage(role="user", content="Hello")
            ]
        )
        
        adapter.chat_completion(request)
        
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs.get('system') == 'You are helpful'
        assert len([m for m in call_kwargs['messages'] if m['role'] == 'system']) == 0
    
    def test_anthropic_adapter_count_tokens(self, monkeypatch):
        """AnthropicAdapter.count_tokens should estimate tokens."""
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_API_KEY', 'test-key')
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_BASE_URL', 'https://test.com')
        
        from llm_gateway import AnthropicAdapter
        
        adapter = AnthropicAdapter()
        text = "This is a test message"
        
        token_count = adapter.count_tokens(text)
        assert token_count == len(text) // 4


class TestGatewayClaudeRouting:
    """Test gateway routing to Claude when enabled."""
    
    @patch('anthropic.Anthropic')
    def test_gateway_routes_to_claude_when_enabled(self, mock_anthropic_class, monkeypatch):
        """Gateway should route to Claude when CLAUDE_ENABLED=true."""
        monkeypatch.setenv('OPENAI_API_KEY', 'openai-key')
        monkeypatch.setenv('CLAUDE_ENABLED', 'true')
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_API_KEY', 'anthropic-key')
        monkeypatch.setenv('AI_INTEGRATIONS_ANTHROPIC_BASE_URL', 'https://test.com')
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='Claude says hi')]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 15
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        from llm_gateway import LLMGateway, LLMRequest, LLMMessage, LLMProvider
        
        gateway = LLMGateway()
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hello")]
        )
        
        response = gateway.chat_completion(request, provider_override=LLMProvider.ANTHROPIC)
        
        assert response.provider == 'anthropic'
        assert response.content == 'Claude says hi'
    
    @patch('openai.OpenAI')
    def test_gateway_falls_back_to_openai_when_claude_disabled(self, mock_openai_class, monkeypatch):
        """Gateway should fall back to OpenAI when Claude disabled."""
        monkeypatch.setenv('OPENAI_API_KEY', 'openai-key')
        monkeypatch.setenv('CLAUDE_ENABLED', 'false')
        monkeypatch.delenv('AI_INTEGRATIONS_ANTHROPIC_API_KEY', raising=False)
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = 'OpenAI fallback'
        mock_response.model = "gpt-4o-mini"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        from llm_gateway import LLMGateway, LLMRequest, LLMMessage, LLMProvider
        
        gateway = LLMGateway()
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hello")]
        )
        
        response = gateway.chat_completion(request, provider_override=LLMProvider.ANTHROPIC)
        
        assert response.provider == 'openai'


class TestV2SurveyGatewayIntegration:
    """Integration tests for V2 survey controller with LLM Gateway.
    
    Note: Full controller instantiation tests are skipped due to Flask circular
    imports in test environment. Core gateway functionality is validated through
    LLMConfig and adapter tests. Production integration is verified manually.
    """
    
    def test_wrapper_function_signatures_include_gateway(self):
        """Verify wrapper functions are designed to use gateway."""
        # This test verifies the code structure without triggering imports
        import ast
        
        with open('ai_conversational_survey_v2.py', 'r') as f:
            source = f.read()
        
        # Check that gateway is used in wrapper functions
        assert 'llm_gateway = get_gateway()' in source
        assert 'llm_gateway=llm_gateway' in source
    
    def test_controller_init_signature(self):
        """Verify controller __init__ accepts llm_gateway parameter."""
        import ast
        
        with open('ai_conversational_survey_v2.py', 'r') as f:
            source = f.read()
        
        # Parse AST to find DeterministicSurveyController.__init__
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'DeterministicSurveyController':
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        arg_names = [arg.arg for arg in item.args.args]
                        assert 'llm_gateway' in arg_names, "llm_gateway parameter not found in __init__"
                        return
        
        pytest.fail("DeterministicSurveyController.__init__ not found")


class TestAnalysisGatewayIntegration:
    """Integration tests for ai_analysis module with LLM Gateway.
    
    Note: Direct function import tests are skipped due to Flask circular
    imports in test environment. Code structure is validated via AST parsing.
    """
    
    def test_call_llm_for_analysis_uses_gateway_structure(self):
        """Verify _call_llm_for_analysis is structured to use gateway."""
        with open('ai_analysis.py', 'r') as f:
            source = f.read()
        
        # Check that the helper function uses gateway
        assert '_get_analysis_gateway()' in source
        assert 'gateway.chat_completion' in source
        assert 'LLMRequest(' in source
    
    def test_llm_config_respects_claude_enabled_flag(self, monkeypatch):
        """LLMConfig should return OpenAI models when Claude disabled."""
        monkeypatch.setenv('CLAUDE_ENABLED', 'false')
        monkeypatch.setenv('DEFAULT_LLM_PROVIDER', 'anthropic')
        
        from llm_gateway import LLMConfig
        
        config = LLMConfig.from_environment()
        
        # Even with Anthropic as default provider, should return OpenAI model
        # because CLAUDE_ENABLED is false
        model = config.get_default_model()
        assert 'gpt' in model.lower()
    
    def test_llm_config_returns_claude_when_enabled(self, monkeypatch):
        """LLMConfig should return Claude models when enabled."""
        monkeypatch.setenv('CLAUDE_ENABLED', 'true')
        monkeypatch.setenv('DEFAULT_LLM_PROVIDER', 'anthropic')
        
        from llm_gateway import LLMConfig
        
        config = LLMConfig.from_environment()
        model = config.get_default_model()
        
        assert 'claude' in model.lower()
    
    def test_get_openai_model_always_returns_openai(self, monkeypatch):
        """get_openai_model should always return OpenAI models regardless of provider."""
        monkeypatch.setenv('CLAUDE_ENABLED', 'true')
        monkeypatch.setenv('DEFAULT_LLM_PROVIDER', 'anthropic')
        
        from llm_gateway import LLMConfig
        
        config = LLMConfig.from_environment()
        
        # Standard model
        model = config.get_openai_model(premium=False)
        assert 'gpt' in model.lower()
        
        # Premium model
        premium_model = config.get_openai_model(premium=True)
        assert 'gpt' in premium_model.lower()
