# VOÏA Scoring Formulas — Internal Reference

> **Internal — Not for distribution. Do not publish to the public documentation site or share with end users.**

This document captures the complete scoring methodology used by VOÏA's AI analysis pipeline. It is intended for engineering and product teams who need to understand or audit the formulas without reading source code. All values are derived directly from `ai_analysis.py` and `data_storage.py`.

---

## 1. Seniority Tier → Influence Weight Multiplier

Every survey respondent is assigned an influence weight based on their organisational seniority. This multiplier scales their contribution to churn risk scores and growth opportunity scores throughout the platform.

| Seniority Tier | Tier Key      | Influence Multiplier |
|----------------|---------------|----------------------|
| C-Level        | `c_level`     | 5.0×                 |
| VP / Director  | `vp_director` | 3.0×                 |
| Manager        | `manager`     | 2.0×                 |
| Team Lead      | `team_lead`   | 1.5×                 |
| End User       | `end_user`    | 1.0×                 |
| Unknown / Default | `default`  | 1.0×                 |

**Fallback behaviour:** If a respondent has no associated participant record, no role field, or an unrecognised role string, the system defaults to `1.0×` (End User equivalent). The role string is mapped to a tier key via `_map_role_to_tier()` in `prompt_template_service.py`.

---

## 2. Churn Risk Score Formula

The churn risk score measures the probability a customer may churn. It is computed in two ways depending on whether the LLM path or the rule-based fallback path is active. Both honour influence weighting.

**Cap behaviour summary:** The rule-based fallback path applies **no cap** — high-influence respondents can produce scores well above 10. The AI-enhanced path produces a raw score bounded 0–10 by the prompt, and only the NPS floor values (used to override an under-estimated AI score) are capped at 10 via `min(10, ...)`. See Sections 2.1 and 2.2 respectively.

### 2.1 Rule-Based (Fallback) Calculation

Base points are accumulated from the following signals. Each signal's base is independently multiplied by the respondent's `influence_weight` and rounded before summing. **No cap is applied** — the raw sum is stored and returned directly.

| Signal                                    | Base Points | Scaled contribution                             |
|-------------------------------------------|-------------|-------------------------------------------------|
| Churn keywords detected in feedback text  | 5           | `round(5 × influence_weight)`                   |
| NPS score ≤ 6 (Detractor / Passive)       | 3           | `round(3 × influence_weight)`                   |

**Final score formula:**

```
risk_score = round(5 × influence_weight)   # if churn keywords present
           + round(3 × influence_weight)   # if NPS ≤ 6
```

> There is **no hard cap at 10** in this path. A C-level respondent (influence_weight = 5.0) who triggers both signals will produce `round(25) + round(15) = 40`. The cap of 10 only applies to the influence-scaled NPS floors used in the AI-enhanced path (Section 2.2).

### 2.2 AI-Enhanced (Primary) Calculation

When the LLM is available, the AI produces an initial `risk_score` (0–10) and `risk_level`. The `enhance_analysis_with_rules()` function then applies **NPS-based floors** scaled by influence weight to ensure low-NPS respondents are never under-scored:

| NPS Range | Base Floor | Scaled Floor Formula          | Rule Effect                                     |
|-----------|------------|-------------------------------|-------------------------------------------------|
| NPS ≤ 3   | 5          | `min(10, round(5 × influence_weight))` | Score raised to floor; level set to `High`  |
| NPS 4–6   | 3          | `min(10, round(3 × influence_weight))` | Score raised to floor if below; level raised from `Minimal` to `Medium` |

---

## 3. Churn Risk Level Thresholds

### 3.1 Per-Respondent Risk Score → Level Mapping

The numeric `risk_score` is converted to a categorical label using the following deterministic thresholds (applied in both the rule-based fallback and as a floor-enforcement override in the AI-enhanced path):

| Risk Score Range | Risk Level |
|------------------|------------|
| 0                | Minimal    |
| 1–2              | Low        |
| 3–4              | Medium     |
| ≥ 5              | High       |

`Critical` is **not** assigned by the deterministic scoring functions. It can be returned directly by the LLM in the AI-enhanced path when the model judges the feedback to warrant it, and the system persists and sorts that value. Dashboard queries treat `High` and `Critical` equivalently in the high-risk account filter.

### 3.2 Company-Level Aggregate Risk (NPS-based)

A separate `Critical` threshold applies when computing risk levels for company or tenure cohort aggregations using the company-level NPS score (distinct from the per-respondent churn risk score above):

| Company / Cohort NPS Range | Risk Level |
|----------------------------|------------|
| ≤ −50                      | Critical   |
| −50 < NPS ≤ −20            | High       |
| −20 < NPS ≤ 20             | Medium     |
| > 20                       | Low / Minimal |

