# Company Trend Analytics - Architecture & Design Document

**Document Version**: 1.0  
**Date**: October 25, 2025  
**Status**: Design Phase - Awaiting Architectural Decisions  
**Author**: VOÏA Development Team  
**Reviewers**: Solution Architect, Business Analyst  

---

## 1. Feature Description

### 1.1 Business Objective

Enable business account administrators to visualize company-level metric trends across multiple completed campaigns, tracking how specific companies evolve over time in their relationship with the business account.

### 1.2 Target Metrics

Track 8 metric categories per company per campaign:

1. **Participation Metrics**:
   - Total invitations sent
   - Total responses received
   - Participation rate (%)

2. **NPS Metrics**:
   - NPS score
   - Promoters count
   - Passives count
   - Detractors count

3. **Rating Metrics** (1-5 scale):
   - Average satisfaction rating
   - Average pricing rating
   - Average service rating
   - Average product value rating

4. **Sentiment Distribution** (percentages):
   - Positive sentiment %
   - Negative sentiment %
   - Neutral sentiment %

5. **Churn Risk Distribution** (percentages):
   - High risk %
   - Medium risk %
   - Low risk %
   - Minimal risk %

### 1.3 User Stories

**As a** business account administrator  
**I want to** view how a specific company's NPS, ratings, and risk levels have evolved across campaigns  
**So that** I can identify trends, detect engagement drops, and take proactive actions

**As a** business account administrator  
**I want to** compare Company A's Q1 vs Q2 vs Q3 performance  
**So that** I can measure relationship health over time

**As a** business account administrator  
**I want to** see when a company stopped responding to surveys  
**So that** I can investigate potential relationship issues early

### 1.4 Proposed Solution

Implement a dedicated `CompanyTrendSnapshot` table that stores company-level aggregated metrics for each completed campaign, enabling efficient time-series queries and trend visualization.

---

## 2. Feature Analysis

### 2.1 Current State Assessment

**Existing Infrastructure**:
- ✅ `/api/company_trends` endpoint exists (routes.py:2178)
- ✅ `CampaignKPISnapshot` model stores campaign-level historical data
- ✅ `SurveyResponse` table contains all required raw metrics
- ✅ PostgreSQL task queue for background processing

**Current Limitations**:
- ❌ `/api/company_trends` aggregates monthly NPS only (not campaign-based)
- ❌ No company-level granularity in `CampaignKPISnapshot`
- ❌ No dedicated table for company-specific trend data
- ❌ Cannot query "Company X trends across all campaigns" efficiently

### 2.2 Architectural Approach

**Decision**: Dedicated `CompanyTrendSnapshot` table (vs extending `CampaignKPISnapshot` JSON fields)

**Rationale**:
1. **Separation of Concerns**: Campaign-level KPIs vs company-level trends serve different analytical use cases
2. **Query Performance**: Simple `WHERE company_id = X ORDER BY campaign_date` vs parsing JSON arrays
3. **Schema Evolution**: Easy to add new company-specific metrics without impacting campaign reports
4. **Scalability**: Indexed, partitionable table handles 1000 companies × 100 campaigns (100K records) efficiently

### 2.3 Data Flow Design

```
Campaign Status: Completed
    ↓
Background Task Queue (PostgreSQL)
    ↓
Single Atomic Transaction:
    1. Lock campaign data
    2. Aggregate metrics once (single query from SurveyResponse)
    3. Generate CampaignKPISnapshot (campaign-level)
    4. Generate CompanyTrendSnapshots (company-level, same data)
    5. Mark both with matching snapshot_version
    6. Commit transaction (all-or-nothing)
    ↓
Snapshots Available for Reporting
```

### 2.4 Proposed Schema

