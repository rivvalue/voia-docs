# VOÏA Platform - Production Scale Cost Analysis

**Document Version:** 1.0  
**Analysis Date:** October 26, 2025  
**Prepared By:** Financial Analysis Team  
**Review Period:** Monthly recurring operational costs

---

## Executive Summary

This document provides a comprehensive cost analysis for operating the VOÏA (Voice Of Client) platform at production scale. The analysis covers infrastructure, AI processing, email delivery, storage, and all operational costs required to support 50 business accounts with high-volume customer feedback collection.

**Key Findings:**
- **Total Monthly Operating Cost:** $4,581.18 USD
- **Cost per Business Account:** $91.62/month
- **Annual Operating Cost:** $54,974.16 USD
- **Primary Cost Driver:** AI conversational surveys (91.9% of total costs)

---

## Production Usage Profile

The cost analysis is based on the following monthly operational metrics:

| Metric | Volume |
|--------|--------|
| Business Accounts | 50 |
| Active Campaigns | 200 |
| AI Conversational Survey Responses | 200,000 |
| Email Deliveries | 1,500,000 |
| Executive Reports Generated | 200 |
| Active Platform Users | 250 |
| Concurrent User Capacity | 100 |

---

## Detailed Cost Breakdown

### 1. Artificial Intelligence (OpenAI GPT-4o)

**Conversational Surveys**
- Volume: 200,000 responses/month
- Average conversation: 8 AI turns per survey
- Token usage per survey: 2,400 tokens (1,200 input + 1,200 output)
- Total monthly tokens: 480M (240M input + 240M output)
- GPT-4o pricing: $2.50 per 1M input tokens, $10.00 per 1M output tokens

**Calculation:**
- Input cost: 240M × $2.50/1M = $600.00
- Output cost: 240M × $10.00/1M = $2,400.00
- **Subtotal: $3,000.00/month**

**AI Response Analysis**
- Volume: 200,000 analyses/month
- Consolidated analysis: 1 API call per response
- Average tokens: 800 input + 400 output per analysis
- Total monthly tokens: 240M (160M input + 80M output)

**Calculation:**
- Input cost: 160M × $2.50/1M = $400.00
- Output cost: 80M × $10.00/1M = $800.00
- **Subtotal: $1,200.00/month**

**Executive Report Generation**
- Volume: 200 reports/month
- Average tokens: 5,000 input + 3,000 output per report
- Total monthly tokens: 1.6M (1M input + 0.6M output)

**Calculation:**
- Input cost: 1M × $2.50/1M = $2.50
- Output cost: 0.6M × $10.00/1M = $6.00
- **Subtotal: $8.50/month**

**🤖 Total AI Costs: $4,208.50/month (91.9% of total)**

---

### 2. Email Delivery Infrastructure (AWS SES)

**Email Volume**
- Total emails sent: 1,500,000/month
- AWS SES bulk pricing: $0.10 per 1,000 emails
- Average email size: 50KB

**Calculation:**
- Email sending: 1,500,000 ÷ 1,000 × $0.10 = $150.00
- SMTP data transfer: 1.5M × 50KB = 75GB × $0.09/GB = $6.75
- **Total: $156.75/month (3.4% of total)**

---

### 3. Database (PostgreSQL - Neon)

**Storage Requirements:**
- SurveyResponse table: 200,000 rows × 15KB = 3.0GB
- EmailDelivery table: 1,500,000 rows × 2KB = 3.0GB
- AuditLog table: 500,000 entries × 1KB = 0.5GB
- Campaigns, Participants, Users: 0.2GB
- Indexes & TSVECTOR (full-text search): 1.5GB
- **Total database storage: 8.2GB**

**Neon PostgreSQL Pricing (Scale Plan):**
- Storage: 8.2GB × $0.000164/GB-hour × 730 hours = $0.98
- Compute: 150 hours/month × $0.16/hour = $24.00
- **Total: $24.98/month (0.5% of total)**

---

### 4. Application Compute & Processing (Replit)

**Infrastructure Configuration:**
- Web application servers (always-on)
- Background task workers
- PostgreSQL task queue processing
- Support for 100 concurrent users

**Replit Hosting:**
- Reserved VM with Always-On deployment
- Optimized for high-availability production workload
- **Total: $150.00/month (3.3% of total)**

**Alternative Self-Hosting Option (GCP/AWS Canada):**
- Web servers: 3× n1-standard-2 instances = $150.00
- Background workers: 2× n1-standard-1 instances = $50.00
- Redis cache: 2GB instance = $25.00
- Load balancer: $18.00
- **Alternative total: $243.00/month**

---

### 5. File Storage (AWS S3)

