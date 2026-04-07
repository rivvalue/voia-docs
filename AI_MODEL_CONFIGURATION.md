# AI Model Configuration Guide

This document explains how to configure the provider-agnostic LLM gateway for different parts of the VOÏA platform using environment variables. The gateway supports both OpenAI and Anthropic (Claude) as first-class providers, with automatic model translation, per-tenant configuration, and failover.

**Last Updated:** April 7, 2026
**Document Version:** 2.0

---

## Environment Variables

### Provider Selection

#### `DEFAULT_LLM_PROVIDER`
**Purpose:** Selects the active LLM provider for all gateway-routed calls.

**Options:**
- `openai` (default) — All calls route to OpenAI
- `anthropic` — All calls route to Claude; requires `CLAUDE_ENABLED=true`

#### `CLAUDE_ENABLED`
**Purpose:** Feature flag that permits Claude as a provider. Must be `true` for Anthropic routing to activate.

**Default:** `false`

#### `PROVIDER_FAILOVER_ORDER`
**Purpose:** Comma-separated ordered list of providers to try if the primary fails.

**Example:** `anthropic,openai` — try Claude first, fall back to OpenAI on error.

---

### Model Selection

#### `DEFAULT_OPENAI_MODEL`
**Purpose:** Default OpenAI model for standard (non-premium) calls through the gateway.

**Default:** `gpt-4o-mini`

**Options:** `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`

#### `DEFAULT_OPENAI_PREMIUM_MODEL`
**Purpose:** OpenAI model used for calls that request the premium model (escalations, complex analysis).

**Default:** `gpt-4o`

#### `DEFAULT_CLAUDE_MODEL`
**Purpose:** Default Claude model for standard calls when `DEFAULT_LLM_PROVIDER=anthropic`.

**Default:** `claude-sonnet-4-5`

**Options:** `claude-3-5-haiku-latest`, `claude-sonnet-4-5`, `claude-opus-4-5`

**Recommended (Scenario B):** `claude-3-5-haiku-latest`

#### `DEFAULT_CLAUDE_PREMIUM_MODEL`
**Purpose:** Claude model used for premium calls (transcript analysis, escalations) when Anthropic is the active provider.

**Default:** `claude-opus-4-5`

**Options:** `claude-3-5-haiku-latest`, `claude-sonnet-4-5`, `claude-opus-4-5`

**Recommended (Scenario B):** `claude-sonnet-4-5`

---

### How the Gateway Handles Model Translation

When `DEFAULT_LLM_PROVIDER=anthropic`, the gateway's `_translate_model_for_provider()` function automatically maps incoming OpenAI model names to their Claude equivalents:

- Any `gpt-4o` or `gpt-4-turbo` request → `DEFAULT_CLAUDE_PREMIUM_MODEL` (e.g. `claude-sonnet-4-5`)
- Any other OpenAI model request → `DEFAULT_CLAUDE_MODEL` (e.g. `claude-3-5-haiku-latest`)

This means meeting transcript analysis (which hard-codes `gpt-4o` in its request) will automatically route to the premium Claude model — the correct behaviour for complex document analysis.

---

## AI Call Inventory

This section documents every active LLM call surface in VOÏA as of the April 2026 performance audit.

### Active LLM Calls

| # | Feature | Module | Gateway? | Current model | Calls/year (est.) | Tokens/call (approx.) | Task complexity |
|---|---|---|---|---|---|---|---|
| 1 | Survey turn — data extraction | `ai_conversational_survey_v2.py` | Yes | Default model (gpt-4o-mini) | ~480K | ~750 | Low — structured JSON field extraction |
| 2 | Survey turn — question generation | `ai_conversational_survey_v2.py` | Yes | Default model (gpt-4o-mini) | ~480K | ~400 | Low-Medium — natural language generation |
| 3 | Post-survey analysis (consolidated) | `ai_analysis.py` | Yes | Default model (gpt-4o-mini) | ~80K | ~3,000 | Medium — sentiment, themes, churn, risk in one call |
| 4 | Meeting transcript analysis | `task_queue.py` | Yes (hard-codes gpt-4o → translated to premium model) | gpt-4o (→ premium Claude when Anthropic enabled) | ~200/year | ~12,000 | High — full document understanding, 20 structured fields |
| 5 | QBR transcript analysis | `task_queue.py` | Yes (uses default_openai_model → translated) | gpt-4o-mini (→ default Claude when Anthropic enabled) | ~80–160/year | ~22,000 | High — strategic intelligence extraction, multilingual, stakeholder identification |
| 6 | High-risk escalations | `ai_analysis.py` (rule-based escalation trigger, LLM call for notification generation) | Yes | gpt-4o | Low volume | ~1,000 | Medium — nuanced churn/risk narrative |

