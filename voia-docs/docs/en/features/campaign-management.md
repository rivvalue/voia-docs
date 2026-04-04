# Campaign Management

---

## Campaign Lifecycle

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

## Creating a Campaign

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

## Survey Simulation Mode

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

## Automated Reminders

VOÏA automatically sends reminder emails to boost response rates:

**Midpoint Reminder**  
Sent halfway through your campaign (e.g., Day 45 of a 90-day campaign)

**Last Chance Reminder**  
Sent 7-14 days before campaign closes (you choose)

**Automatic and smart** - No manual work needed.