```sql
CREATE TABLE company_trend_snapshots (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Multi-Tenant Identity
    business_account_id INTEGER NOT NULL REFERENCES business_accounts(id),
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id),  -- PENDING: Table creation
    company_name VARCHAR(200) NOT NULL,  -- Denormalized display label
    
    -- Campaign Context
    campaign_completion_date DATE NOT NULL,
    snapshot_version VARCHAR(10) NOT NULL DEFAULT 'v1.0',
    
    -- Response Status (distinguishes invited vs responded)
    response_status VARCHAR(30) NOT NULL,  -- ENUM: 'responded', 'invited_no_response', 'not_invited'
    
    -- Participation Metrics (Authoritative)
    total_invitations INTEGER NOT NULL DEFAULT 0,
    total_responses INTEGER NOT NULL DEFAULT 0,
    participation_rate FLOAT,  -- (responses / invitations) * 100
    
    -- NPS Metrics (NULL when zero responses)
    nps_score FLOAT,
    promoters_count INTEGER DEFAULT 0,
    passives_count INTEGER DEFAULT 0,
    detractors_count INTEGER DEFAULT 0,
    
    -- Rating Metrics (1-5 scale, NULL when zero responses)
    avg_satisfaction_rating FLOAT,
    avg_pricing_rating FLOAT,
    avg_service_rating FLOAT,
    avg_product_value_rating FLOAT,
    
    -- Sentiment Distribution (percentages, NULL when zero responses)
    sentiment_positive_pct FLOAT DEFAULT 0.0,
    sentiment_negative_pct FLOAT DEFAULT 0.0,
    sentiment_neutral_pct FLOAT DEFAULT 0.0,
    
    -- Churn Risk Distribution (percentages, NULL when zero responses)
    churn_risk_high_pct FLOAT DEFAULT 0.0,
    churn_risk_medium_pct FLOAT DEFAULT 0.0,
    churn_risk_low_pct FLOAT DEFAULT 0.0,
    churn_risk_minimal_pct FLOAT DEFAULT 0.0,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Multi-Tenant Unique Constraint
    UNIQUE (business_account_id, campaign_id, company_id),
    
    -- Indexes for Performance
    INDEX idx_company_trends_company (business_account_id, company_id, campaign_completion_date),
    INDEX idx_company_trends_campaign (campaign_id)
);
```

### 2.5 Example API Response

**Endpoint**: `GET /api/companies/{company_id}/trends?business_account_id={id}`

```json
{
  "company_id": 123,
  "company_name": "Acme Corporation",
  "business_account_id": 5,
  "trends": [
    {
      "campaign_id": 10,
      "campaign_name": "Q1 2024 NPS Survey",
      "campaign_completion_date": "2024-03-31",
      "snapshot_version": "v20240401_143000",
      "response_status": "responded",
      "participation": {
        "total_invitations": 20,
        "total_responses": 15,
        "participation_rate": 75.0
      },
      "nps": {
        "score": 50,
        "promoters": 8,
        "passives": 5,
        "detractors": 2
      },
      "ratings": {
        "satisfaction": 4.2,
        "pricing": 3.8,
        "service": 4.5,
        "product_value": 4.1
      },
      "sentiment": {
        "positive_pct": 60.0,
        "negative_pct": 20.0,
        "neutral_pct": 20.0
      },
      "churn_risk": {
        "high_pct": 10.0,
        "medium_pct": 15.0,
        "low_pct": 50.0,
        "minimal_pct": 25.0
      }
    },
    {
      "campaign_id": 11,
      "campaign_name": "Q2 2024 NPS Survey",
      "campaign_completion_date": "2024-06-30",
      "response_status": "invited_no_response",
      "participation": {
        "total_invitations": 20,
        "total_responses": 0,
        "participation_rate": 0.0
      },
      "nps": null,
      "ratings": null,
      "sentiment": null,
      "churn_risk": null
    }
  ]
}
```

---

## 3. Risk Assessment

### 3.1 Risk #1: Company Identity Under Multi-Tenancy

**Risk Level**: 🔴 **CRITICAL - NOT MITIGATED**

**Problem Statement**:
Within a single business account, company name variations create duplicate trend lines instead of unified longitudinal data.

**Example Scenario**:
```
Business Account: "Consulting Firm A"
Campaign 1: "Acme Corporation" → 15 responses, NPS=50
Campaign 2: "ACME CORP" → 12 responses, NPS=55
Campaign 3: "Acme Corp." → 18 responses, NPS=60
```

**Current Risk**:
- Using `company_name` alone creates 3 separate trend lines
- Cannot join/merge historical data across name variations
- Trend charts fragment instead of showing single company evolution

**Business Analyst's Proposed Mitigation**:
- Scope all calculations by `business_account_id` (prevents cross-tenant collisions)
- Argument: "Acme Corp in Account A vs Account B are different entities"

**Architect's Assessment**: ⚠️ **PARTIALLY MITIGATED**
- ✅ Solves: Cross-tenant collision risk
- ❌ Doesn't solve: Intra-tenant name variation fragmentation

