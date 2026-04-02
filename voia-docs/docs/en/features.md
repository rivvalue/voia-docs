# VOÏA Voice Of Client Platform Features

VOÏA captures customer feedback through conversational interactions, processes each response into structured data (NPS, sentiment, drivers, risk signals), and aggregates results into actionable insights at both campaign and account levels.

This guide covers all features available in the VOÏA platform.

---

## AI-Powered Survey Intelligence

### Conversational Survey Engine

Instead of traditional forms, VOÏA can conduct natural conversations with your customers using AI.

**How it works:**
- Customers respond in their own words
- AI asks smart follow-up questions
- Conversation feels natural and engaging
- Data is automatically structured for analysis

**Benefits:**
- Higher completion rates (customers prefer conversations)
- Richer feedback (more detailed responses)
- Less survey fatigue
- Automatic language detection

---

### Automatic Analysis

VOÏA analyzes every response automatically:

**Sentiment Analysis**  
Detects if feedback is positive, negative, or neutral

**Key Themes**  
Identifies the main topics customers mention (e.g., "pricing," "support quality," "features")

**Churn Risk**  
Flags customers who might stop using your service

**Growth Opportunities**  
Highlights areas where customers want improvements

**No manual work required** - All analysis happens automatically in the background.

---

### Executive Reports

Executive Reports bring together the most important findings from a campaign into a single, presentation-ready document you can share with leadership or stakeholders. Each report is organized into three named sections.

**KPI Overview**
A summary table that shows your key performance indicators side by side. Each metric row includes a sparkline — a miniature trend chart — so readers can see at a glance whether a number has been improving or declining over the campaign period. The NPS figure is color-coded (green for a healthy score, amber for a score that needs attention, red for a score requiring immediate action) so the most critical information is immediately visible. An AI-generated headline sentence at the top of the table translates the numbers into plain language for readers who prefer a quick summary.

**Campaign Comparison**
A structured table that lets you measure the current campaign against one or more previous campaigns. Each metric is shown with a directional indicator — an upward arrow for improvement, a downward arrow for decline — so trends are visible without having to calculate differences yourself. A real-time search bar lets you filter the comparison table by metric name or campaign name, which is especially useful when you are working with many campaigns and need to find a specific data point quickly. See the Campaign Comparison section below for more detail on how to use this feature.

**Trends Modal**
An interactive overlay that opens when you click **View Trends** inside the report. It displays eight charts organized into two groups. The first group focuses on experience metrics: NPS trajectory, sentiment distribution over time, response volume, and completion rate. The second group focuses on relationship health: churn risk trend, growth opportunity trend, account balance score, and theme frequency changes. Use the Trends Modal when you want to understand the story behind the headline numbers and identify which direction things are heading.

**Perfect for:** Sharing with leadership or stakeholders who need the full picture without logging into the platform

---

## Campaign Management

### Campaign Lifecycle

Every campaign moves through a defined workflow that includes a mandatory vetting gate between Ready and Active:

**Draft** → Create and configure your survey  
**Ready** → Review your campaign and complete the vetting gate  
**[Vetting gate]** → Simulate the survey, then have a manager validate it  
**Active** → Survey is live, collecting responses  
**Completed** → Campaign closed, final reports available

The campaign list shows each campaign's current status. A lifecycle help tooltip is available at the **Status** column header — click or hover the header to see a description of every stage. This tooltip appears once at the column level rather than on each individual campaign row. Each campaign row also displays action buttons (View, Insights, Participants, Export, Report) that are all rendered at equal width, so the controls remain visually consistent and easy to scan regardless of label length.

**Vetting gate — required before activation**

A campaign in the Ready state cannot be activated until it passes a two-step vetting gate. The gate has three possible statuses:

- **Not simulated** — The campaign has not yet been simulated. You must run a simulation before the Activate button becomes available.
- **Simulated, not validated** — The simulation is complete, but a manager has not yet reviewed and validated the results. Validation is required before activation.
- **Ready to activate** — Both steps are complete. The Activate button is now available.

**Single active campaign per account**

By default, only one campaign can be active at a time per account. Attempting to activate a second campaign while one is already active will be blocked. If your team needs to run multiple campaigns simultaneously, parallel campaign activation is available on request — contact your account administrator or VOÏA support to enable it.

---

### Creating a Campaign

**Step 1: Basic Information**
- Campaign name
- Start date (when invitations send)
- End date (last day to respond)
- Description (internal notes)

**Step 2: Survey Type**
- **Traditional Survey:** Fixed questions
- **Conversational Survey:** AI-powered conversations

**Step 3: Customization**
- Customize questions
- Set completion time estimate
- Add your branding
- **Custom Topic Hints (JSON):** Optionally guide the AI toward specific topics by entering a JSON list of hints. The field includes an info (?) button that opens a formatted example showing the correct JSON structure. Inside that example panel, a **Copy JSON** button lets you copy the sample directly to your clipboard so you can adapt it without typing the format from scratch.