#### Call surface notes

**Survey turns (calls #1 and #2):** The V2 survey controller (`DeterministicSurveyController`) makes exactly two sequential LLM calls per conversation turn via `process_user_response()`. The first call (`_extract_with_ai`) performs structured JSON field extraction from the user's natural-language reply. The second call (`_generate_question_with_ai`) generates the next conversational question based on outstanding survey goals. Both calls go through the gateway and both use the default model. At ~80K conversations/year with ~6 turns average, this produces ~960K calls/year for these two surfaces combined.

**Post-survey analysis (call #3):** `perform_consolidated_ai_analysis()` in `ai_analysis.py` makes a single LLM call per completed survey response. It covers all six analysis dimensions in one pass: sentiment, key themes, churn risk, growth opportunities, account risk factors, and an executive summary with reasoning. The model is selected via `llm_config.get_default_model()`, which routes to the default Claude model when Anthropic is active.

**Meeting transcript analysis (call #4):** `_analyze_transcript_with_ai()` in `task_queue.py` hard-codes `model="gpt-4o"` in the gateway request. Because `gpt-4o` maps to the premium model in the translation layer, this call always routes to `DEFAULT_CLAUDE_PREMIUM_MODEL` when Anthropic is enabled — the correct behaviour for a task requiring 20-field structured extraction from 12K-token transcripts.

**QBR transcript analysis (call #5):** `_analyze_qbr_transcript_with_ai()` in `task_queue.py` uses `gateway.config.default_openai_model`, which maps to `DEFAULT_CLAUDE_MODEL` in Anthropic mode. QBR transcripts average ~22K tokens and require multilingual support and stakeholder identification across 60–90 minute sessions. This is the highest reasoning-complexity call in the system; using the default Claude model means the quality of `DEFAULT_CLAUDE_MODEL` is critical for this surface.

**High-risk escalations (call #6):** When rule-based analysis in `enhance_analysis_with_rules()` detects high churn risk signals, a follow-up LLM call is made for notification generation using `gpt-4o`. This maps to `DEFAULT_CLAUDE_PREMIUM_MODEL` in Anthropic mode. Volume is low but the narrative quality directly affects account manager decision-making.

**Executive report generation:** The executive report service (`executive_report_service.py`) makes **no LLM calls**. It aggregates pre-computed analysis fields from completed survey responses. Reports are compute-intensive (in-memory aggregation and PDF rendering) but have zero AI token cost.

---

### Dead Code (No Action Needed)

`analyze_sentiment()`, `extract_key_themes()`, `assess_churn_risk()`, `identify_growth_opportunities()`, `identify_account_risk_factors()` in `ai_analysis.py` — superseded by the consolidated call (#3). Never invoked in production.

---

### One Gateway Gap to Note

`ai_conversational_survey.py` (v1 survey) is still imported and used as a fallback when the `DETERMINISTIC_SURVEY_FLOW` feature flag is disabled. It makes direct OpenAI calls and does **not** go through the gateway — it uses `get_openai_model(premium=True)` (gpt-4o) with no Claude routing possible. If the team wishes to fully migrate to Claude, this flag must be permanently enabled in production to retire the v1 path. See the action item at the end of this document.

---

## Claude Economic Analysis

### Pricing Reference (April 2026)

| Model | Input $/1M | Output $/1M | Blended $/1M (70/30 split) | Best suited for |
|---|---|---|---|---|
| gpt-4o-mini | $0.15 | $0.60 | ~$0.29 | High-volume structured tasks |
| gpt-4o | $2.50 | $10.00 | ~$4.75 | Complex reasoning, escalations |
| claude-3-5-haiku-latest | $0.80 | $4.00 | ~$1.76 | High-volume structured tasks (Claude equivalent of gpt-4o-mini) |
| claude-sonnet-4-5 | $3.00 | $15.00 | ~$6.60 | Analysis, synthesis, document understanding (Claude equivalent of gpt-4o) |
| claude-opus-4-5 | $15.00 | $75.00 | ~$33.00 | Maximum reasoning (not recommended at current scale) |

---

### Baseline: Current OpenAI Costs (20 Accounts, 80K Conversations/Year)

All baseline numbers from the April 2026 performance audit.

| Cost item | Volume | Model | Annual cost |
|---|---|---|---|
| Survey extraction + question gen (2 calls/turn, ~6 turns avg, 80K convs) | 960K calls, 552M tokens | gpt-4o-mini | $331 |
| Post-survey analysis (1 consolidated call per survey) | 80K calls, ~240M tokens | gpt-4o-mini | $77 |
| Meeting transcript analysis | ~200 calls, ~2.4M tokens | gpt-4o | ~$11 |
| QBR transcript analysis | ~80–160 calls, ~2–4M tokens | gpt-4o-mini | ~$2 |
| High-risk escalations | Low volume | gpt-4o | $480 |
| Executive report generation | Very low | — (reads pre-computed fields, no LLM call) | $0 |
| Infrastructure (email, queue, hosting) | — | — | ~$552 |
| **Grand total** | | | **~$1,453/year — ~$73/account** |

Note: The executive report service makes no LLM calls. It aggregates pre-computed analysis fields from survey responses.

---

### Model Recommendation Per Call Type

| Call type | Recommended Claude model | Rationale |
|---|---|---|
| Survey extraction (high volume, structured JSON, ~750 tokens) | `claude-3-5-haiku-latest` | Low complexity, latency-sensitive, structured output. Haiku matches gpt-4o-mini quality on extraction tasks. |
| Survey question generation (high volume, ~400 tokens) | `claude-3-5-haiku-latest` | Short generation, conversational phrasing, no complex reasoning required. |
| Post-survey analysis (medium volume, ~3,000 tokens, 6 analysis types in one call) | `claude-sonnet-4-5` | Insight quality directly affects what managers see on dashboards. Sonnet's reasoning depth improves churn risk nuance and theme identification over Haiku at this task. |
| Meeting transcript analysis (~12,000 tokens, 20 structured fields) | `claude-sonnet-4-5` (via premium model translation) | Large document understanding, multi-field extraction in one pass. Sonnet handles context windows reliably. Haiku may miss nuance in long transcripts. |
| QBR transcript analysis (~22,000 tokens, multilingual, stakeholder identification) | `claude-sonnet-4-5` (via default model when Sonnet is set as default) | Complex strategic intelligence extraction across 60–90 min transcripts in any language. This is the highest reasoning-complexity call in the system. Sonnet is required; Haiku is not recommended. |
| High-risk escalations (nuanced churn/risk narrative) | `claude-sonnet-4-5` | Replaces gpt-4o. Sonnet is directly comparable in reasoning depth for this task. |

---

### Scenario A — All claude-3-5-haiku-latest (Lowest Claude Cost)

| Cost item | Annual cost | vs current |
|---|---|---|
| Survey extraction + question gen | ~$970 | +$639 |
| Post-survey analysis | ~$226 | +$149 |
| Meeting transcript analysis | ~$4 | −$7 (cheaper than gpt-4o) |
| QBR transcript analysis | ~$6 | +$4 |
| High-risk escalations (was gpt-4o) | ~$178 | −$302 |
| Infrastructure (unchanged) | $552 | — |
| **Grand total** | **~$1,936/year** | **+33%** |
| **Per account** | **~$97** | Just under $100 ceiling ✓ |

Trade-off: Haiku on the post-survey analysis call and QBR transcripts will produce lower-quality strategic insights compared to Sonnet. Acceptable for the survey analysis task; not recommended for the complex QBR reasoning task (22K tokens, multilingual stakeholder extraction).

Configuration:
```
CLAUDE_ENABLED=true
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_CLAUDE_MODEL=claude-3-5-haiku-latest
DEFAULT_CLAUDE_PREMIUM_MODEL=claude-3-5-haiku-latest
PROVIDER_FAILOVER_ORDER=anthropic,openai
```

---

### Scenario B — Haiku for Surveys, Sonnet for Analysis and Document Intelligence (Recommended)

Haiku handles the 960K high-volume survey calls where cost dominates. Sonnet handles the reasoning-heavy calls: post-survey analysis, transcript analysis, QBR, and escalations.

| Cost item | Model | Annual cost | vs current |
|---|---|---|---|
| Survey extraction + question gen (960K calls) | claude-3-5-haiku-latest | ~$970 | +$639 |
| Post-survey analysis | claude-sonnet-4-5 | ~$847 | +$770 |
| Meeting transcript analysis (~2.4M tokens) | claude-sonnet-4-5 (via premium translation) | ~$16 | +$5 |
| QBR transcript analysis (~3M tokens) | claude-sonnet-4-5 (via default model) | ~$20 | +$18 |
| High-risk escalations (was gpt-4o) | claude-sonnet-4-5 | ~$667 | +$187 |
| Infrastructure (unchanged) | — | $552 | — |
| **Grand total** | | **~$3,072/year** | **+111%** |
| **Per account** | | **~$154** | Requires revising ceiling to ~$160 |

Trade-off: Requires revising the cost ceiling from $100 to ~$160/account. Delivers the best quality across all call types — survey quality unchanged (Haiku is appropriate), analysis and document intelligence quality improved over gpt-4o-mini.

Configuration:
```
CLAUDE_ENABLED=true
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_CLAUDE_MODEL=claude-3-5-haiku-latest
DEFAULT_CLAUDE_PREMIUM_MODEL=claude-sonnet-4-5
PROVIDER_FAILOVER_ORDER=anthropic,openai
```

> **Note on QBR routing in Scenario B:** The QBR transcript analysis call uses `gateway.config.default_openai_model`, which translates to `DEFAULT_CLAUDE_MODEL` in Anthropic mode. The Scenario B configuration above sets `DEFAULT_CLAUDE_MODEL=claude-3-5-haiku-latest` (for survey cost efficiency), which means QBR calls will also route to Haiku under this configuration — not Sonnet. The QBR cost figure (~$20) in the table above assumes `claude-sonnet-4-5` for that call surface. To achieve Sonnet on QBR while keeping Haiku for surveys, the gateway would need per-call model override support (not currently available). If QBR quality with Haiku is unacceptable after testing, setting `DEFAULT_CLAUDE_MODEL=claude-sonnet-4-5` will route both QBR and survey turns to Sonnet, increasing survey costs toward Scenario C levels. Validate QBR output quality with Haiku before committing.

---

### Scenario C — All claude-sonnet-4-5 (Maximum Claude Quality, Not Recommended at Current Scale)

| Cost item | Annual cost | vs current |
|---|---|---|
| Survey extraction + question gen | ~$3,641 | +$3,310 |
| Post-survey analysis | ~$847 | +$770 |
| Transcript + QBR + escalations | ~$703 | +$210 |
| Infrastructure | $552 | — |
| **Grand total** | **~$5,743/year** | **+295%** |
| **Per account** | **~$287** | Far exceeds ceiling |

Not recommended. Applying Sonnet to 960K high-volume survey calls provides no measurable quality improvement over Haiku for extraction and short question generation, at a 3.75× cost penalty on the dominant cost item.

---

### Summary Recommendation Table

| Scenario | Annual total | Per account | vs $100 ceiling | Quality level |
|---|---|---|---|---|
| Current (OpenAI baseline) | ~$1,453 | ~$73 | Under ✓ | Good |
| **A — All Haiku** | **~$1,936** | **~$97** | **Just under ✓** | Good (reduced on QBR/analysis) |
| **B — Haiku + Sonnet (recommended)** | **~$3,072** | **~$154** | **Requires ceiling revision to ~$160** | Best |
| C — All Sonnet | ~$5,743 | ~$287 | Significantly exceeds | Maximum |
| OpenAI mixed (keep current) | ~$1,453 | ~$73 | Under ✓ | Good |

**Recommendation:** Scenario B is the correct Claude-first strategy. It applies Haiku where volume is the constraint (survey turns, 960K calls/year) and Sonnet where reasoning quality directly affects client-facing outputs (analysis dashboards, QBR strategic intelligence, escalation narratives). The cost ceiling should be revised from $100 to $160/account to accommodate this.

Scenario A is viable if the $100 ceiling is a hard constraint, but the QBR transcript analysis quality degradation (Haiku on 22K-token multilingual documents) is a meaningful trade-off that should be validated before committing.

Opus is not recommended for any production use case at current scale.

---

### Cost Ceiling Note

The $100/account/year ceiling was set against a gpt-4o-mini baseline in the November 2025 audit. Favouring Claude as the primary provider reflects a deliberate quality-first choice and warrants a formal ceiling revision to ~$160/account. Costs should be reviewed when: (a) conversation volume exceeds 200K/year, (b) QBR upload frequency increases significantly, or (c) Anthropic revises model pricing.

---

## Recommended Configuration (Scenario B)

```
# Provider selection
CLAUDE_ENABLED=true
DEFAULT_LLM_PROVIDER=anthropic

# Haiku for high-volume survey calls (extraction + question generation)
DEFAULT_CLAUDE_MODEL=claude-3-5-haiku-latest

# Sonnet for analysis, transcripts, QBR, escalations (via premium model translation)
DEFAULT_CLAUDE_PREMIUM_MODEL=claude-sonnet-4-5

# Failover to OpenAI if Anthropic is unavailable
PROVIDER_FAILOVER_ORDER=anthropic,openai
```

Existing variables that continue to control the OpenAI fallback path:
```
DEFAULT_OPENAI_MODEL=gpt-4o-mini
DEFAULT_OPENAI_PREMIUM_MODEL=gpt-4o
```

---

### One Action Required for Full Claude Coverage

The v1 conversational survey (`ai_conversational_survey.py`) bypasses the gateway entirely — it calls OpenAI directly using `get_openai_model(premium=True)`. This path is active when the `DETERMINISTIC_SURVEY_FLOW` feature flag is off. To ensure 100% of survey calls route through Claude, set `DETERMINISTIC_SURVEY_FLOW=true` permanently in production, making v1 a true dead code path.

---

## Staged Rollout Strategy (Recommended)

### Week 1: Test Analysis Optimization
```bash
AI_ANALYSIS_MODEL=gpt-4o-mini
AI_CONVERSATION_MODEL=gpt-4o
```
**Validate:** Review 50 analyzed responses for quality
**Expected:** Zero quality impact, $1,128/month savings

### Week 2-4: Monitor Quality
**Track metrics:**
- Sentiment accuracy vs historical data
- Churn risk prediction accuracy
- Theme extraction completeness

**Success criteria:** <2% deviation from GPT-4o baseline

### Optional: Test Conversation Optimization (High Risk, High Reward)
```bash
AI_ANALYSIS_MODEL=gpt-4o-mini
AI_CONVERSATION_MODEL=gpt-4o-mini  # Test this carefully
```
**Validate:** Run 100 survey conversations, review customer experience
**Expected:** $3,215/month additional savings if quality acceptable

---

## Monitoring & Quality Assurance

### Key Metrics to Monitor

1. **Analysis Quality:**
   - Sentiment label accuracy (compare to manual review sample)
   - Churn risk false positives/negatives
   - Theme completeness (are key topics captured?)

2. **Conversation Quality:**
   - Survey completion rates
   - Average conversation length
   - Customer satisfaction with survey experience

3. **Cost Tracking:**
   - Daily OpenAI API spend
   - Cost per response analysis
   - Cost per survey conversation

### Quality Gates

**RED FLAG - Revert immediately if:**
- Sentiment accuracy drops >5%
- Churn risk false negatives >2% (missing critical unhappy customers)
- Survey completion rate drops >10%
- Customer complaints about survey quality

**YELLOW FLAG - Monitor closely:**
- Sentiment accuracy drops 2-5%
- Theme extraction misses minor topics
- Slight increase in conversation length

**GREEN LIGHT - Safe to continue:**
- Metrics within 2% of baseline
- Cost savings realized as expected
- No quality complaints

---

## Emergency Rollback

If you need to revert to premium models immediately:

1. **Update secrets in Replit:**
   ```bash
   AI_ANALYSIS_MODEL=gpt-4o
   AI_CONVERSATION_MODEL=gpt-4o
   ```

2. **Restart application:**
   - In Replit console: Click "Stop" then "Run"
   - Or: `pkill gunicorn` and restart

3. **Verify rollback:**
   - Check logs for "model=gpt-4o" in OpenAI API calls
   - Monitor next 10 responses for quality

**Rollback time:** ~30 seconds

---

## Support

For questions or issues with model configuration:
1. Check Replit logs for OpenAI API errors
2. Verify secrets are set correctly in Secrets Manager
3. Ensure application was restarted after changing secrets
4. Review this document for recommended configurations