**Required Solution**:
1. Create `Companies` dimension table:
   ```sql
   CREATE TABLE companies (
       id SERIAL PRIMARY KEY,
       business_account_id INTEGER NOT NULL REFERENCES business_accounts(id),
       canonical_name VARCHAR(200) NOT NULL,  -- Normalized: "acme corporation"
       display_name VARCHAR(200) NOT NULL,    -- User-facing: "Acme Corporation"
       created_at TIMESTAMP NOT NULL DEFAULT NOW(),
       UNIQUE (business_account_id, canonical_name)
   );
   ```

2. Implement normalization logic:
   - Convert to lowercase
   - Remove legal suffixes (Inc., Corp., LLC, Ltd.)
   - Trim whitespace
   - Remove punctuation

3. Update `CompanyTrendSnapshot.company_id` as foreign key to `Companies.id`

**Impact If Not Resolved**:
- Trend data fragments across campaigns
- Longitudinal analysis impossible
- Business value severely degraded

**Status**: 🔴 **BLOCKING IMPLEMENTATION**

---

### 3.2 Risk #2: Zero-Response Company Handling

**Risk Level**: 🟠 **HIGH - NOT MITIGATED**

**Problem Statement**:
Companies invited but not responding create ambiguous trend gaps that prevent detecting engagement drops.

**Example Scenario**:
```
Q1 Campaign: Acme Corp → 20 invited, 15 responded (75% participation, NPS=50)
Q2 Campaign: Acme Corp → 20 invited, 0 responded (0% participation, NPS=NULL)
Q3 Campaign: Acme Corp → 20 invited, 12 responded (60% participation, NPS=45)
```

**Business Analyst's Proposed Mitigation**:
- Skip zero-response companies (gaps are acceptable in time-series data)
- Argument: "Ratings are analyzed against time, empty responses don't matter"

**Architect's Assessment**: ❌ **REJECTED - CRITICAL BUSINESS SIGNALS LOST**

**Why Zero-Response Persistence is Required**:

1. **Participation Rate Trend Visibility**:
   - WITH zero-response: 75% → **0%** → 60% (clear engagement drop in Q2)
   - WITHOUT zero-response: 75% → [gap] → 60% (unclear what happened)

2. **Distinguish Data Gaps**:
   - "Company wasn't invited to Q2" (expected gap)
   - "Company invited but zero responses" (red flag for churn risk)

3. **Early Warning System**:
   - Participation drop from 75% to 0% = actionable insight
   - Missing data point = no signal to investigate

**Required Solution**:
1. Add `response_status` field to schema:
   - `'responded'`: Company has >= 1 response
   - `'invited_no_response'`: Company invited but 0 responses
   - `'not_invited'`: Company not part of this campaign

2. Persist zero-response companies with:
   - `total_invitations` > 0
   - `total_responses` = 0
   - `participation_rate` = 0.0
   - All metric fields (NPS, ratings, sentiment, risk) = NULL

3. Update frontend visualization to handle NULL metrics:
   - Show gap in metric trend charts
   - Highlight participation rate drop to 0%
   - Display tooltip: "Invited but no response"

**Impact If Not Resolved**:
- Lose critical engagement drop signals
- Cannot differentiate expected gaps from concerning behavior
- Churn risk detection delayed or missed

**Status**: 🟠 **BLOCKING IMPLEMENTATION**

---

### 3.3 Risk #3: Snapshot Consistency

**Risk Level**: 🟡 **MEDIUM - PARTIALLY MITIGATED**

**Problem Statement**:
If `CampaignKPISnapshot` and `CompanyTrendSnapshot` are generated separately, data drift can occur if second generation fails.

**Example Failure Scenario**:
```
Campaign Status → Completed
    ↓
Task 1: Generate CampaignKPISnapshot
    ✅ Commits successfully (NPS=50)
    ↓
Task 2: Generate CompanyTrendSnapshots (triggered by Task 1)
    ❌ Fails (DB timeout, memory error)
```

**Result**:
- Campaign-level snapshot exists (NPS=50)
- Company-level snapshots missing
- Reports show conflicting data

**Business Analyst's Proposed Mitigation**:
- Sequential triggering: CampaignKPISnapshot completion triggers CompanyTrendSnapshot creation
- Single source of truth (both derive from same campaign state)

**Architect's Assessment**: ⚠️ **PARTIALLY MITIGATED - FAILURE WINDOW EXISTS**
- ✅ Sequential triggering prevents timing-based data drift
- ❌ Leaves failure window where first succeeds but second fails