**Step 4: Participant Assignment**
- Choose who receives the survey
- Import from CSV or add manually

---

### Survey Simulation Mode

Survey Simulation Mode lets you experience your campaign's survey exactly as a respondent would, before any real invitations are sent. It is a required step in the vetting gate — you cannot activate a campaign until a simulation has been completed.

**What simulation is**

Simulation runs a live, interactive preview of the survey using the same AI engine and configuration that real respondents will encounter. For conversational surveys, the AI conducts the full conversation. For classic surveys, you walk through the complete questionnaire as it will appear to participants.

**Why it exists**

Simulation protects you from sending a misconfigured or confusing survey to your customer base. It gives your team confidence that questions are phrased correctly, the flow makes sense, and the survey behaves as intended — all before a single invitation goes out.

**How to launch a simulation**

1. Open a campaign in Draft or Ready status
2. Click **Simulate** (or **Preview** for classic surveys) in the campaign detail view
3. Complete the survey as a respondent would — try different answers to test the AI's follow-up behavior
4. When finished, confirm that the simulation is complete; the campaign's vetting status updates to **Simulated, not validated**

**What the manager sees**

After simulation, the campaign detail page shows the simulation timestamp and the current vetting status badge. The manager can then review the results and click **Validate** to move the status to **Ready to activate**.

**Testing different respondent personas**

For conversational surveys, you can run the simulation multiple times using different simulated personas — for example, a satisfied promoter, a neutral passive, or a frustrated detractor — to verify that the AI adapts its follow-up questions appropriately for each scenario. Each run updates the simulation timestamp.

**Prerequisite for activation**

The Activate button remains disabled until both steps of the vetting gate are complete: the simulation must be finished and a manager must have validated the campaign. Once both conditions are met, the Activate button becomes available.

---

### Automated Reminders

VOÏA automatically sends reminder emails to boost response rates:

**Midpoint Reminder**  
Sent halfway through your campaign (e.g., Day 45 of a 90-day campaign)

**Last Chance Reminder**  
Sent 7-14 days before campaign closes (you choose)

**Automatic and smart** - No manual work needed.

---

## Participant Management

### Participant Database

Centralized database of all your customers:
- Name and email
- Company (optional)
- Role/position (optional)
- Custom fields

**Advanced filtering:** Find participants by company, role, or custom attributes

---

### Adding Participants

**Option 1: Manual Entry**
1. Click **Add Participant**
2. Enter name, email, and optional details
3. Save

**Option 2: Bulk CSV Import** (Recommended for large lists)
1. Download CSV template
2. Fill in participant data
3. Upload file
4. VOÏA validates and imports automatically

**Validation:** VOÏA checks for duplicate emails and invalid data

---

### Participant Segmentation

Group participants by:
- **Company:** Track feedback by organization
- **Role:** Senior executives vs. frontline users
- **Tenure:** Long-term vs. new customers

**Use segmentation for:**
- Targeted campaigns
- Segmented analytics
- Personalized survey experiences

---

## Analytics & Business Intelligence

### Dashboard Overview

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

### Net Promoter Score (NPS)

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

### Sentiment Analysis

Every response is analyzed for emotion:
- **Positive:** Customer is happy
- **Neutral:** Factual feedback, no strong emotion
- **Negative:** Customer is frustrated or disappointed

**Visual trends:** See sentiment change over time

---

### Key Themes

VOÏA automatically extracts the main topics customers mention and presents them as a ranked bar chart. Each bar represents one theme (for example, "pricing," "support quality," or "onboarding") and is color-coded by the dominant sentiment behind it — green for predominantly positive feedback, red for predominantly negative, and grey for neutral or mixed. Bars are ordered from most-mentioned to least-mentioned so you can see at a glance what is top of mind. Each bar displays both the raw response count and the percentage of respondents who raised that topic. Beneath the chart, an interpretive callout sentence summarizes the single most important takeaway — for example, "Pricing was the most discussed topic and was viewed negatively by 63% of respondents."

**Use Key Themes to:**
- Spot recurring concerns before they become serious problems
- Prioritize which areas of your product or service to improve first
- Track whether a theme grows or shrinks after you make changes

---

### Campaign Insights: Five-Tab Analytics

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

### Account Intelligence

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

### Influence-Weighted Scoring

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

### Campaign Comparison

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

### Account Insights

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

### Strategic Accounts Dashboard

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

---

## Communication & Email System

### Email Configuration

Choose how VOÏA sends emails:

**Option 1: VOÏA-Managed (Default)**  
We handle email delivery using our servers. No configuration needed.

**Option 2: Your Own SMTP Server**  
Use your company's email server for branded emails.

**Requirements for custom SMTP:**
- SMTP server address
- Port number
- Username and password
- Connection security (TLS/SSL)

**Test before activating:** VOÏA includes a built-in connection tester

---

### Email Templates

All emails are professionally designed and include:
- Your company logo
- Campaign name
- Personalized greeting
- Survey link
- Professional footer