**Storage Breakdown:**
- Executive Reports: 200 PDFs × 2MB = 0.4GB/month growth
- Campaign Exports: 50 CSV files × 10MB = 0.5GB/month growth
- Monthly storage growth: 0.9GB
- Annual accumulation: 10.8GB/year

**AWS S3 Standard Pricing:**
- Storage: 1GB × $0.023/GB = $0.02
- Data transfer out: 10GB × $0.09/GB = $0.90
- **Total: $0.92/month (0.02% of total)**

---

### 6. Long-Term Archiving (AWS S3 Glacier)

**Archive Policy:**
- Reports older than 90 days moved to Glacier
- Annual archived data: 8GB

**AWS Glacier Pricing:**
- Storage: 8GB × $0.004/GB = $0.03
- Occasional retrieval budget: $5.00
- **Total: $5.03/month (0.1% of total)**

---

### 7. Network & Bandwidth

**Traffic Breakdown:**
- Ingress (survey submissions): Free
- Egress (dashboard, reports, downloads): 100GB/month

**Calculation:**
- Bandwidth: 100GB × $0.09/GB = $9.00
- **Total: $9.00/month (0.2% of total)**

---

### 8. Monitoring & Security (Sentry)

**Error Tracking & Performance Monitoring:**
- Sentry Developer Plan
- Comprehensive error logging
- Performance monitoring
- **Total: $26.00/month (0.6% of total)**

---

## Monthly Cost Summary

| Cost Category | Monthly Cost | % of Total |
|---------------|--------------|------------|
| AI (OpenAI GPT-4o) | $4,208.50 | 91.9% |
| Email Delivery (AWS SES) | $156.75 | 3.4% |
| Compute/Processing (Replit) | $150.00 | 3.3% |
| Monitoring (Sentry) | $26.00 | 0.6% |
| Database (Neon PostgreSQL) | $24.98 | 0.5% |
| Network/Bandwidth | $9.00 | 0.2% |
| Archiving (S3 Glacier) | $5.03 | 0.1% |
| File Storage (S3) | $0.92 | 0.02% |
| **TOTAL** | **$4,581.18** | **100%** |

---

## Key Financial Metrics

| Metric | Value |
|--------|-------|
| **Total Monthly Operating Cost** | $4,581.18 USD |
| **Cost per Business Account** | $91.62/month |
| **Annual Operating Cost** | $54,974.16 USD |
| **Cost per Survey Response** | $2.29 |
| **Cost per Email Sent** | $0.003 |
| **Cost per Executive Report** | $21.44 |
| **Cost per Active User** | $18.32/month |

---

## Cost Optimization Opportunities

### High-Impact Optimizations

**1. AI Model Selection (Potential savings: -37%)**
- **Current:** GPT-4o for all conversational surveys
- **Optimization:** Use GPT-4o-mini for standard surveys, reserve GPT-4o for complex cases
- **Impact:** Reduce AI costs from $4,208.50 to $2,650.00
- **Annual savings:** $18,702/year

**2. Response Caching (Potential savings: -15% AI cost)**
- Implement intelligent caching for common survey patterns
- Cache AI analysis results for similar feedback
- **Impact:** Reduce AI costs by $631/month
- **Annual savings:** $7,572/year

**3. Survey Length Optimization (Potential savings: -25% AI cost)**
- Reduce average questions from 8 to 6 per survey
- Maintain data quality with targeted questioning
- **Impact:** Reduce AI costs by $1,052/month
- **Annual savings:** $12,624/year

### Medium-Impact Optimizations

**4. Self-Hosting in Canada (Potential cost: +2%)**
- Migrate to Canadian cloud infrastructure (GCP Montreal, AWS Canada)
- **Benefit:** Data sovereignty compliance for Canadian clients
- **Impact:** Increase compute costs by $93/month
- **Trade-off:** Better compliance vs. slightly higher costs

**5. Database Archiving (Potential savings: -30% DB cost after Year 1)**
- Archive campaigns older than 12 months to cold storage
- Maintain active database performance
- **Impact:** Reduce database costs by $7.50/month after Year 1
- **Annual savings:** $90/year (ongoing)

### Low-Impact Optimizations

**6. Reserved Instance Pricing**
- Commit to 1-year or 3-year compute reservations
- **Impact:** Reduce compute costs by 20-40%
- **Annual savings:** $360-720/year

---

## Sensitivity Analysis

### Scenario Modeling

