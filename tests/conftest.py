"""
Pytest configuration and shared fixtures for VOÏA test suite.
"""
import os
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv('SESSION_SECRET', 'test-secret-key')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-openai-key')


@pytest.fixture
def gateway_enabled(monkeypatch):
    """Enable LLM gateway for tests."""
    monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'true')
    monkeypatch.setenv('CLAUDE_ENABLED', 'false')


@pytest.fixture
def gateway_disabled(monkeypatch):
    """Disable LLM gateway for tests."""
    monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'false')


@pytest.fixture
def claude_enabled(monkeypatch):
    """Enable Claude provider for tests."""
    monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'true')
    monkeypatch.setenv('CLAUDE_ENABLED', 'true')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-anthropic-key')


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"test": "response"}'
    return mock_response


@pytest.fixture
def mock_transcript_response():
    """Create a mock transcript analysis response."""
    return '''{
        "NPS Score": 8,
        "NPS Category": "Passive",
        "Satisfaction Rating": 4,
        "Product Value Rating": 4,
        "Service Rating": 5,
        "Pricing Rating": 3,
        "Improvement Feedback": "Better pricing options needed",
        "Recommendation Reason": "Good service but expensive",
        "Additional Comments": "Overall satisfied with the product",
        "Sentiment Score": 0.6,
        "Sentiment Label": "Positive",
        "Key Themes": ["pricing", "service quality", "product value"],
        "Churn Risk Score": 0.3,
        "Churn Risk Level": "Low",
        "Churn Risk Factors": ["pricing concerns"],
        "Growth Opportunities": ["upsell premium features"],
        "Account Risk Factors": [],
        "Growth Factor": 1.5,
        "Growth Rate": "15%",
        "Growth Range": "7-8"
    }'''
