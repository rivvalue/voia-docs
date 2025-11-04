# AI Model Configuration Guide

This document explains how to configure OpenAI models for different parts of the VOÏA platform using environment variables.

## Environment Variables

### `AI_ANALYSIS_MODEL`
**Purpose:** Controls which OpenAI model is used for backend response analysis (sentiment, themes, churn risk, growth opportunities)

**Default:** `gpt-4o-mini` (cost-optimized)

**Options:**
- `gpt-4o-mini` - Cost-effective model for structured analysis tasks (-94% cost vs GPT-4o)
- `gpt-4o` - Premium model for maximum accuracy
- `gpt-3.5-turbo` - Legacy model (not recommended, more expensive than mini)

**Cost Impact:**
- Using `gpt-4o-mini`: **$72/month** for 200k responses
- Using `gpt-4o`: **$1,200/month** for 200k responses
- **Monthly savings: $1,128** (-94%)

**Recommended:** Keep as `gpt-4o-mini` unless you need absolute maximum accuracy for analysis tasks.

---

### `AI_CONVERSATION_MODEL`
**Purpose:** Controls which OpenAI model is used for customer-facing conversational surveys

**Default:** `gpt-4o` (premium customer experience)

**Options:**
- `gpt-4o` - Premium conversational quality (recommended for customer-facing)
- `gpt-4o-mini` - Cost-effective alternative (90% quality at 94% cost savings)

**Cost Impact:**
- Using `gpt-4o`: **$3,800/month** for 200k survey conversations
- Using `gpt-4o-mini`: **$585/month** for 200k survey conversations
- **Potential savings: $3,215/month** (-85%)

**Recommended:** Keep as `gpt-4o` for best customer experience, or switch to `gpt-4o-mini` after testing quality with your specific use cases.

---

## How to Set Environment Variables in Replit

1. **Open Secrets Manager:**
   - Click the lock icon (🔒) in the left sidebar
   - Or go to Tools → Secrets

2. **Add the secrets:**

   **For cost optimization (recommended starting point):**
   ```
   Key: AI_ANALYSIS_MODEL
   Value: gpt-4o-mini
   ```
   ```
   Key: AI_CONVERSATION_MODEL
   Value: gpt-4o
   ```

3. **Click "Add Secret"** for each one

4. **Restart your application** to apply changes

---

## Configuration Scenarios

### Scenario 1: Maximum Cost Savings (-77% total AI costs)
**Monthly Cost: $1,258 total operating cost**

```bash
AI_ANALYSIS_MODEL=gpt-4o-mini
AI_CONVERSATION_MODEL=gpt-4o-mini
```

✅ Best for: High-volume operations, budget-conscious deployments
⚠️ Test quality: Run pilot with 100 surveys to validate conversation quality

---

### Scenario 2: Balanced Approach (RECOMMENDED, -21% AI costs)
**Monthly Cost: $4,245 total operating cost**

```bash
AI_ANALYSIS_MODEL=gpt-4o-mini
AI_CONVERSATION_MODEL=gpt-4o
```

✅ Best for: Most deployments - premium customer experience, optimized backend costs
✅ Minimal risk: Backend analysis quality maintained, zero customer impact

---

### Scenario 3: Premium Everything (current baseline)
**Monthly Cost: $5,381 total operating cost**

```bash
AI_ANALYSIS_MODEL=gpt-4o
AI_CONVERSATION_MODEL=gpt-4o
```

✅ Best for: When cost is not a concern and maximum accuracy is required everywhere
⚠️ Expensive: Paying premium for backend tasks that mini handles equally well

---

## Staged Rollout Strategy (Recommended)

### Week 1: Test Analysis Optimization
```bash
AI_ANALYSIS_MODEL=gpt-4o-mini  # Switch to mini
AI_CONVERSATION_MODEL=gpt-4o   # Keep premium
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

## Cost Summary

| Configuration | Monthly AI Cost | Total Monthly Cost | Annual Cost | Savings vs Baseline |
|--------------|----------------|-------------------|-------------|---------------------|
| **Baseline (All GPT-4o)** | $5,009 | $5,381 | $64,574 | - |
| **Balanced (Recommended)** | $3,873 | $4,245 | $50,940 | **-21%** (-$13,634/year) |
| **Maximum Savings** | $885 | $1,258 | $15,096 | **-77%** (-$49,478/year) |

---

## Support

For questions or issues with model configuration:
1. Check Replit logs for OpenAI API errors
2. Verify secrets are set correctly in Secrets Manager
3. Ensure application was restarted after changing secrets
4. Review this document for recommended configurations

**Last Updated:** November 4, 2025
**Document Version:** 1.0
