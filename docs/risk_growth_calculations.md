# Risk Factor & Growth Opportunities Calculation Methodology

**Version**: 2.0  
**Last Updated**: April 2026  
**Source**: `ai_analysis.py`, `data_storage.py`

---

## Overview

VOÏA calculates Risk Factors and Growth Opportunities using a hybrid approach that combines:
1. **Rule-based scoring** - Deterministic calculations based on NPS scores and ratings
2. **AI enhancement** - Additional insights extracted from customer feedback text
3. **Influence weighting** - Each respondent's signals are scaled by their seniority tier

This methodology is **provider-agnostic** and produces consistent results whether using OpenAI or Claude/Anthropic.

---

## 0. Influence Weighting (Phase 1 — April 2026)

Not all respondents carry equal weight in account-level scoring. A C-level Detractor
who controls contract renewals represents a materially higher churn risk than an end
user with the same NPS score.

### 0.1 Influence Tier Multipliers

| Seniority Tier | Example Titles | Multiplier |
|---------------|---------------|-----------|
| C-Level | CEO, CFO, COO, CTO, President | 5× |
| VP / Director | VP, Vice President, Director, Head of | 3× |
| Manager | Manager, Product Manager, Program Manager | 2× |
| Team Lead | Team Lead, Supervisor, Lead, Coordinator | 1.5× |
| End User / IC | All others, unknown roles | 1× |

### 0.2 Where Influence Is Applied

| Component | How Influence Is Applied |
|-----------|------------------------|
| `SurveyResponse.influence_weight` | Float column set at analysis time |
| AI prompt (CHURN RISK section) | Model is instructed to weight signals by influence level |
| AI prompt (GROWTH OPPORTUNITIES section) | Model is instructed to weight positive signals by influence |
| `enhance_analysis_with_rules()` | NPS override thresholds scale inversely with influence (high-influence respondents trigger High risk at a lower AI score) |
| `assess_churn_risk_fallback()` | Risk points multiplied by `influence_weight` before threshold comparison |
| Growth opportunity / risk factor aggregation | `count` incremented by `influence_weight` per response, not by 1 |
| `calculate_weighted_account_balance()` | `count`-based scores already influence-weighted via aggregation |

### 0.3 Fallback Behaviour

If a participant has no role field, or the role cannot be matched to a known tier, the
system falls back to a weight of **1.0** (End User equivalent) without error. Historical
completed campaigns are not affected — their frozen KPI snapshots remain unchanged.

---

## 1. Churn Risk Assessment

### 1.1 Points-Based Scoring System

The system assigns risk points based on detected signals:

| Signal | Points Added | Description |
|--------|-------------|-------------|
| Churn keywords detected | +5 | Words like "leave", "switch", "cancel", "terminate", "competitor" |
| Low NPS score (0-6) | +3 | Detractor category indicates dissatisfaction |
| Critical NPS score (0-3) | Forced High | Overrides to High risk regardless of other factors |

### 1.2 Risk Level Conversion

| Total Points | Risk Level |
|-------------|------------|
| 5+ | High |
| 3-4 | Medium |
| 1-2 | Low |
| 0 | Minimal |

### 1.3 NPS Override Rules

To prevent false negatives, the system enforces minimum risk levels based on NPS:

- **NPS 0-3**: Minimum risk score of 5, forced to "High" level
- **NPS 4-6**: Minimum risk score of 3, upgrades "Minimal" to "Medium"

---

## 2. Account Risk Factors

Account Risk Factors provide detailed, actionable risk indicators with severity levels.

### 2.1 Automatic Risk Factor Generation

| Condition | Risk Type | Severity | Recommended Action |
|-----------|-----------|----------|-------------------|
| NPS score 0-3 | `critical_satisfaction` | Critical | Schedule urgent customer success call within 24 hours |
| Any rating ≤ 2 (satisfaction, product, service, pricing) | `poor_ratings` | High | Address specific pain points in affected areas |
| High/Medium churn risk level | `churn_risk` | Matches churn level | Implement retention measures and regular check-ins |

### 2.2 AI-Enhanced Risk Identification

The AI analyzes customer feedback text to identify additional risk factors not captured by quantitative scores. Each AI-identified factor includes:

- **Type**: Category of risk (e.g., "service_quality", "competitive_threat")
- **Description**: Specific explanation of the risk
- **Severity**: Low / Medium / High / Critical
- **Action**: Recommended mitigation step

