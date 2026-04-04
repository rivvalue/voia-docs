# QBR Intelligence

QBR Intelligence is VOÏA's purpose-built module for turning Quarterly Business Review transcripts into structured, AI-powered briefings. Instead of reading through meeting notes manually, your team uploads the raw transcript and receives a concise QBR Brief — a single document covering renewal sentiment, relationship health, stakeholder mapping, key concerns, and committed action items.

**Who it is for:** Customer success managers, account executives, and CS leaders who run QBR conversations with clients and need to capture, track, and act on the outcomes quickly and consistently.

---

## How QBR Intelligence Works

1. You upload a plain-text transcript of your QBR conversation.
2. VOÏA's AI reads the transcript, identifies every participant, and extracts strategic intelligence.
3. The analysis is stored as a **QBR Brief** — a structured document you can review, compare, and share.
4. Every QBR brief for a given client is stored together, giving you a longitudinal view of how the relationship has evolved quarter over quarter.

---

## Uploading a Transcript

### Step 1 — Navigate to QBR Intelligence

Open the main navigation and click **QBR Intelligence**. The QBR dashboard lists all previously uploaded sessions for your account.

### Step 2 — Click Upload Transcript

Click the **Upload Transcript** button to open the upload form.

### Step 3 — Fill in the Session Details

| Field | What to enter |
|---|---|
| **Client Company** | Select or type the name of the client company. The autocomplete list is drawn from your participant database. |
| **Quarter** | Select Q1, Q2, Q3, or Q4. |
| **Year** | Enter the year of the QBR (e.g. 2026). |
| **Transcript File** | Upload a `.txt` file containing the QBR conversation. |

**File requirements:**

- Format: plain text (`.txt`) only
- Maximum size: 500 KB
- Encoding: UTF-8 (recommended)
- Content: the conversation transcript as exported from your meeting tool, or pasted manually

**Company name validation:** The company name must match a client in your participant database. If the company is not listed, add a participant for that company first, then return to the upload form.

### Step 4 — Submit

Click **Upload & Analyse**. VOÏA saves the transcript and queues it for analysis. You are redirected to the QBR dashboard where the new session appears with a **Pending** status badge.

---

## Duplicate Detection

VOÏA computes a unique fingerprint of each transcript file when it is uploaded. If you attempt to upload the same file a second time — even under a different filename — VOÏA will detect the duplicate and display an error message identifying the existing session. This prevents accidental double-processing and keeps your history clean.

---

## Analysis Lifecycle

Each QBR session moves through the following statuses:

| Status | Meaning |
|---|---|
| **Pending** | The transcript has been received and is waiting in the analysis queue. |
| **Processing** | VOÏA's AI is actively reading and analysing the transcript. |
| **Complete** | Analysis is finished. The full QBR Brief is available to view. |
| **Failed** | The analysis could not be completed (for example, if the transcript was empty or unreadable). You will receive an in-app notification. Re-upload a corrected file to try again. |

You will receive an in-app notification when analysis completes or fails. For large transcripts, processing typically takes between a few seconds and a couple of minutes.

---

## The QBR Brief

When a session reaches **Complete** status, click the session row to open the full QBR Brief. The brief is organized into the following sections.

### Executive Summary

A concise, AI-generated paragraph — no longer than 300 characters — that captures the single most important takeaway from the QBR conversation. Written in the same language as the transcript. Use this to brief stakeholders who need the headline before reading the full document.

### Renewal Sentiment

VOÏA classifies the client's overall disposition toward renewal into one of three values:

| Sentiment | Meaning |
|---|---|
| **Positive** | The client is satisfied and shows clear signals of intending to renew or expand. |
| **Neutral** | The relationship is stable but no strong signal in either direction was detected. |
| **At risk** | The transcript contains churn signals — dissatisfaction, unresolved concerns, or competitive pressure — that put renewal in doubt. |

A **Renewal Confidence Score** (0–100) accompanies the sentiment label and reflects how clearly the transcript supports that classification. A score of 90 or above means the AI found strong, unambiguous evidence; a lower score suggests the signal was mixed or subtle.

### Relationship Health

Alongside renewal sentiment, VOÏA provides a broader assessment of the client relationship:

| Health | Meaning |
|---|---|
| **Strong** | The partnership is performing well. Both sides appear aligned and engaged. |
| **Stable** | The relationship is functional but not exceptional. No major warning signs, but room to grow. |
| **Fragile** | Significant issues are present. The relationship may be at risk beyond the current renewal. |

