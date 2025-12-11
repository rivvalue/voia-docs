# VOÏA V2 Enhancement: Role-Based Questioning & Deflection Control

**Document Version:** 1.0  
**Date:** December 11, 2025  
**Status:** Proposal for Team Review

---

## Executive Summary

This proposal addresses three critical gaps in VOÏA's conversational survey system:

1. **Role-Appropriate Questioning** - Adapt question style and depth based on participant persona
2. **Deflection Detection** - Recognize when participants can't/won't answer and respond gracefully
3. **Intelligent Follow-up Control** - Limit follow-ups per persona to respect participant time

The solution extends the existing `ROLE_METADATA` infrastructure with minimal architectural changes, no new infrastructure dependencies, and zero additional API costs.

---

## Problem Statement

### Current Behavior

| Issue | Impact | Example |
|-------|--------|---------|
| Same questions for all personas | Executives asked operational details they can't answer | VP asked "What specific features slow you down?" |
| No deflection detection | VOÏA keeps asking after user signals inability | User says "ask my PO" → VOÏA asks again |
| Fixed follow-up quota | 3 follow-ups per topic regardless of persona | Busy executive gets 3 detailed probes |

### Real Example (Zayd, VP of Operations)

```
VOÏA: "What specific aspects of the product could be improved?"
Zayd: "That's too technical for me to answer, ask my product owner"
VOÏA: "Could you share any specific examples?" ← Ignores deflection
Zayd: "I already told you I can't answer that"
VOÏA: "What challenges have you experienced?" ← Continues pushing
```

---

## Proposed Solution

### Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        ENHANCED ROLE_METADATA                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ROLE_METADATA = {                                                 │
│    'vp_director': {                                                │
│      'label': 'VP/Director-level leader',                          │
│      'excluded_topics': [],                                        │
│                                                                    │
│      # NEW: Behavioral Controls                                    │
│      'questioning_style': 'strategic',                             │
│      'follow_up_depth': 1,                                         │
│      'accept_delegation': True,                                    │
│                                                                    │
│      # NEW: LLM Guidance                                           │
│      'prompt_guidance': "Ask about business outcomes...",          │
│                                                                    │
│      # NEW: Curated Templates                                      │
│      'question_templates': { ... }                                 │
│    }                                                               │
│  }                                                                 │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                     V2 DETERMINISTIC CONTROLLER                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  1. Load persona config from ROLE_METADATA                         │
│  2. Select topic (unchanged)                                       │
│  3. Generate question using persona guidance/templates             │
│  4. Extract response + deflection signals                          │
│  5. Update topic_status with deflection tracking                   │
│  6. Respect follow_up_depth per persona                            │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                      TOPIC STATUS TRACKING                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  topic_status = {                                                  │
│    "NPS": {                                                        │
│      "status": "completed",                                        │
│      "question_count": 2,                                          │
│      "deflection": null                                            │
│    },                                                              │
│    "Product Quality": {                                            │
│      "status": "skipped",                                          │
│      "question_count": 1,                                          │
│      "deflection": {                                               │
│        "type": "not_responsible",                                  │
│        "reason": "Delegates to product owner"                      │
│      }                                                             │
│    }                                                               │
│  }                                                                 │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Enhanced ROLE_METADATA

### Complete Schema