---

## 4. AI-Enhanced Account Risk Factors and Severity Weights

The AI identifies account-specific risk factors and assigns each a severity label. The severity label is later consumed by the health balance scoring (see Section 6).

### 4.1 Canonical Risk Factor Types

| Canonical Type       | Example Source Strings                                      |
|----------------------|-------------------------------------------------------------|
| `pricing_concern`    | pricing concern, price sensitivity, cost issues, expensive  |
| `service_issue`      | service issue, poor service, support problem                |
| `product_problem`    | product issues, quality issue, functionality                |
| `competitor_risk`    | competitor mention, considering alternatives                |
| `satisfaction_risk`  | dissatisfaction, unhappy customer, low_satisfaction         |
| `relationship_risk`  | communication issue, trust issue, poor relationship         |
| `contract_risk`      | renewal risk, contract concerns                             |
| `churn_risk`         | retention risk, at risk, likely to leave                    |
| `poor_ratings`       | low ratings, poor performance                               |

### 4.2 Severity Weight Table

| Severity Label | Numeric Weight |
|----------------|----------------|
| Low            | 0.5            |
| Medium         | 1.0            |
| High           | 2.0            |
| Critical       | 3.0            |

These weights are used in the health balance ratio formula (see Section 6).

---

## 5. Growth Factor Lookup Table

The growth factor is a deterministic lookup driven solely by the respondent's NPS score. No AI call is made for this calculation.

| NPS Score Range | Growth Rate | Growth Factor |
|-----------------|-------------|---------------|
| < 0             | 0%          | 0.00          |
| 0 – 29          | 5%          | 0.05          |
| 30 – 49         | 15%         | 0.15          |
| 50 – 69         | 25%         | 0.25          |
| 70 – 100        | 40%         | 0.40          |
| Invalid (other) | 0%          | 0.00          |

The result is stored on the `SurveyResponse` model as `growth_factor` (float), `growth_rate` (string, e.g. `"40%"`), and `growth_range` (string, e.g. `"70-100"`).

---

## 6. Growth Opportunity Weights

When scoring account health balance, each growth opportunity is weighted by business impact type. Unrecognised types default to `1.0`.

| Opportunity Type        | Weight |
|-------------------------|--------|
| Upsell                  | 3.0    |
| Expansion               | 3.0    |
| Cross-sell / Cross sell  | 2.0    |
| Referral                | 1.5    |
| Advocacy                | 1.5    |
| Renewal                 | 1.0    |
| Unknown / Other         | 1.0    |

---

## 7. Health Balance Ratio Formula

The health balance ratio measures the overall account posture by comparing weighted opportunity potential against weighted risk exposure.

### 7.1 Score Calculation

```
Opportunity Score = Σ (opportunity_weight × count × influence_weight)
Risk Score        = Σ (severity_weight × count × influence_weight)

Health Ratio = Opportunity Score / (Opportunity Score + Risk Score)
```

- When `Opportunity Score + Risk Score = 0` (no data), `Health Ratio` defaults to `0.5` (neutral).
- `influence_weight` should only be passed when processing a single raw respondent. For company-level aggregated data, each `count` field already incorporates influence-weighted summing — pass `influence_weight = 1.0` to avoid double-counting.

### 7.2 Classification Bands

| Health Ratio       | Classification      | Label          |
|--------------------|---------------------|----------------|
| ≥ 0.65             | `opportunity_heavy` | High Potential |
| 0.35 – 0.64 (0.35 ≤ ratio < 0.65) | `balanced` | Stable |
| ≤ 0.35             | `risk_heavy`        | At-Risk        |

> Boundary values: `0.65` is classified as `opportunity_heavy` (not balanced) and `0.35` is classified as `risk_heavy` (not balanced). This matches the `>=` / `<=` comparisons in `calculate_weighted_account_balance()`.

---

## Source Files

| File              | Contains                                                   |
|-------------------|------------------------------------------------------------|
| `ai_analysis.py`  | `INFLUENCE_TIER_WEIGHTS`, `calculate_growth_factor()`, `assess_churn_risk_fallback()`, `enhance_analysis_with_rules()`, `perform_consolidated_ai_analysis()` |
| `data_storage.py` | `OPPORTUNITY_WEIGHTS`, `RISK_SEVERITY_WEIGHTS`, `HEALTH_RATIO_HIGH_POTENTIAL`, `HEALTH_RATIO_RISK_HEAVY`, `calculate_weighted_account_balance()`, `normalize_risk_factor_type()` |

---

*Last updated: April 2026. Update this document whenever scoring constants or formula logic change in source.*