**Automatic branding:** Your logo appears in all emails automatically

---

### Invitation Management

**Bulk Invitations**  
Send to all participants at once when campaign activates

**Individual Invitations**  
Send to specific participants manually

**Resend Options**  
Resend to participants who haven't responded

**Delivery Tracking**  
See which emails were delivered, opened, or bounced

---

## User Management & Permissions

### User Roles

**Admin**  
- Create and manage campaigns
- Add and remove users
- Configure branding and email settings
- View all analytics

**Manager**  
- Create and manage campaigns
- Add participants
- View analytics
- Cannot manage users or settings

**Viewer**  
- View dashboards and reports only
- Cannot create campaigns or modify data

---

### Adding Team Members

1. Navigate to **User Management**
2. Click **Add User**
3. Enter email address
4. Select role (Admin, Manager, or Viewer)
5. Send invitation

**Email invitation:** New user receives login instructions automatically

---

### License Limits

Your account has a limit on users based on your license:
- **Core:** 5 users
- **Plus:** 10 users
- **Pro:** 25+ users (customizable)

**Check usage:** User management page shows "X of Y users"

---

## Branding & Customization

### Logo Upload

Add your company logo to surveys and emails:

1. Go to **Brand Configuration**
2. Click **Upload Logo**
3. Select image file (PNG, JPG, or SVG)
4. Logo appears automatically across platform

**Best practices:**
- Use transparent background (PNG)
- Recommended size: 200x60 pixels
- Maximum file size: 2MB

---

### White-Label Options

**Custom Domain** (Enterprise plans)  
Use your own domain (e.g., feedback.yourcompany.com)

**Branded Surveys**  
Surveys match your company colors and style

**Email Branding**  
Emails sent from your domain

[Contact support for white-label setup]

---

## Security & Privacy

### Secure Survey Access

Participants access surveys using unique, secure tokens:
- **One-time use:** Token expires after use
- **Time-limited:** Optional expiration dates
- **No login required:** Participants don't need accounts

**Security:** Tokens are cryptographically secure and cannot be guessed

---

### Data Privacy

**Anonymization Options**  
Hide participant names in reports (show anonymous responses only)

**Data Encryption**  
All data is encrypted in transit (HTTPS) and at rest

**Access Control**  
Only authorized users in your account can see your data

**Multi-tenant Isolation**  
Your data is completely separated from other VOÏA accounts

---

### Audit Logging

VOÏA tracks all important actions:
- Campaign creation and activation
- User logins
- Participant additions
- Email sends
- Report exports

**Use audit logs for:**
- Compliance
- Security monitoring
- Team accountability

---

## Understanding Your License

Your VOÏA account includes specific limits based on your license tier:

- **Campaigns per year**
- **Maximum users**
- **Participants per campaign**
- **Features included**

**Check your limits:** Navigate to **License Overview** in settings

[Learn more about licenses →](licenses.md)

---

## Mobile & Accessibility

### Mobile-Responsive Design

VOÏA works on all devices:
- **Desktop:** Full feature access
- **Tablet:** Optimized layout
- **Mobile:** Surveys and dashboards work perfectly on phones

**Participants can respond from any device**

---

### Accessibility Features

VOÏA follows web accessibility standards (WCAG 2.1 AA):
- Screen reader compatible
- Keyboard navigation support
- High contrast mode
- Clear labels and instructions

**Inclusive feedback collection** for all customers

---

## Data Export & Integration

### Export Options

Export your data in multiple formats:
- **CSV:** Spreadsheet format for analysis
- **PDF:** Executive reports
- **Excel:** Formatted workbooks with charts

**What you can export:**
- Participant lists
- Survey responses
- Analytics reports
- NPS trends

---

### API Access (Plus and Pro plans)

Integrate VOÏA with other systems:
- CRM integration
- Business intelligence tools
- Custom reporting systems
- Automated workflows

[API documentation available for technical teams]

---

## Performance & Reliability

### System Performance

VOÏA is built for speed:
- Dashboard loads in under 500ms
- Supports 1,000+ concurrent survey participants
- Handles 10,000+ responses per hour

**99.9% uptime** with automatic failover

---

### Background Processing

Long-running tasks happen in the background:
- AI analysis of responses
- Bulk email sending
- Executive report generation

**You don't have to wait** - Continue working while VOÏA processes data

---

## Getting Support

### Help Resources

**In-Platform Help**  
Look for <i class="fa fa-question-circle"></i> icons next to features

**This Documentation**  
Comprehensive guides and instructions

**Video Tutorials** <span class="badge badge-coming-soon">Coming Soon</span>  
Step-by-step video walkthroughs

### Contact Support

Reach out to your account administrator or contact:
- **Email:** [support@rivvalue.com](mailto:support@rivvalue.com)

---

<div class="text-center text-muted" style="margin-top: 3rem;">
  <p>Need help? Don't hesitate to reach out to our support team.</p>
</div>