```python
ROLE_METADATA = {
    'c_level': {
        'label': 'C-level executive',
        'excluded_topics': [],
        
        # Behavioral controls
        'questioning_style': 'strategic',
        'follow_up_depth': 1,
        'accept_delegation': True,
        
        # LLM guidance (injected into system prompt)
        'prompt_guidance': {
            'en': """
                For this C-level executive:
                - Focus on strategic impact, ROI, and business outcomes
                - Accept high-level answers without pressing for operational details
                - Do NOT ask about specific features, UI, or day-to-day workflows
                - If they delegate to their team, acknowledge positively and move on
                - Keep questions concise and respect their time
            """,
            'fr': """
                Pour ce dirigeant C-level:
                - Concentrez-vous sur l'impact stratégique, le ROI et les résultats business
                - Acceptez les réponses de haut niveau sans insister sur les détails opérationnels
                - NE PAS poser de questions sur les fonctionnalités spécifiques ou les workflows
                - S'ils délèguent à leur équipe, reconnaissez-le positivement et passez à autre chose
            """
        },
        
        # Curated question templates (optional, fallback to LLM if missing)
        'question_templates': {
            'en': {
                'NPS': "From a strategic perspective, how likely are you to recommend {company} to a fellow executive?",
                'Product Quality': "How would you characterize the overall value {product} brings to your organization?",
                'Support Quality': "How well has our partnership supported your strategic objectives?",
                'Pricing Value': "Does our pricing model align with the value delivered to your business?"
            },
            'fr': {
                'NPS': "D'un point de vue stratégique, recommanderiez-vous {company} à un collègue dirigeant?",
                'Product Quality': "Comment évalueriez-vous la valeur globale que {product} apporte à votre organisation?",
                'Support Quality': "Dans quelle mesure notre partenariat a-t-il soutenu vos objectifs stratégiques?"
            }
        }
    },
    
    'vp_director': {
        'label': 'VP/Director-level leader',
        'excluded_topics': [],
        
        'questioning_style': 'strategic',
        'follow_up_depth': 1,
        'accept_delegation': True,
        
        'prompt_guidance': {
            'en': """
                For this VP/Director:
                - Ask about team-level impact and departmental outcomes
                - Balance strategic and tactical perspectives
                - Accept delegation to team members as valid input
                - Limit detailed probing - they oversee but may not use directly
            """,
            'fr': """
                Pour ce VP/Directeur:
                - Posez des questions sur l'impact au niveau de l'équipe
                - Équilibrez les perspectives stratégiques et tactiques
                - Acceptez la délégation aux membres de l'équipe comme réponse valide
            """
        },
        
        'question_templates': {
            'en': {
                'NPS': "Based on your team's experience, how likely are you to recommend {company}?",
                'Product Quality': "How has {product} impacted your department's productivity?",
                'Support Quality': "How would you rate our responsiveness to your team's needs?"
            }
        }
    },
    
    'manager': {
        'label': 'Manager',
        'excluded_topics': [],
        
        'questioning_style': 'balanced',
        'follow_up_depth': 2,
        'accept_delegation': True,
        
        'prompt_guidance': {
            'en': """
                For this Manager:
                - Balance operational and strategic questions
                - Ask about team workflows and productivity
                - Can probe for some specific examples
                - Respect if they defer to technical team members
            """
        },
        
        'question_templates': {
            'en': {
                'NPS': "How likely are you to recommend {product} to peers in your role?",
                'Product Quality': "How well does {product} support your team's daily workflows?"
            }
        }
    },
    
    'team_lead': {
        'label': 'Team Lead/Supervisor',
        'excluded_topics': ['Pricing Value'],
        
        'questioning_style': 'operational',
        'follow_up_depth': 2,
        'accept_delegation': False,
        
        'prompt_guidance': {
            'en': """
                For this Team Lead:
                - Ask about hands-on experience and team usage
                - Can probe for specific feature feedback
                - Expect direct answers about workflows
            """
        }
    },
    
    'end_user': {
        'label': 'End User',
        'excluded_topics': ['Pricing Value'],
        
        'questioning_style': 'operational',
        'follow_up_depth': 3,
        'accept_delegation': False,
        
        'prompt_guidance': {
            'en': """
                For this End User:
                - Ask about day-to-day experience and specific features
                - Probe for concrete examples and pain points
                - Ask follow-up questions to understand workflows
                - Request specific feedback on usability
            """,
            'fr': """
                Pour cet utilisateur final:
                - Posez des questions sur l'expérience quotidienne et les fonctionnalités
                - Cherchez des exemples concrets et des points de friction
                - Posez des questions de suivi pour comprendre les workflows
            """
        },
        
        'question_templates': {
            'en': {
                'NPS': "Based on your daily experience, how likely are you to recommend {product}?",
                'Product Quality': "What features do you use most, and how well do they work for you?",
                'Support Quality': "When you've needed help, how responsive has our support been?"
            }
        }
    },
    
    'default': {
        'label': 'Participant',
        'excluded_topics': [],
        
        'questioning_style': 'balanced',
        'follow_up_depth': 2,
        'accept_delegation': True,
        
        'prompt_guidance': {
            'en': "Ask balanced questions appropriate for a general participant."
        }
    }
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Human-readable role name for display/logging |
| `excluded_topics` | list | Topics hidden from this persona |
| `questioning_style` | enum | `strategic` \| `balanced` \| `operational` |
| `follow_up_depth` | int | Maximum follow-up questions before moving to next topic |
| `accept_delegation` | bool | If true, treat "ask my team" as valid response |
| `prompt_guidance` | dict | Per-language LLM instructions for this persona |
| `question_templates` | dict | Per-language curated questions by topic |

---

## Component 2: Deflection Detection & Tracking

### Deflection Types

| Type | Signal Phrases | Controller Action |
|------|---------------|-------------------|
| `not_responsible` | "Ask my manager", "That's handled by IT", "My product owner knows" | Skip topic if `accept_delegation=True` |
| `no_data` | "I haven't used that", "Too new to comment", "Don't have experience" | Mark skipped, no follow-up |
| `confidential` | "Can't share that", "Internal only", "Sensitive information" | Mark skipped, acknowledge respectfully |
| `dont_understand` | "Not sure what you mean", "Can you clarify?" | Rephrase once, then skip |
| `already_answered` | "I told you already", "Same as before", "Already covered" | Skip immediately |
| `refuse` | "I'd rather not", "No comment", "Pass" | Mark skipped, move on |

### Enhanced Extraction Prompt

Add to existing extraction prompt:

```
DEFLECTION DETECTION:
Analyze the user's response for deflection signals. If detected, return:

{
  "deflection_detected": true,
  "deflection_type": "<type>",
  "deflection_reason": "<brief explanation>"
}

Deflection types and signals:
- "not_responsible": User delegates ("ask my manager", "my team handles this")
- "no_data": User lacks experience ("I don't use that", "too new")
- "confidential": Privacy concern ("can't share", "internal only")
- "dont_understand": Confusion ("what do you mean?", "can you clarify?")
- "already_answered": Repetition ("I already said", "same as before")
- "refuse": Explicit refusal ("I'd rather not", "no comment")

If no deflection detected, return:
{
  "deflection_detected": false,
  "deflection_type": null,
  "deflection_reason": null
}
```

### Topic Status Schema

```python
topic_status = {
    "NPS": {
        "status": "completed",        # completed | skipped | pending | in_progress
        "question_count": 2,
        "deflection": None
    },
    "Product Quality": {
        "status": "skipped",
        "question_count": 1,
        "deflection": {
            "type": "not_responsible",
            "reason": "User delegates to product owner",
            "detected_at": "2025-12-11T10:30:00Z"
        }
    },
    "Support Quality": {
        "status": "pending",
        "question_count": 0,
        "deflection": None
    }
}
```

---

## Component 3: Controller Integration

### Modified Flow

```python
def process_response(self, user_message: str) -> Dict[str, Any]:
    """Process user response with persona-aware controls"""
    
    # 1. Load persona config
    role_tier = _map_role_to_tier(self.participant_data.get('role'))
    persona_config = ROLE_METADATA.get(role_tier, ROLE_METADATA['default'])
    
    # 2. Extract data + deflection signals
    extraction_result = self._extract_with_ai(user_message)
    
    # 3. Check for deflection
    if extraction_result.get('deflection_detected'):
        deflection = {
            'type': extraction_result['deflection_type'],
            'reason': extraction_result['deflection_reason'],
            'detected_at': datetime.utcnow().isoformat()
        }
        
        # Update topic status
        self.topic_status[self.current_topic]['status'] = 'skipped'
        self.topic_status[self.current_topic]['deflection'] = deflection
        
        # Generate graceful acknowledgment
        return self._generate_deflection_response(deflection, persona_config)
    
    # 4. Check follow-up depth
    current_count = self.topic_status[self.current_topic]['question_count']
    max_depth = persona_config['follow_up_depth']
    
    if current_count >= max_depth:
        # Move to next topic
        self.topic_status[self.current_topic]['status'] = 'completed'
        return self._generate_next_topic_question()
    
    # 5. Generate persona-appropriate follow-up
    return self._generate_question(persona_config)


def _generate_question(self, persona_config: Dict) -> str:
    """Generate question using persona config"""
    
    language = self._campaign_language_code
    topic = self.current_topic
    
    # Option 1: Use curated template if available
    templates = persona_config.get('question_templates', {})
    if language in templates and topic in templates[language]:
        template = templates[language][topic]
        return template.format(
            company=self.company_name,
            product=self.product_name
        )
    
    # Option 2: LLM generation with persona guidance
    guidance = persona_config.get('prompt_guidance', {}).get(language, '')
    return self._generate_question_with_ai(topic, guidance)


