"""
LLM Gateway: Provider-agnostic abstraction layer for AI/LLM operations.

This module provides a unified interface for LLM providers (OpenAI, Anthropic, etc.)
with feature-flag protection, structured logging, and backward compatibility.

Architecture:
    LLMGateway (factory/router)
        ├── OpenAIAdapter (default, production-proven)
        └── AnthropicAdapter (future, behind feature flag)

Configuration precedence:
    Campaign → Business Account → Environment → Default (OpenAI)

Feature Flags:
    LLM_GATEWAY_ENABLED: Use gateway vs direct calls (default: true)
    CLAUDE_ENABLED: Allow Claude provider selection (default: false)
"""

import os
import json
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Iterator
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMModel(Enum):
    """Supported models with provider mapping."""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    CLAUDE_SONNET = "claude-sonnet-4-5"
    CLAUDE_HAIKU = "claude-haiku-4-5"
    CLAUDE_HAIKU_35 = "claude-3-5-haiku-latest"
    CLAUDE_OPUS = "claude-opus-4-5"


VALID_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": [
        "claude-sonnet-4-5", "claude-3-5-sonnet-latest",
        "claude-haiku-4-5", "claude-3-5-haiku-latest",
        "claude-opus-4-5", "claude-3-opus-latest"
    ]
}


@dataclass
class LLMMessage:
    """Standardized message format for LLM requests."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMRequest:
    """Standardized request format for LLM operations."""
    messages: List[LLMMessage]
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    json_mode: bool = False
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Standardized response format from LLM operations."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    raw_response: Any = None


@dataclass
class LLMConfig:
    """
    Configuration for LLM Gateway.
    
    Environment Variables:
        DEFAULT_LLM_PROVIDER: Provider to use (openai, anthropic). Default: openai
        CLAUDE_ENABLED: Allow Claude provider selection. Default: false
        DEFAULT_OPENAI_MODEL: Default OpenAI model. Default: gpt-4o-mini
        DEFAULT_CLAUDE_MODEL: Default Claude model. Default: claude-sonnet-4-5
        DEFAULT_OPENAI_PREMIUM_MODEL: Premium OpenAI model for escalations. Default: gpt-4o
        DEFAULT_CLAUDE_PREMIUM_MODEL: Premium Claude model for escalations. Default: claude-opus-4-5
        PROVIDER_FAILOVER_ORDER: Comma-separated failover order. Default: openai
    """
    default_provider: LLMProvider = LLMProvider.OPENAI
    claude_enabled: bool = False
    failover_order: List[LLMProvider] = field(default_factory=lambda: [LLMProvider.OPENAI])
    model_mapping: Dict[str, str] = field(default_factory=dict)
    default_openai_model: str = "gpt-4o-mini"
    default_claude_model: str = "claude-sonnet-4-5"
    default_openai_premium_model: str = "gpt-4o"
    default_claude_premium_model: str = "claude-opus-4-5"
    
    @classmethod
    def from_environment(cls) -> 'LLMConfig':
        """Load configuration from environment variables."""
        default_provider_str = os.environ.get('DEFAULT_LLM_PROVIDER', 'openai').lower()
        claude_enabled = os.environ.get('CLAUDE_ENABLED', 'false').lower() == 'true'
        
        try:
            default_provider = LLMProvider(default_provider_str)
        except ValueError:
            logger.warning(f"Invalid DEFAULT_LLM_PROVIDER '{default_provider_str}', using openai")
            default_provider = LLMProvider.OPENAI
        
        failover_str = os.environ.get('PROVIDER_FAILOVER_ORDER', 'openai')
        failover_order = []
        for p in failover_str.split(','):
            try:
                failover_order.append(LLMProvider(p.strip().lower()))
            except ValueError:
                continue
        if not failover_order:
            failover_order = [LLMProvider.OPENAI]
        
        default_openai_model = os.environ.get('DEFAULT_OPENAI_MODEL', 'gpt-4o-mini')
        default_claude_model = os.environ.get('DEFAULT_CLAUDE_MODEL', 'claude-sonnet-4-5')
        default_openai_premium_model = os.environ.get('DEFAULT_OPENAI_PREMIUM_MODEL', 'gpt-4o')
        default_claude_premium_model = os.environ.get('DEFAULT_CLAUDE_PREMIUM_MODEL', 'claude-opus-4-5')
        
        if default_openai_model not in VALID_MODELS['openai']:
            logger.warning(f"Invalid DEFAULT_OPENAI_MODEL '{default_openai_model}', using gpt-4o-mini")
            default_openai_model = "gpt-4o-mini"
        
        if default_claude_model not in VALID_MODELS['anthropic']:
            logger.warning(f"Invalid DEFAULT_CLAUDE_MODEL '{default_claude_model}', using claude-sonnet-4-5")
            default_claude_model = "claude-sonnet-4-5"
        
        return cls(
            default_provider=default_provider,
            claude_enabled=claude_enabled,
            failover_order=failover_order,
            default_openai_model=default_openai_model,
            default_claude_model=default_claude_model,
            default_openai_premium_model=default_openai_premium_model,
            default_claude_premium_model=default_claude_premium_model
        )
    
    def get_default_model(self, provider: Optional[LLMProvider] = None) -> str:
        """Get default model for the specified or default provider."""
        provider = provider or self.default_provider
        if provider == LLMProvider.ANTHROPIC:
            return self.default_claude_model
        return self.default_openai_model
    
    def get_premium_model(self, provider: Optional[LLMProvider] = None) -> str:
        """Get premium model for escalations."""
        provider = provider or self.default_provider
        if provider == LLMProvider.ANTHROPIC:
            return self.default_claude_premium_model
        return self.default_openai_premium_model


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters."""
    
    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """Return the provider enum for this adapter."""
        pass
    
    @abstractmethod
    def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Execute a chat completion request."""
        pass
    
    @abstractmethod
    def stream_chat(self, request: LLMRequest) -> Iterator[str]:
        """Execute a streaming chat completion request."""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """Estimate token count for text."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (API key configured, etc.)."""
        pass