A **Relationship Health Score** (0–100) accompanies this classification, measured on the same confidence scale.

### Stakeholders

A table listing every person identified in the transcript, showing:

- **Name** — as it appears in the transcript
- **Role** — job title or function (e.g. VP of Product, Customer Success Manager)
- **Side** — whether the person represents the **client** organisation, the **vendor** (your team), or is **unknown**

VOÏA scans speaker-turn labels, attendee lists, and self-introductions to build this list automatically. Up to 10 participants are shown.

**Tip:** The stakeholder list helps you understand whose voice carries most weight in the conversation. A concern raised by a C-level executive carries different strategic significance than the same concern raised by an end user.

### Top Concerns

Up to five key concerns raised by the client during the QBR, written in plain language. Each concern is accompanied by a **verbatim quote** — the shortest excerpt from the transcript that best supports it. If no clear source quote exists, the quote field is left blank.

Use this section to:
- Prioritise follow-up actions for your customer success team
- Prepare responses before your next client touchpoint
- Flag recurring concerns that appear across multiple QBR sessions

### Positive Highlights

Up to five positive signals from the conversation — wins, satisfied feedback, compliments on your product or team. Each highlight is paired with a supporting verbatim quote.

Use this section to:
- Reinforce what is working well
- Identify stories suitable for case studies or references
- Share wins with your internal team or leadership

### Competitive Mentions

A list of competitors mentioned during the QBR, along with the context in which they were mentioned and a threat level:

| Threat Level | Meaning |
|---|---|
| **Low** | The competitor was mentioned in passing or without urgency. |
| **Medium** | The competitor is being evaluated or the client has expressed interest in their offering. |
| **High** | The client has made direct comparisons, issued an ultimatum, or is actively considering switching. |

Monitoring competitive mentions across QBR sessions helps your team track which competitors are gaining traction and where your positioning needs strengthening.

### Action Items

Up to ten specific commitments or follow-up actions identified in the transcript — things that were agreed during the meeting, promised by either side, or explicitly flagged as next steps. Each action item is paired with a supporting verbatim quote.

Use this section as a checklist after the QBR. You can copy action items into your CRM, project tracker, or account plan to ensure nothing falls through the cracks.

### Expansion Signals

Up to five signals that the client may be open to expanding the relationship — interest in additional features, new use cases, references to growing their team, or requests for new capabilities. These are distinct from positive highlights; they specifically point toward upsell or cross-sell opportunity.

### Key Themes

Up to five overarching themes that emerged from the conversation — for example, "integration complexity," "support responsiveness," or "roadmap alignment." Themes are higher-level than individual concerns; they represent the recurring threads running through the meeting.

---

## Company History View

Each client company has a dedicated history page that shows all QBR sessions uploaded for that company, ordered from most recent to oldest. Click the company name on any session row in the QBR dashboard to open this view.

The history view lets you:
- Track how renewal sentiment and relationship health have changed over time
- Spot recurring concerns that persist across quarters
- Compare action items from previous sessions to see which ones were resolved

---

## Tips for Interpreting Results

**Combine sentiment with health scores.** A "Neutral" renewal sentiment paired with a low relationship health score is more urgent than a "Neutral" sentiment with a strong health score. Read both signals together.

**Prioritise high-threat competitive mentions.** If a competitor appears at "High" threat level in two consecutive QBR briefs for the same client, escalate the account internally before the next renewal conversation.

**Use action items as a QBR scorecard.** Before the next QBR, open the previous brief's action items and confirm which ones were completed. This holds both sides accountable and signals to the client that you track your commitments.

**Watch for shift in stakeholder composition.** If new C-level stakeholders appear in a QBR who were not present in previous sessions, this can signal an internal change at the client — a reorganisation, a new sponsor, or increased executive scrutiny of the relationship.

**Confidence scores guide your follow-up intensity.** A renewal confidence score below 50 means the AI could not find a strong directional signal. In those cases, schedule a direct check-in call rather than relying solely on the transcript.

**Language is preserved automatically.** If your QBR was conducted in French, German, or another language, VOÏA will write the brief — concerns, highlights, action items, summary — in that same language. Enum values (renewal sentiment, health classification, threat level) remain in English regardless of the transcript language.