def _generate_deflection_response(self, deflection: Dict, persona_config: Dict) -> str:
    """Generate graceful response to deflection"""
    
    deflection_type = deflection['type']
    language = self._campaign_language_code
    
    responses = {
        'en': {
            'not_responsible': "Understood, that's helpful context. Let's move on to something else.",
            'no_data': "No problem, we'll skip that one. Moving on...",
            'confidential': "Of course, I understand. Let's continue with another topic.",
            'dont_understand': "Let me rephrase that differently.",
            'already_answered': "Got it, thanks. Let me ask about something else.",
            'refuse': "No problem at all. Let's continue."
        },
        'fr': {
            'not_responsible': "Compris, c'est un contexte utile. Passons à autre chose.",
            'no_data': "Pas de problème, on va passer cette question.",
            'confidential': "Bien sûr, je comprends. Continuons avec un autre sujet.",
            'already_answered': "Compris, merci. Passons à une autre question."
        }
    }
    
    lang_responses = responses.get(language, responses['en'])
    return lang_responses.get(deflection_type, lang_responses.get('refuse'))
```

---

## Data Persistence

### What Gets Stored

| Location | Data | Purpose |
|----------|------|---------|
| `active_conversations.survey_data` | `topic_status` dict | Mid-conversation state |
| `survey_response.ai_prompts_log` | All prompts + responses | Debugging |
| `survey_response` (new field) | `deflection_summary` | Analytics |

### New Field: `deflection_summary`

```sql
ALTER TABLE survey_response 
ADD COLUMN deflection_summary TEXT;  -- JSON
```

```json
{
  "total_deflections": 2,
  "deflections": [
    {
      "topic": "Product Quality",
      "type": "not_responsible",
      "reason": "Delegates to product owner"
    },
    {
      "topic": "Pricing Value",
      "type": "confidential",
      "reason": "Cannot share pricing discussions"
    }
  ],
  "completion_rate": 0.75
}
```

---

## Analytics Value

### New Metrics Available

| Metric | Query | Insight |
|--------|-------|---------|
| Deflection rate by persona | `GROUP BY role_tier, deflection_type` | VPs deflect 3x more than end users |
| Topic coverage by role | `WHERE deflection IS NOT NULL` | Executives skip Product Quality 60% |
| Question efficiency | `AVG(question_count) BY persona` | End users need 2.5 questions, execs need 1.2 |

### Dashboard Additions

- Deflection heatmap: persona × topic
- Completion rate by persona tier
- Most common deflection reasons

---

## Migration Path

### Phase 1: Immediate (Week 1)
1. Extend `ROLE_METADATA` with new fields
2. Add `prompt_guidance` injection to system prompt
3. Update `follow_up_depth` control in V2 controller

### Phase 2: Deflection (Week 2)
1. Enhance extraction prompt with deflection detection
2. Add `topic_status` tracking
3. Implement graceful deflection responses
4. Add `deflection_summary` to survey_response

### Phase 3: Templates (Week 3)
1. Populate `question_templates` for priority personas
2. Validate with live survey transcripts
3. A/B test template vs LLM-generated questions

### Phase 4: Analytics (Week 4)
1. Build deflection analytics queries
2. Add dashboard visualizations
3. Generate persona tuning recommendations

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM ignores guidance | Medium | Low | Templates as fallback, strict prompting |
| False deflection detection | Low | Medium | Conservative detection, manual review |
| Over-restrictive follow-ups | Low | Medium | Start with higher limits, tune down |
| Template gaps | Medium | Low | LLM fallback for missing templates |

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Executive completion rate | 65% | 85% |
| Deflection-after-signal rate | 45% | <10% |
| Avg questions for executives | 8 | 4-5 |
| User satisfaction (post-survey) | N/A | 4.2/5 |

---

## Appendix: Files to Modify

| File | Changes |
|------|---------|
| `prompt_template_service.py` | Extend ROLE_METADATA, add guidance injection |
| `ai_conversational_survey_v2.py` | Deflection detection, topic_status, follow-up control |
| `deterministic_helpers.py` | Update state persistence for topic_status |
| `models.py` | Add deflection_summary column |
| `routes.py` | Save deflection_summary on finalization |

---

## Appendix: Comparison with RAG Alternative

The team considered a RAG (Retrieval-Augmented Generation) approach using pgvector for semantic question retrieval. After analysis, the ROLE_METADATA approach was selected for the following reasons:

| Factor | RAG Layer | ROLE_METADATA |
|--------|-----------|---------------|
| Scale fit | Designed for 1000s of variations | Perfect for ~50 combinations |
| Setup cost | High (schema, embeddings, caching) | Low (extend existing code) |
| Maintenance | Embedding regeneration on edits | Simple dictionary updates |
| Latency | Vector search overhead | Zero overhead (in-memory) |
| Determinism | Risk of unexpected results | Fully predictable |

**Recommendation:** Implement ROLE_METADATA first. Consider RAG only if template needs exceed 100+ variations or require dynamic A/B testing at scale.

---

**End of Proposal**