**Required Solution**:
1. **Single Atomic Background Job**:
   ```python
   def generate_campaign_snapshots(campaign_id):
       """Atomic task generates both snapshot types"""
       with db.session.begin_nested():
           # 1. Aggregate metrics once
           metrics = aggregate_campaign_metrics(campaign_id)
           
           # 2. Generate both snapshots
           campaign_snapshot = create_campaign_snapshot(campaign_id, metrics)
           company_snapshots = create_company_snapshots(campaign_id, metrics)
           
           # 3. Same snapshot_version
           version = generate_version_id()
           campaign_snapshot.snapshot_version = version
           for snapshot in company_snapshots:
               snapshot.snapshot_version = version
           
           # 4. All-or-nothing commit
           db.session.commit()
   ```

2. **Idempotent Retry Logic**:
   - Use `ON CONFLICT (campaign_id, company_id) DO UPDATE`
   - Safe to retry entire task if failure occurs
   - Track retry attempts and alert on repeated failures

3. **Compensating Logic for Regeneration**:
   - If campaign data is recalculated, delete old snapshots
   - Generate new snapshots with incremented version
   - Maintain audit trail of regeneration events

**Impact If Not Resolved**:
- Data inconsistency between campaign and company reports
- User confusion when numbers don't match
- Difficult to diagnose and repair inconsistent states

**Status**: 🟡 **REQUIRES IMPLEMENTATION REFINEMENT**

---

### 3.4 Risk #4: Performance Impact on Live Users

**Risk Level**: 🟡 **MEDIUM - NOT DEFINED**

**Problem Statement**:
Snapshot generation must not degrade performance for concurrent user operations.

**Business Requirement**:
"Process must run with no disturbance or load on real-time tasks and functionalities performed by connected end users."

**Architect's Assessment**: ⚠️ **PERFORMANCE SAFEGUARDS UNDEFINED**

**Missing Specifications**:

1. **Processing Time Estimates**:
   - 100 responses, 10 companies → ??? seconds
   - 1,000 responses, 50 companies → ??? seconds
   - 10,000 responses, 200 companies → ??? seconds

2. **Resource Consumption**:
   - CPU usage during snapshot generation?
   - Database connections consumed?
   - Memory footprint?
   - Impact on query latency for concurrent users?

3. **Queue Configuration**:
   - Task priority level (lower than user requests?)
   - Concurrency limit (max simultaneous snapshot jobs?)
   - Rate limiting (max jobs per minute?)
   - Timeout thresholds?

4. **User Experience**:
   - When are trend charts available after campaign completion?
   - Loading states during background processing?
   - Error handling and retry visibility?

**Required Solution**:

1. **Benchmark Processing Time**:
   - Test with realistic campaign sizes (100, 500, 1000+ responses)
   - Measure CPU, memory, DB connection usage
   - Identify performance bottlenecks

2. **Define Queue Limits**:
   ```python
   SNAPSHOT_QUEUE_CONFIG = {
       'priority': 'low',  # Below user request priority
       'max_concurrent': 2,  # Max 2 snapshot jobs simultaneously
       'timeout': 300,  # 5 minute timeout
       'retry_limit': 3,
       'backoff': 'exponential'
   }
   ```

3. **Implement Resource Monitoring**:
   - Track queue lag (time from campaign completion to snapshot availability)
   - Alert on queue backlog exceeding threshold
   - Monitor DB connection pool saturation

4. **Back-Pressure Mechanisms**:
   - If queue depth > 10, delay new snapshot tasks
   - Rate limit to max 20 snapshot generations per minute
   - Prioritize user-facing requests over background tasks

**Impact If Not Resolved**:
- Potential performance degradation during peak campaign completions
- Database connection pool exhaustion
- User experience impacted by slow response times

**Status**: 🟡 **REQUIRES PERFORMANCE TESTING & CONFIGURATION**

---

## 4. Open Architectural Decisions

### 4.1 Decision #1: Company Identity Model

**Question**: How should we model company identity within a business account?

**Options**:

**Option A: Use Participant.id as Company Identifier**
- Pros: No new table, reuse existing data
- Cons: Participants are individuals, not companies; semantic mismatch
- Risk: Confusing data model, difficult to explain

