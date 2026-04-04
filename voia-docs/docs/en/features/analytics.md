# Analytics & Business Intelligence

---

## Dashboard Overview

Your main dashboard shows:
- **NPS Score:** Net Promoter Score (-100 to +100)
- **Response Rate:** Percentage of participants who responded
- **Sentiment Distribution:** Positive, neutral, negative breakdown
- **Active Campaigns:** Currently running surveys
- **Recent Responses:** Latest feedback received

**Real-time updates:** Dashboard refreshes automatically

**Example output:**

- Company: Mid-market SaaS
- NPS: 6 (Detractor)
- Sentiment: Negative
- Key driver: Support responsiveness
- Risk signal: High churn probability

---

## Net Promoter Score (NPS)

NPS measures customer loyalty on a scale from -100 to +100.

**How it's calculated:**
- **Promoters (9-10):** Happy customers who recommend you
- **Passives (7-8):** Satisfied but not enthusiastic
- **Detractors (0-6):** Unhappy customers at risk of leaving

**NPS = % Promoters - % Detractors**

**Industry benchmarks:**
- Excellent: 50+
- Good: 30-50
- Average: 10-30
- Needs improvement: Below 10

---

## Sentiment Analysis

Every response is analyzed for emotion:
- **Positive:** Customer is happy
- **Neutral:** Factual feedback, no strong emotion
- **Negative:** Customer is frustrated or disappointed

**Visual trends:** See sentiment change over time

---

## Key Themes

VOÏA automatically extracts the main topics customers mention and presents them as a ranked bar chart. Each bar represents one theme (for example, "pricing," "support quality," or "onboarding") and is color-coded by the dominant sentiment behind it — green for predominantly positive feedback, red for predominantly negative, and grey for neutral or mixed. Bars are ordered from most-mentioned to least-mentioned so you can see at a glance what is top of mind. Each bar displays both the raw response count and the percentage of respondents who raised that topic. Beneath the chart, an interpretive callout sentence summarizes the single most important takeaway — for example, "Pricing was the most discussed topic and was viewed negatively by 63% of respondents."

**Use Key Themes to:**
- Spot recurring concerns before they become serious problems
- Prioritize which areas of your product or service to improve first
- Track whether a theme grows or shrinks after you make changes

---

## Campaign Insights: Five-Tab Analytics

When you open a campaign and click **Insights**, you see a five-tab analytics workspace. Each tab focuses on a different dimension of your results. You can move freely between tabs without losing your place.

**Overview**
A high-level summary of the campaign so far:
- NPS score with a trend line showing how it has moved over the campaign period
- Response rate and total responses received
- Sentiment distribution (positive, neutral, negative) as a donut chart
- NPS Distribution chart showing the breakdown of Promoters, Passives, and Detractors as a proportion of all respondents
- A short AI-written headline that describes the most important finding in plain language

**Growth Analytics**
Focuses on expansion and retention signals:
- Promoter, Passive, and Detractor counts with week-over-week changes
- Response volume over time as an area chart
- Completion funnel showing how many participants opened the survey versus responded
- Highlight cards for the segments with the highest and lowest NPS