class OpenAIAdapter(LLMAdapter):
    """
    OpenAI adapter - mirrors current production behavior exactly.
    
    This adapter is designed to produce byte-identical behavior to the
    existing direct OpenAI calls throughout the codebase.
    """
    
    def __init__(self):
        """Initialize OpenAI client."""
        self._client = None
        self._api_key = os.environ.get('OPENAI_API_KEY')
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None and self._api_key:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client
    
    def is_available(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self._api_key)
    
    def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Execute chat completion via OpenAI API.
        
        Mirrors existing production behavior exactly.
        """
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")
        
        start_time = datetime.utcnow()
        
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        api_params = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
        }
        
        if request.max_tokens:
            api_params["max_tokens"] = request.max_tokens
        
        if request.json_mode:
            api_params["response_format"] = {"type": "json_object"}
        
        try:
            client = self.client
            if client is None:
                raise RuntimeError("OpenAI client not initialized")
            response = client.chat.completions.create(**api_params)
            
            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            content = response.choices[0].message.content or ""
            
            usage = {}
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            logger.info(
                f"LLM_CALL provider=openai model={request.model} "
                f"tokens_in={usage.get('prompt_tokens', 0)} "
                f"tokens_out={usage.get('completion_tokens', 0)} "
                f"latency_ms={latency_ms:.0f} status=success"
            )
            
            return LLMResponse(
                content=content,
                model=request.model,
                provider="openai",
                usage=usage,
                latency_ms=latency_ms,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(
                f"LLM_CALL provider=openai model={request.model} "
                f"status=error error_type={type(e).__name__} error_msg={str(e)[:100]}"
            )
            raise
    
    def stream_chat(self, request: LLMRequest) -> Iterator[str]:
        """Execute streaming chat completion via OpenAI API."""
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")
        
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        api_params = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            api_params["max_tokens"] = request.max_tokens
        
        try:
            client = self.client
            if client is None:
                raise RuntimeError("OpenAI client not initialized")
            response = client.chat.completions.create(**api_params)
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    def count_tokens(self, text: str, model: str = "gpt-4o-mini") -> int:
        """
        Estimate token count for text.
        
        Uses rough approximation (4 chars per token) for efficiency.
        For precise counting, use tiktoken library.
        """
        return len(text) // 4


class AnthropicAdapter(LLMAdapter):
    """
    Anthropic (Claude) adapter using Replit AI Integrations.
    
    Uses Replit's managed Anthropic access (no external API key required).
    Supports claude-sonnet-4-5 (balanced), claude-opus-4-5 (complex), claude-haiku-4-5 (fast).
    """
    
    def __init__(self):
        """Initialize Anthropic client using Replit AI Integrations."""
        self._client = None
        self._api_key = os.environ.get('AI_INTEGRATIONS_ANTHROPIC_API_KEY')
        self._base_url = os.environ.get('AI_INTEGRATIONS_ANTHROPIC_BASE_URL')
    
    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None and self.is_available():
            try:
                from anthropic import Anthropic
                self._client = Anthropic(
                    api_key=self._api_key,
                    base_url=self._base_url
                )
            except ImportError:
                logger.error("anthropic package not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                return None
        return self._client
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.ANTHROPIC
    
    def is_available(self) -> bool:
        """Check if Anthropic via Replit AI Integrations is configured."""
        return bool(self._api_key and self._base_url)
    
    def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Execute chat completion via Anthropic Claude API."""
        if not self.is_available():
            raise RuntimeError("Anthropic adapter not available - missing AI Integrations config")
        
        start_time = time.time()
        
        model = request.model or "claude-sonnet-4-5"
        
        messages = []
        system_content = None
        
        for msg in request.messages:
            role = msg.role if hasattr(msg, 'role') else msg.get("role", "user")
            content = msg.content if hasattr(msg, 'content') else msg.get("content", "")
            
            if role == "system":
                system_content = content
            else:
                messages.append({
                    "role": role,
                    "content": content
                })
        
        api_params = {
            "model": model,
            "max_tokens": request.max_tokens or 8192,
            "messages": messages
        }
        
        if system_content:
            api_params["system"] = system_content
        
        if request.temperature is not None:
            api_params["temperature"] = request.temperature
        
        try:
            client = self.client
            if client is None:
                raise RuntimeError("Anthropic client not initialized")
            
            response = client.messages.create(**api_params)
            
            latency_ms = (time.time() - start_time) * 1000
            
            content = ""
            if response.content and len(response.content) > 0:
                content = response.content[0].text
            
            usage = {}
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            
            logger.info(
                f"LLM_CALL provider=anthropic model={model} "
                f"tokens_in={usage.get('prompt_tokens', 0)} "
                f"tokens_out={usage.get('completion_tokens', 0)} "
                f"latency_ms={latency_ms:.0f} status=success"
            )
            
            return LLMResponse(
                content=content,
                model=model,
                provider="anthropic",
                usage=usage,
                latency_ms=latency_ms,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(
                f"LLM_CALL provider=anthropic model={model} "
                f"status=error error_type={type(e).__name__} error_msg={str(e)[:100]}"
            )
            raise
    
    def stream_chat(self, request: LLMRequest) -> Iterator[str]:
        """Execute streaming chat completion via Anthropic Claude API."""
        if not self.is_available():
            raise RuntimeError("Anthropic adapter not available - missing AI Integrations config")
        
        model = request.model or "claude-sonnet-4-5"
        
        messages = []
        system_content = None
        
        for msg in request.messages:
            role = msg.role if hasattr(msg, 'role') else msg.get("role", "user")
            content = msg.content if hasattr(msg, 'content') else msg.get("content", "")
            
            if role == "system":
                system_content = content
            else:
                messages.append({
                    "role": role,
                    "content": content
                })
        
        api_params = {
            "model": model,
            "max_tokens": request.max_tokens or 8192,
            "messages": messages,
            "stream": True
        }
        
        if system_content:
            api_params["system"] = system_content
        
        if request.temperature is not None:
            api_params["temperature"] = request.temperature
        
        try:
            client = self.client
            if client is None:
                raise RuntimeError("Anthropic client not initialized")
            
            with client.messages.stream(**api_params) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
    
    def count_tokens(self, text: str, model: str = "claude-sonnet-4-5") -> int:
        """Estimate token count for text."""
        return len(text) // 4


class LLMGateway:
    """
    Central gateway for all LLM operations.
    
    Provides:
    - Provider abstraction (OpenAI, Anthropic)
    - Configuration-based routing
    - Failover support
    - Structured logging
    - Token usage tracking
    
    Usage:
        gateway = LLMGateway.get_instance()
        response = gateway.chat_completion(request)
    """
    
    _instance: Optional['LLMGateway'] = None
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize gateway with configuration."""
        self.config = config or LLMConfig.from_environment()
        self._adapters: Dict[LLMProvider, LLMAdapter] = {}
        self._initialize_adapters()
    
    @classmethod
    def get_instance(cls, config: Optional[LLMConfig] = None) -> 'LLMGateway':
        """Get singleton instance of LLMGateway."""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing)."""
        cls._instance = None
    
    def _initialize_adapters(self):
        """Initialize available adapters."""
        self._adapters[LLMProvider.OPENAI] = OpenAIAdapter()
        
        if self.config.claude_enabled:
            self._adapters[LLMProvider.ANTHROPIC] = AnthropicAdapter()
            logger.info("Claude adapter registered (CLAUDE_ENABLED=true)")
        else:
            logger.debug("Claude adapter disabled (CLAUDE_ENABLED=false)")
    
    def _get_adapter(
        self,
        provider_override: Optional[LLMProvider] = None,
        business_account_id: Optional[int] = None,
        campaign_id: Optional[int] = None
    ) -> LLMAdapter:
        """
        Get appropriate adapter based on configuration precedence.
        
        Precedence: provider_override → campaign → business_account → env default
        """
        target_provider = provider_override or self.config.default_provider
        
        if target_provider == LLMProvider.ANTHROPIC and not self.config.claude_enabled:
            logger.warning("Anthropic requested but CLAUDE_ENABLED=false, falling back to OpenAI")
            target_provider = LLMProvider.OPENAI
        
        adapter = self._adapters.get(target_provider)
        
        if not adapter or not adapter.is_available():
            logger.warning(f"Adapter {target_provider} unavailable, using failover")
            for fallback in self.config.failover_order:
                fallback_adapter = self._adapters.get(fallback)
                if fallback_adapter and fallback_adapter.is_available():
                    return fallback_adapter
            raise RuntimeError("No LLM providers available")
        
        return adapter
    
    def chat_completion(
        self,
        request: LLMRequest,
        provider_override: Optional[LLMProvider] = None,
        business_account_id: Optional[int] = None,
        campaign_id: Optional[int] = None
    ) -> LLMResponse:
        """
        Execute chat completion through appropriate adapter.
        
        Args:
            request: Standardized LLM request
            provider_override: Force specific provider
            business_account_id: For tenant-level config lookup
            campaign_id: For campaign-level config lookup
        
        Returns:
            Standardized LLM response
        """
        adapter = self._get_adapter(provider_override, business_account_id, campaign_id)
        
        logger.debug(
            f"LLM_GATEWAY_ROUTE provider={adapter.provider.value} model={request.model} "
            f"json_mode={request.json_mode} stream={request.stream}"
        )
        
        return adapter.chat_completion(request)
    
    def stream_chat(
        self,
        request: LLMRequest,
        provider_override: Optional[LLMProvider] = None,
        business_account_id: Optional[int] = None,
        campaign_id: Optional[int] = None
    ) -> Iterator[str]:
        """Execute streaming chat completion through appropriate adapter."""
        adapter = self._get_adapter(provider_override, business_account_id, campaign_id)
        
        logger.debug(
            f"LLM_GATEWAY_STREAM provider={adapter.provider.value} model={request.model}"
        )
        
        return adapter.stream_chat(request)
    
    def count_tokens(self, text: str, model: str = "gpt-4o-mini") -> int:
        """Estimate token count for text using default adapter."""
        adapter = self._get_adapter()
        return adapter.count_tokens(text, model)


def get_gateway() -> LLMGateway:
    """Convenience function to get gateway instance."""
    return LLMGateway.get_instance()


def is_gateway_enabled() -> bool:
    """Check if LLM Gateway is enabled via feature flag."""
    return os.environ.get('LLM_GATEWAY_ENABLED', 'true').lower() == 'true'


def is_claude_enabled() -> bool:
    """Check if Claude/Anthropic provider is enabled via feature flag."""
    return os.environ.get('CLAUDE_ENABLED', 'false').lower() == 'true'