**Option B: Create Dedicated Companies Dimension Table** ⭐ **RECOMMENDED**
- Pros: Clean separation, proper normalization, extensible for company attributes
- Cons: Requires new table and migration logic
- Schema:
  ```sql
  CREATE TABLE companies (
      id SERIAL PRIMARY KEY,
      business_account_id INTEGER NOT NULL,
      canonical_name VARCHAR(200) NOT NULL,
      display_name VARCHAR(200) NOT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT NOW(),
      UNIQUE (business_account_id, canonical_name)
  );
  ```

**Required**: Choose Option A or B

**Impact**: Blocks schema finalization and implementation

---

### 4.2 Decision #2: Zero-Response Persistence

**Question**: Should we persist companies with zero responses in CompanyTrendSnapshot?

**Options**:

**Option A: Skip Zero-Response Companies**
- Pros: Smaller table, simpler queries
- Cons: Lose participation rate trends, cannot detect engagement drops
- Business Impact: Critical signals missed

**Option B: Persist Zero-Response Companies** ⭐ **RECOMMENDED**
- Pros: Complete participation rate trends, early warning system
- Cons: Larger table, requires NULL handling in frontend
- Implementation: Add `response_status` field, persist with NULL metrics

**Required**: Choose Option A or B

**Impact**: Affects business value and analytical capabilities

---

### 4.3 Decision #3: Snapshot Deletion Policy

**Question**: What happens to snapshots when a campaign is deleted?

**Options**:

**Option A: CASCADE Delete (Hard Delete)**
- Behavior: `ON DELETE CASCADE` - snapshots deleted with campaign
- Pros: Clean database, no orphaned data
- Cons: Historical trend data lost permanently
- Use Case: Development/testing environments

**Option B: Soft Delete (Mark as Deleted)** ⭐ **RECOMMENDED**
- Behavior: Add `deleted_at` field, mark snapshots as deleted
- Pros: Preserves historical data, allows trend continuity
- Cons: Requires query filters to exclude deleted snapshots
- Use Case: Production environments with audit requirements

**Required**: Choose Option A or B

**Impact**: Affects data retention and regulatory compliance

---

### 4.4 Decision #4: Data Source Priority

**Question**: Where should company metrics be aggregated from?

**Options**:

**Option A: Raw SurveyResponse Aggregation** ⭐ **RECOMMENDED**
- Source: Query `SurveyResponse` table grouped by `campaign_id` + `company_id`
- Pros: Most accurate, single source of truth
- Cons: More complex query
- Query:
  ```sql
  SELECT 
      campaign_id,
      company_id,
      COUNT(*) as total_responses,
      AVG(nps_score) as avg_nps,
      AVG(satisfaction_rating) as avg_satisfaction,
      -- ... more aggregations
  FROM survey_responses
  WHERE campaign_id = ?
  GROUP BY campaign_id, company_id
  ```

**Option B: Derive from CampaignKPISnapshot JSON**
- Source: Parse `CampaignKPISnapshot.company_nps_breakdown` JSON field
- Pros: Faster (data pre-aggregated)
- Cons: Assumes JSON structure exists and is complete
- Risk: JSON schema may not include all 8 metric categories

**Required**: Choose Option A or B

**Impact**: Affects accuracy and query complexity

---

## 5. Implementation Roadmap

### 5.1 Prerequisites (BLOCKING)

**Must complete before implementation**:

1. ✅ **Resolve Decision #1**: Choose company identity model (Participant.id vs Companies table)
2. ✅ **Resolve Decision #2**: Zero-response persistence policy
3. ✅ **Resolve Decision #3**: Snapshot deletion policy (CASCADE vs soft-delete)
4. ✅ **Resolve Decision #4**: Data source priority (raw vs JSON)

### 5.2 Phase 1: Foundation (Estimated 4 hours)