### 2.3 Severity Level Definitions

| Severity | Definition | Response Time |
|----------|------------|---------------|
| Critical | Immediate action required, high churn probability | Within 24 hours |
| High | Significant issue affecting customer relationship | Within 1 week |
| Medium | Notable concern requiring attention | Within 2 weeks |
| Low | Minor issue for monitoring | Next scheduled touchpoint |

---

## 3. Growth Opportunities

Growth Opportunities identify positive signals indicating potential for expansion, upsell, or advocacy.

### 3.1 Automatic Opportunity Detection

| Condition | Opportunity Type | Description | Recommended Action |
|-----------|-----------------|-------------|-------------------|
| NPS score 9-10 | `advocacy` | Customer is a Promoter | Engage for case studies, referrals, or testimonials |
| Any rating ≥ 4 (satisfaction, product, service, pricing) | `upsell` | High satisfaction in specific areas | Consider upselling or cross-selling opportunities |

### 3.2 AI-Enhanced Opportunity Identification

The AI scans feedback text for additional growth signals:

- Feature requests indicating engagement
- Expansion needs mentioned by customer
- Positive sentiment toward specific products/services
- References to additional business units or use cases

### 3.3 Opportunity Structure

Each opportunity includes:
- **Type**: Category (advocacy, upsell, cross-sell, expansion)
- **Description**: Specific opportunity explanation
- **Action**: Recommended next step

---

## 4. Growth Factor (NPS-Based)

The Growth Factor is a separate metric correlating NPS score ranges with expected business growth, based on industry research.

### 4.1 Growth Rate Lookup Table

| NPS Score Range | Growth Rate | Growth Factor |
|-----------------|-------------|---------------|
| 70-100 | 40% | 0.40 |
| 50-69 | 25% | 0.25 |
| 30-49 | 15% | 0.15 |
| 0-29 | 5% | 0.05 |
| Below 0 | 0% | 0.00 |

### 4.2 Interpretation

- **Growth Rate**: Expected revenue/business growth correlation
- **Growth Factor**: Decimal multiplier for calculations
- **Range**: The NPS band the score falls into

---

## 5. Fallback Behavior

When AI services are unavailable, the system uses pure rule-based analysis:

1. **Churn Risk**: Points-based scoring using keywords and NPS thresholds
2. **Risk Factors**: Basic identification from NPS and ratings only
3. **Growth Opportunities**: NPS ≥ 9 triggers advocacy opportunity
4. **Growth Factor**: Always uses lookup table (no AI dependency)

This ensures consistent baseline functionality regardless of AI availability.

---

## 6. LLM Provider Independence

The calculation methodology is **identical across LLM providers**:

| Component | Provider Dependency |
|-----------|---------------------|
| Points-based churn scoring | None (Python code) |
| Risk level conversion | None (Python code) |
| NPS override rules | None (Python code) |
| Growth Factor lookup | None (Python code) |
| Automatic risk/opportunity detection | None (Python code) |
| AI text analysis enhancement | Same prompts sent to OpenAI/Claude |

The only variation is in **how each AI interprets written feedback**, but the fundamental scoring framework remains constant.

---

## 7. Data Storage

Calculated values are stored on the `SurveyResponse` model:

| Field | Type | Description |
|-------|------|-------------|
| `churn_risk_score` | Float (0-10+) | Numeric risk score (influence-scaled in fallback path) |
| `churn_risk_level` | String | Minimal / Low / Medium / High |
| `churn_risk_factors` | JSON Array | List of risk factor strings |
| `account_risk_factors` | JSON Array | Detailed risk objects with severity |
| `growth_opportunities` | JSON Array | Growth opportunity objects |
| `growth_factor` | Float | Growth rate as decimal (0.0-0.4) |
| `growth_rate` | String | Growth rate as percentage |
| `growth_range` | String | NPS range band |
| `influence_weight` | Float | Respondent seniority multiplier (1.0–5.0); set at analysis time |

---

## 8. References

- **Source Code**: `ai_analysis.py`
- **Functions**:
  - `assess_churn_risk_fallback()` - Rule-based churn scoring
  - `identify_account_risk_factors()` - Risk factor identification
  - `identify_growth_opportunities()` - Opportunity detection
  - `calculate_growth_factor()` - NPS-to-growth lookup
  - `perform_comprehensive_analysis()` - AI-enhanced analysis orchestrator