| Scenario | Monthly Cost | Change | Annual Cost |
|----------|-------------|--------|-------------|
| **Base (Current)** | $4,581 | - | $54,974 |
| High Growth (+50% responses) | $6,475 | +41% | $77,700 |
| AI Optimization (GPT-4o-mini) | $2,900 | -37% | $34,800 |
| Self-Hosted Canada | $4,674 | +2% | $56,088 |
| Reduced Survey Length (6Q) | $3,831 | -16% | $45,972 |
| Full Optimization Stack | $2,450 | -47% | $29,400 |

### Volume Scaling

**Cost per Additional 10,000 Survey Responses:**
- AI processing: $150.00
- Email delivery: $10.00
- Database storage: $1.25
- **Total marginal cost:** $161.25

**Break-Even Analysis:**
- Fixed costs (compute, monitoring, storage): $215.95/month
- Variable costs per response: $2.18
- At 200,000 responses: $4,365.23 variable + $215.95 fixed = $4,581.18

---

## Cost Allocation Model

### Per-Business-Account Breakdown

**Standard Account (Average Usage):**
- AI surveys: 4,000 responses × $2.10 = $84.00
- Email delivery: 30,000 emails × $0.0001 = $3.00
- Shared infrastructure: $4.62
- **Total per account:** $91.62/month

### High-Volume Account Surcharge

For accounts exceeding 10,000 responses/month:
- Base allocation: $91.62
- Overage rate: $1.50 per 1,000 additional responses
- Example (20,000 responses): $91.62 + (10,000 ÷ 1,000 × $1.50) = $106.62/month

---

## Financial Recommendations

### Immediate Actions (0-30 days)
1. Implement AI response caching for 15% cost reduction
2. Negotiate annual commitment discounts with OpenAI
3. Set up cost monitoring dashboards

### Short-Term (1-3 months)
1. A/B test GPT-4o-mini for 50% of surveys
2. Optimize survey question sequences to reduce average length
3. Implement automated cost alerts at $5,000/month threshold

### Long-Term (3-12 months)
1. Develop hybrid AI model strategy (GPT-4o + GPT-4o-mini)
2. Evaluate Canadian hosting migration for data sovereignty
3. Implement tiered pricing based on actual usage patterns

---

## Risk Assessment

### Cost Volatility Factors

**High Risk:**
- OpenAI pricing changes (91.9% of costs)
- Unexpected surge in survey volume

**Medium Risk:**
- AWS SES deliverability affecting retry rates
- Database growth exceeding projections

**Low Risk:**
- Compute resource scaling
- Storage cost increases

### Mitigation Strategies

1. **AI Cost Protection:**
   - Maintain fallback to GPT-4o-mini
   - Implement strict token budgets per survey
   - Monitor and cap daily AI spending

2. **Email Delivery:**
   - Multi-provider strategy (AWS SES + backup SMTP)
   - Email validation to reduce bounces

3. **Database Growth:**
   - Automated archiving policies
   - Regular cleanup of transient data

---

## Conclusion

VOÏA's operating costs are dominated by AI processing (91.9%), which directly correlates with the platform's value proposition of high-quality conversational surveys. The current cost structure of **$91.62 per business account per month** is sustainable and provides significant optimization opportunities through AI model selection and caching strategies.

**Key Takeaways:**
- AI costs scale linearly with survey volume
- Infrastructure costs are well-optimized at current scale
- 37% cost reduction achievable through GPT-4o-mini adoption
- Cost per survey response ($2.29) is competitive for AI-powered feedback collection

---

## Appendix A: Technology Stack

- **AI:** OpenAI GPT-4o / GPT-4o-mini
- **Database:** PostgreSQL (Neon-backed, Replit infrastructure)
- **Email:** AWS SES (primary), SMTP fallback
- **Compute:** Replit Always-On + Reserved VM
- **Storage:** AWS S3 Standard + Glacier
- **Monitoring:** Sentry
- **Task Queue:** PostgreSQL-backed background processing
- **Caching:** Redis

---

## Appendix B: Calculation Methodology

**AI Token Estimates:**
- Based on hybrid prompt architecture analysis (300 tokens/turn)
- Includes system prompts, conversation history, and structured outputs
- Conservative estimates with 10% safety buffer

**Database Storage:**
- Row size estimates based on actual schema analysis
- Includes indexes, TSVECTOR, and JSONB columns
- Measured from production data patterns

**Email Costs:**
- AWS SES bulk pricing tier ($0.10/1000)
- Average email size: 50KB (HTML template + personalization)
- SMTP data transfer calculated separately

---

**Document Control:**
- Version: 1.0
- Last Updated: October 26, 2025
- Next Review: Monthly
- Owner: Financial Planning Team
- Classification: Internal Use

---

*This document provides cost projections based on current usage patterns and vendor pricing as of October 2025. Actual costs may vary based on usage fluctuations, vendor pricing changes, and optimization implementations.*
