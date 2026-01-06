# VOÏA Environment Variables Configuration

This document describes all configurable environment variables for the VOÏA platform.

---

## LLM Gateway Configuration

These variables control which AI models are used throughout the application.

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_OPENAI_MODEL` | `gpt-4o-mini` | Standard model for analysis tasks (sentiment analysis, theme extraction). Cost-optimized for high-volume operations. |
| `DEFAULT_OPENAI_PREMIUM_MODEL` | `gpt-4o` | Premium model for conversational surveys and complex reasoning tasks. Higher quality but more expensive. |
| `DEFAULT_CLAUDE_MODEL` | `claude-sonnet-4-5` | Standard Anthropic model (used when Claude is enabled). Balanced performance and cost. |
| `DEFAULT_CLAUDE_PREMIUM_MODEL` | `claude-opus-4-5` | Premium Anthropic model for complex tasks (used when Claude is enabled). |
| `CLAUDE_ENABLED` | `false` | Enable/disable Claude models. Set to `true` to use Anthropic models via the LLM Gateway. |
| `DEFAULT_LLM_PROVIDER` | `openai` | Default AI provider. Options: `openai`, `anthropic`. Only applies when using the LLM Gateway. |
| `LLM_GATEWAY_ENABLED` | `true` | Enable/disable the LLM Gateway abstraction layer. When disabled, direct OpenAI calls are used. |

---

## Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | (required) | PostgreSQL connection string. Automatically set by Replit. |

---

## Security & Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_SECRET` | (required) | Secret key for Flask session encryption. Must be a strong random string. |
| `EMAIL_ENCRYPTION_KEY` | (required) | Fernet key for encrypting stored email credentials. |
| `JWT_SECRET_KEY` | (auto-generated) | Secret for JWT token generation. Falls back to SESSION_SECRET if not set. |

---

## Email Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAIL_SERVER` | `None` | SMTP server hostname for sending emails. |
| `MAIL_PORT` | `587` | SMTP server port. |
| `MAIL_USE_TLS` | `True` | Enable TLS encryption for email. |
| `MAIL_USERNAME` | `None` | SMTP authentication username. |
| `MAIL_PASSWORD` | `None` | SMTP authentication password. |
| `ADMIN_EMAIL` | `None` | Default admin email for notifications. |

---

## Monitoring & Performance

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTRY_DSN` | `None` | Sentry error tracking DSN. Leave empty to disable Sentry. |
| `SENTRY_ENVIRONMENT` | `Development` | Environment name for Sentry reporting. |
| `SENTRY_SAMPLE_RATE` | `0.1` | Percentage of transactions to sample (0.0 to 1.0). |
| `RESPONSE_TIME_THRESHOLD` | `1000` | Response time threshold in milliseconds for performance alerts. |
| `ERROR_RATE_THRESHOLD` | `5.0` | Error rate percentage threshold for alerts. |

---

## Caching Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_ENABLED` | `true` | Enable/disable response caching. |
| `CACHE_TYPE` | `SimpleCache` | Cache backend type. Options: `SimpleCache`, `RedisCache`. |
| `CACHE_DEFAULT_TIMEOUT` | `7200` | Default cache timeout in seconds (2 hours). |
| `REDIS_URL` | `None` | Redis connection URL (required if using RedisCache). |

---

## Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `UI_VERSION` | `2` | UI version toggle. Use `2` for latest design patterns. |
| `USE_TOPIC_TRANSITIONS` | `true` | Enable natural language transitions between survey topics. |
| `ENABLE_CONCURRENT_CAMPAIGNS` | `false` | Allow multiple active campaigns per business account. |

---

## How to Configure

1. Open your Replit project
2. Click **Tools** in the left sidebar
3. Select **Secrets**
4. Click **New Secret** to add or modify variables

Changes take effect after restarting the application.

---

## Model Pricing Reference

### OpenAI Models
| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |

### Anthropic Models (via Replit AI Integrations)
| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| claude-haiku-4-5 | $1.00 | $5.00 |
| claude-sonnet-4-5 | $3.00 | $15.00 |
| claude-opus-4-5 | $5.00 | $25.00 |

**Recommendation:** OpenAI (GPT-4o-mini) is recommended for production due to lower costs at scale.