**Tasks**:
1. Create Companies dimension table (if Decision #1 = Option B)
2. Implement company name normalization logic
3. Migrate existing company_name data to Companies table
4. Add foreign key relationships

**Deliverables**:
- `companies` table with normalized data
- Migration script with rollback capability
- Unit tests for normalization logic

### 5.3 Phase 2: Schema Implementation (Estimated 2 hours)

**Tasks**:
1. Create `company_trend_snapshots` table with final schema
2. Add indexes for query performance
3. Configure cascade/soft-delete behavior (based on Decision #3)
4. Add database constraints and validations

**Deliverables**:
- Production-ready table schema
- Database migration script
- Schema documentation

### 5.4 Phase 3: Background Task Implementation (Estimated 3 hours)

**Tasks**:
1. Implement single atomic snapshot generation task
2. Add metrics aggregation logic (based on Decision #4)
3. Implement idempotent upsert with retry logic
4. Add zero-response company handling (based on Decision #2)
5. Implement snapshot versioning system

**Deliverables**:
- `generate_campaign_snapshots(campaign_id)` background task
- Unit tests with mock data
- Integration tests with real campaign data

### 5.5 Phase 4: API Development (Estimated 2 hours)

**Tasks**:
1. Create `/api/companies/{company_id}/trends` endpoint
2. Implement multi-tenant security (business_account_id scoping)
3. Add query filters (date range, metric type)
4. Implement pagination for large datasets

**Deliverables**:
- REST API endpoint with Swagger documentation
- Integration tests for API
- Security audit passed

### 5.6 Phase 5: Frontend Visualization (Estimated 2 hours)

**Tasks**:
1. Create Chart.js multi-line trend chart component
2. Implement NULL metric handling (gaps in charts)
3. Add participation rate visualization
4. Implement zero-response highlighting

**Deliverables**:
- Interactive trend chart UI
- Responsive mobile layout
- User documentation

### 5.7 Phase 6: Performance Testing (Estimated 2 hours)

**Tasks**:
1. Benchmark snapshot generation at scale (1000+ responses)
2. Load test concurrent snapshot jobs
3. Measure database connection pool usage
4. Configure queue limits and rate limiting

**Deliverables**:
- Performance test report
- Queue configuration tuned for production
- Monitoring dashboards for queue lag

### 5.8 Phase 7: Production Deployment (Estimated 1 hour)

**Tasks**:
1. Deploy database migrations
2. Deploy background task updates
3. Deploy API endpoints
4. Deploy frontend components
5. Monitor for 24 hours

**Deliverables**:
- Production deployment complete
- Monitoring active
- Incident response plan documented

---

## 6. Success Criteria

### 6.1 Functional Requirements

- ✅ Company trend data persists for all completed campaigns
- ✅ Zero-response companies tracked with participation rate = 0%
- ✅ All 8 metric categories calculated correctly
- ✅ Multi-tenant isolation enforced (no cross-account data leakage)
- ✅ API returns trends sorted by campaign completion date
- ✅ Frontend charts display NULL metrics as gaps (not zeros)

### 6.2 Performance Requirements

- ✅ Snapshot generation completes within 5 minutes for 1000 responses
- ✅ No more than 2 concurrent snapshot jobs running simultaneously
- ✅ Zero impact on P95 latency for user-facing requests during snapshot generation
- ✅ Database connection pool usage stays below 80% during peak load
- ✅ Queue lag (campaign completion → snapshot available) < 10 minutes

### 6.3 Data Quality Requirements

- ✅ Zero data drift between CampaignKPISnapshot and CompanyTrendSnapshot
- ✅ Snapshot version numbers consistent across related snapshots
- ✅ Idempotent retry logic prevents duplicate snapshots
- ✅ Company name normalization produces consistent company_id assignments

---

## 7. Appendix

### 7.1 Related Models

**Existing Tables**:
- `campaigns`: Campaign metadata and lifecycle
- `campaign_kpi_snapshots`: Campaign-level aggregated metrics
- `survey_responses`: Individual survey response records
- `campaign_participants`: Participant invitation tracking
- `participants`: Participant master data

**New Tables (Proposed)**:
- `companies`: Company dimension with normalized names
- `company_trend_snapshots`: Company-level metrics per campaign

### 7.2 References

- VOÏA System Architecture: `replit.md`
- Campaign Lifecycle Management: `campaign_routes.py`
- Snapshot Generation: `data_storage.py::calculate_segmentation_analytics()`
- Background Task Queue: `postgres_task_queue.py`

### 7.3 Glossary

- **Company Identity**: Stable identifier for a company within a business account
- **Snapshot**: Immutable point-in-time aggregated metrics
- **Snapshot Version**: Unique identifier tracking regeneration events
- **Response Status**: Flag indicating whether company responded, was invited, or not part of campaign
- **Participation Rate**: (total_responses / total_invitations) × 100
- **Canonical Name**: Normalized company name for deduplication (lowercase, no punctuation)
- **Display Name**: User-facing company name preserving original formatting

---

**Document Status**: 🔴 **AWAITING ARCHITECTURAL DECISIONS**

**Next Steps**: Resolve 4 open decisions, then proceed to Phase 1 implementation.
