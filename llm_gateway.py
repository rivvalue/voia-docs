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
    """Configuration for LLM Gateway."""
    default_provider: LLMProvider = LLMProvider.OPENAI
    claude_enabled: bool = False
    failover_order: List[LLMProvider] = field(default_factory=lambda: [LLMProvider.OPENAI])
    model_mapping: Dict[str, str] = field(default_factory=dict)
    
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
        
        return cls(
            default_provider=default_provider,
            claude_enabled=claude_enabled,
            failover_order=failover_order
        )


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
            
            logger.debug(f"OpenAI completion: model={request.model}, tokens={usage.get('total_tokens', 'N/A')}, latency={latency_ms:.0f}ms")
            
            return LLMResponse(
                content=content,
                model=request.model,
                provider="openai",
                usage=usage,
                latency_ms=latency_ms,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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
    Anthropic (Claude) adapter - placeholder for future implementation.
    
    This adapter will be implemented in Step 2 of the migration plan.
    Currently returns NotImplementedError to ensure it's not used prematurely.
    """
    
    def __init__(self):
        """Initialize Anthropic client placeholder."""
        self._client = None
        self._api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.ANTHROPIC
    
    def is_available(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(self._api_key)
    
    def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Placeholder - to be implemented in Step 2."""
        raise NotImplementedError("Anthropic adapter not yet implemented. Set CLAUDE_ENABLED=false.")
    
    def stream_chat(self, request: LLMRequest) -> Iterator[str]:
        """Placeholder - to be implemented in Step 2."""
        raise NotImplementedError("Anthropic adapter not yet implemented. Set CLAUDE_ENABLED=false.")
    
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
        
        logger.debug(f"LLM Gateway: routing to {adapter.provider.value}, model={request.model}")
        
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
        
        logger.debug(f"LLM Gateway: streaming via {adapter.provider.value}, model={request.model}")
        
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