**Account Intelligence**
Gives you a company-level view of risk and opportunity across all accounts in the campaign:
- Balance score for each company — a single indicator combining NPS, sentiment, churn risk, and growth opportunity
- Confidence level (High, Medium, Low, or Insufficient) alongside each score so you know how much weight to give it
- A sortable account list so you can quickly surface the accounts most at risk or most likely to expand
- Hover over any account row to load detailed themes, sub-metrics, and verbatim highlights on demand
- See the [Account Intelligence](#account-intelligence) section below for a full explanation of each element

**Survey Insights**
Dives into the content of what customers said:
- Key Themes bar chart (described above)
- A question-by-question breakdown showing the distribution of answers
- Verbatim response samples tagged with sentiment and the themes they relate to
- NPS by Company table where each company name is a clickable link that takes you directly to that company's Account Insights page, so you can move from survey-level data to a full account view in one click

**Segmentation Insights**
Breaks results down by the groups you care about:
- NPS and sentiment split by company, role, or tenure
- Side-by-side segment comparison so you can see which groups are happiest and which need attention
- Filter controls let you isolate a single segment to explore its themes and responses in isolation

---

## Account Intelligence

Account Intelligence gives you a company-by-company view of how your customer relationships are performing.

**Balance Score**
Each account receives a balance score — a single number that combines NPS, sentiment, churn risk, and growth opportunity signals into one easy-to-read indicator. A positive balance score suggests a healthy relationship; a negative score is a warning sign that the account may need attention.

**Confidence Levels**
Because some accounts have responded more than others, every score is accompanied by a confidence level that tells you how much weight to give it:

- **High confidence** — Enough responses and data points to be statistically reliable. You can act on this score with confidence.
- **Medium confidence** — A reasonable signal, but consider reaching out directly to confirm the picture.
- **Low confidence** — Only a small amount of data is available. Treat this as an early indicator rather than a firm conclusion.
- **Insufficient data** — Too few responses to generate a meaningful score. The account row is still shown so you can decide whether to follow up proactively.

**Risk Badges**
Each company row displays a risk badge — **Critical**, **High**, **Medium**, or **Low** — that summarizes the overall risk level for that account. Hovering over the badge opens a tooltip that explains exactly why the account received that rating, describing the specific signals (such as low NPS, high churn risk, or negative sentiment trend) that drove the classification. This makes it easy to understand not just what the risk level is, but why it was assigned.

**Hover-Loaded Enrichment**
Hovering over any account row opens a tooltip that loads additional detail on demand. The tooltip includes the top themes that respondents from that company mentioned, a sub-metric breakdown covering satisfaction, service, pricing, and product value, the account's average AI churn risk score, and an AI-generated plain-language summary that synthesizes the account's overall feedback picture. This tooltip now also shows a **weighted enrichment breakdown** that reflects the influence of each respondent's seniority level — feedback from C-level executives and VP-level contacts is highlighted so you can see at a glance whether the signals are coming from decision-makers or from end users. This keeps the main table clean and scannable while still giving you depth when you need it.

**Use Account Intelligence to:**
- Prioritize at-risk accounts for your customer success team
- Identify expansion opportunities with healthy, engaged accounts
- Allocate outreach effort where it will have the most impact

---

## Influence-Weighted Scoring

VOÏA's scoring engine weights each survey response by the seniority of the person who submitted it. This means that feedback from senior stakeholders — the people with the most authority over renewal, expansion, and contract decisions — carries proportionally more weight than feedback from end users when calculating risk and growth signals.

VOÏA recognizes the following seniority tiers, from highest influence to baseline: C-level executives, VP/Director, Manager, Team Lead, and End user / individual contributor. C-level and VP-level respondents carry the most weight; end users serve as the baseline.

**How this affects risk signals**
When a C-level executive gives a low NPS score or signals dissatisfaction, the churn risk score for that account rises significantly more than it would for the same score submitted by an end user. This reflects the real-world reality that a dissatisfied executive has the authority to cancel or not renew a contract, while an end user typically does not.

**How this affects growth signals**
Positive feedback from senior stakeholders — a VP expressing strong satisfaction, a C-level executive indicating willingness to expand the relationship — is weighted more heavily in the growth opportunity calculations. This helps your customer success and sales teams prioritize the accounts where expansion signals are genuinely strategic.

**Where you see the effect**
- **Risk level badge** on each account row in Account Intelligence reflects influence-weighted churn risk
- **Balance score indicator** incorporates influence-weighted opportunity and risk totals
- **Hover enrichment tooltip** shows a weighted breakdown so you can see whether the signals are coming from decision-makers or end users
- **Growth signals** in the Growth Analytics tab reflect the weighted contribution of senior advocates

---

## Campaign Comparison

Campaign Comparison lets you place two or more campaigns side by side to understand how your results have changed over time. It is most useful when you have run a campaign more than once — for example, an annual or quarterly customer feedback cycle — and want to know whether things are getting better, staying the same, or getting worse.

**How to use it:**
- Open the **Executive Reports** section of a campaign and scroll to the Campaign Comparison table, or access it directly from the **Insights** workspace
- Select which previous campaigns to include in the comparison using the campaign selector
- Use the real-time search bar to filter rows by metric name if you are looking for a specific indicator

**What you see:**
- A metrics table that shows each KPI (NPS, sentiment, response rate, churn risk, and others) for each campaign in the comparison set
- A directional indicator next to each value — an upward arrow means the metric improved relative to the previous campaign, a downward arrow means it declined, and a dash means it held steady
- An account-level comparison table that shows, for each company in your participant list, the NPS delta between the current and previous campaign — so you can spot which accounts are trending up or down at the relationship level

**When to use Campaign Comparison:**
- At the end of each survey cycle to brief your leadership on progress
- When you suspect a product change or service improvement has had an effect on customer sentiment and want data to confirm it
- To identify accounts whose scores have dropped significantly since the last campaign, so your customer success team can intervene early

---

## Account Insights

Account Insights is a per-company panel that appears on the **Company Responses** page when you click on a company name. It gives you a concentrated view of everything VOÏA knows about that account from the current campaign, without needing to open the full Account Intelligence tab.

**The panel includes:**
- **NPS breakdown** — the count of Promoters, Passives, and Detractors from that company, along with their calculated NPS
- **Sub-metric progress bars** — visual indicators for churn risk and growth opportunity, scaled from 0–100 so you can assess account health at a glance
- **Churn risk gauge** — a prominent gauge that highlights accounts most at risk of not renewing or disengaging, helping you prioritize outreach
- **Topic pills** — small labeled tags showing the themes that respondents from this company mentioned most frequently; clicking a pill filters the response list to show only responses that mention that topic
- **Collapsible AI summary** — an AI-generated paragraph that synthesizes all responses from this company into a plain-language narrative; it explains the dominant sentiment, key concerns, and any notable positive signals; expand it when you need a quick briefing before a customer call

**Use Account Insights when:**
- You are preparing for a customer review or renewal conversation and need a quick summary of how that account feels
- Your customer success team wants to understand a specific company's feedback without reading through every individual response
- You need to decide whether to escalate an account to senior leadership based on their current sentiment and churn risk

---

## Strategic Accounts Dashboard

The Strategic Accounts dashboard is a dedicated view that focuses exclusively on your highest-priority customer relationships — those whose participants are tagged as **Strategic** or **Key** tier in the participant database. It is designed for customer success leaders and account executives who need to monitor their most important accounts without the noise of the full account list.

**How to access it**

Open the main dashboard and click the **Strategic Accounts** tab (marked with a crown icon). The view loads automatically for the active campaign. If you want to see data for a different campaign, you can pass a campaign ID via the URL. If no campaign is specified and one is active, the dashboard defaults to the active campaign.

**What the dashboard shows**

At the top of the view, a KPI strip gives you an instant snapshot of the overall health of your strategic account portfolio:

- **At-risk accounts** — the number of strategic accounts that have at least one active risk factor
- **Growth opportunities** — the number of strategic accounts showing at least one positive growth signal
- **No response** — the number of strategic accounts that have not yet submitted any survey responses in the current campaign (a coverage gap you may want to address)
- **Coverage rate** — the percentage of strategic accounts that have responded so far

Below the KPI strip, the account list shows every Strategic and Key tier account in the campaign, sorted from highest to lowest churn risk. Each row displays:

- **Company name** and their customer tier (Strategic or Key)
- **Risk badge** (Critical, High, Medium, or Low) derived from their influence-weighted churn risk
- **Balance score** indicator showing whether the account is risk-heavy, balanced, or opportunity-heavy
- **Response count** for the current campaign — accounts with zero responses are flagged visually so you know where coverage is missing
- **Hover-loaded enrichment** with the same detailed tooltip available in Account Intelligence, including the weighted breakdown of seniority tiers for that account's respondents

**How it differs from Account Intelligence**

Account Intelligence (in the Insights workspace) shows every company that has submitted at least one response in the campaign. The Strategic Accounts dashboard shows every company in the Strategic or Key tier, regardless of whether they have responded — this means you can see at a glance which of your most important accounts have not yet engaged with the survey.

**Use Strategic Accounts when:**
- You need to review the health of your top accounts before a QBR or leadership meeting
- You want to identify which key accounts have gone silent and may need proactive outreach
- You are prioritizing where your customer success team should focus their time this week
