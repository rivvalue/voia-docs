# VOÏA Business Intelligence Hub — Analytics Reference

**What Every Chart Tells You and What You Can Do With It**

*Action Type: **S** = Strategic (long-term direction, resource allocation, positioning) · **O** = Operational (immediate execution, specific account touchpoints)*

*Applies to both VOÏA conversational (AI) and classic structured surveys unless noted.*

---

## Tab 1 — Overview

| Chart / Metric | Description | Questions it addresses | Actions it identifies | Type | Category |
|---|---|---|---|---|---|
| **NPS Score** | Overall Net Promoter Score for the campaign (−100 to +100) | What is the health of our client relationships? How do we trend vs. prior period? | Set relationship health baseline; trigger cross-functional intervention if score falls below benchmark | S | Relationship Health |
| **Total Responses** | Count of completed survey responses | Is the volume statistically meaningful to draw conclusions? | Extend campaign or send reminders before analysis cutoff | O | Campaign Management |
| **Response Rate** | % of invited participants who completed the survey | Are clients engaging? Which segments are systematically silent? | Target silent accounts with personalized follow-up; diagnose disengagement before NPS data exists | O | Churn Risk Management |
| **Recent (30 days)** | Responses submitted in the last 30 days | Is feedback arriving consistently or front-loaded? | Adjust reminder cadence; time analysis and action cycles accordingly | O | Campaign Management |
| **Accounts Needing Attention** *(KPI card)* | Count of companies flagged by AI as likely needing re-engagement | How many clients are at risk right now? | Escalate to leadership; prioritize account manager outreach | O | Churn Risk Management |
| **Opportunity Signal** | Aggregated growth potential score based on NPS distribution | What is our organic growth capacity from the existing client base? | Activate promoter programs (referrals, case studies) when high; invest in relationship repair when low | S | Account Growth |
| **NPS Distribution** | Promoter / Passive / Detractor breakdown in counts and % | What proportion of clients are loyal advocates vs. at-risk? | Convert passives through value reinforcement; address detractors individually through customer success | S + O | Relationship Health |
| **Accounts Needing Attention** *(panel)* | Ranked list of highest-risk companies with direct links to responses | Which companies need relationship intervention this week? | Trigger account manager calls, executive outreach, or customized recovery plans | O | Churn Risk Management |
| **Key Themes** | AI-ranked frequency of topics mentioned in open-text feedback | What are clients talking about most? Are recurring themes positive or negative? | Prioritize product roadmap and service improvements; validate suspected pain points with evidence | S | Product & Service Improvement |

---

## Tab 2 — Account Intelligence

| Chart / Metric | Description | Questions it addresses | Actions it identifies | Type | Category |
|---|---|---|---|---|---|
| **Account Intelligence Table** | Per-company scoring of opportunities (upsell / expansion / referral / renewal) vs. risks (Critical → Low), producing a Health Ratio: High Potential / Balanced / Risk-Heavy. Confidence-rated by response rate and count. | Which accounts represent the best expansion opportunities? Which are at risk? Where should commercial teams focus this quarter? | Prioritize High Potential accounts for expansion conversations; build recovery plans for Risk-Heavy accounts; schedule maintenance touchpoints for Balanced accounts | S + O | Account Growth / Churn Risk Management |

---

## Tab 3 — Growth Analytics

| Chart / Metric | Description | Questions it addresses | Actions it identifies | Type | Category |
|---|---|---|---|---|---|
| **Customer Tenure Distribution** | Distribution of respondents by client tenure cohort (< 1 yr to 10+ yrs) | What is the experience profile of respondents? Which cohort is over- or under-represented? | Design differentiated engagement by cohort: onboarding programs for new clients; loyalty recognition for long-tenured accounts | S | Customer Lifecycle |
| **NPS-Based Opportunity Analysis** | Promoter / Passive / Detractor breakdown in relation to growth factor potential | What NPS segment is limiting organic growth? Are we losing more from detractors or failing to convert passives? | Launch promoter activation campaigns; set passive conversion targets; define detractor recovery metrics | S | Account Growth |
| **Sentiment Analysis** | AI-derived positive / neutral / negative tone distribution across all open-text feedback *(both survey types)* | What is the emotional tone overall? Is negative sentiment rising independently of the NPS score? | Escalate if sentiment spikes negatively; use as a leading indicator ahead of NPS movement | O | Relationship Health |
| **Average Ratings** | Mean scores for Satisfaction, Service, Product Value, and Pricing | Where are we strongest and where is there a measurable performance gap? | Target the weakest sub-metric for immediate improvement; compare across campaigns to track whether interventions worked | S + O | Product & Service Improvement |
| **CSAT Distribution** *(classic surveys only)* | Distribution of Customer Satisfaction scores | How satisfied are clients with specific interactions? When do satisfaction dips occur? | Identify dips correlated with product changes or time periods; trigger root-cause investigation | O | Product & Service Improvement |
| **CES Distribution** *(classic surveys only)* | Distribution of Customer Effort Scores — how easy clients find it to work with you | Are we creating friction in our processes or delivery? | Simplify onboarding, support, or service request processes where effort scores are high | O | Product & Service Improvement |
| **Driver Impact Analysis** *(classic surveys only)* | Frequency-weighted ranking of drivers clients cite as most influential on their NPS (quality, pricing, support, ease, etc.) | What factors most strongly influence loyalty and detraction? Are the drivers the same? | Prioritize improvement of highest-impact negative drivers; proactively communicate and reinforce positive ones | S | Product & Service Improvement |
| **Recommendation Status** *(classic surveys only)* | Distribution across recommendation stages: actively recommends → would not recommend | How many clients are reference-ready today? What is blocking advocacy? | Build a reference program from the "actively recommends" segment; address blockers cited by "would not recommend" clients | S | Promoter Activation |
| **NPS–CSAT–CES Correlation** *(classic surveys only)* | Alignment between NPS, satisfaction, and effort scores per respondent or segment | Is high satisfaction always correlated with high NPS? Does low effort produce loyalty? | Investigate outliers: high CSAT + low NPS = satisfied but not enthusiastic; diagnose whether effort is a barrier to advocacy | S | Relationship Health |
| **Feature Adoption & Satisfaction** *(classic surveys only)* | Per-feature usage frequency, importance rating, and satisfaction score | Which features are widely used but poorly rated? Which are important but underutilized? | Focus product improvements on high-importance, low-satisfaction features; create enablement programs for high-importance, low-adoption features | S | Product & Service Improvement |

---

## Tab 4 — Survey Insights

| Chart / Metric | Description | Questions it addresses | Actions it identifies | Type | Category |
|---|---|---|---|---|---|
| **NPS by Client Company** | Per-company NPS, promoter / passive / detractor split, sub-metric averages, top themes, churn risk score, and AI summary — full detail on hover | How is each individual relationship performing? Which companies drag the aggregate score down? | Build a company-by-company action plan; brief account managers using the AI summary before client calls | O | Churn Risk Management / Account Growth |
| **NPS by Customer Tenure** | NPS score per tenure cohort showing Promoters, Passives, Detractors per group | At which lifecycle stage are we strongest? Where does loyalty decline? | Intervene earlier if new clients score low (onboarding gap); create retention programs at the cohort where NPS decays; activate long-tenured advocates | S | Customer Lifecycle |

---

## Tab 5 — Segmentation Analytics

| Chart / Metric | Description | Questions it addresses | Actions it identifies | Type | Category |
|---|---|---|---|---|---|
| **NPS by Role** | NPS broken down by respondent role (C-Suite, Manager, End User, IT, Finance, etc.) | Do decision-makers feel differently than end users? Is a role systematically underserved? | Tailor communication and value messaging by role; investigate usability if End User NPS is low while C-Suite NPS is high | S | Segmentation & Targeting |
| **NPS by Region** | NPS broken down by the geographic region of each client company | Are there regional performance disparities? Is a specific market underserved? | Adjust regional service resources, support coverage, or local partnerships; identify markets ready for expansion | S | Segmentation & Targeting |
| **NPS by Customer Tier** | NPS broken down by client tier (Enterprise, Mid-Market, SMB) | Are larger accounts more or less satisfied than smaller ones? Are we over- or under-investing in a tier? | Reallocate customer success resources toward underperforming tiers; develop differentiated service models if the tier-NPS gap is consistent | S | Segmentation & Targeting |
| **NPS by Client Industry** | NPS broken down by the client's industry vertical | Do we perform better in some verticals? Where is product-market fit strongest? | Refine go-to-market positioning toward high-NPS verticals; investigate product gaps in low-NPS sectors | S | Commercial Strategy |
| **Promoter / Passive / Detractor Composition** | Stacked NPS category composition across all segmentation dimensions simultaneously | Where is our detractor concentration highest? Which segments have the most balanced mix? | Identify the highest-risk segment combination for targeted intervention; build segment-specific recovery plans | S + O | Segmentation & Targeting / Churn Risk Management |
| **Churn Risk by Segment** | Average AI-derived churn risk score per segment, switchable: Tier / Role / Region | Which segment carries the highest aggregate churn risk? Is risk concentrated in one dimension? | Proactively engage the highest-risk segment with retention programs before renewal windows open | O | Churn Risk Management |
| **Tenure Cohort Analysis** | NPS and satisfaction by client tenure cohort showing how relationship quality evolves over the lifecycle | At what point does loyalty peak or decline? Is there a "tenure fatigue" effect? | Redesign the client experience at identified drop-off points; build milestone recognition for long-tenured clients | S | Customer Lifecycle |
| **Sub-Metric Breakdown by Segment** | Average Satisfaction, Service, Product Value, and Pricing scores per segment, switchable: Role / Region / Tier | Does one segment consistently rate pricing lower? Do certain roles perceive less product value? | Develop segment-specific value propositions; escalate structural pricing or service quality gaps to the relevant business function | S | Segmentation & Targeting / Commercial Strategy |

---

**Action categories:** Relationship Health · Account Growth · Churn Risk Management · Product & Service Improvement · Promoter Activation · Customer Lifecycle · Segmentation & Targeting · Commercial Strategy · Campaign Management

---
---

# Hub d'Intelligence Client VOÏA — Référence Analytique

**Ce que chaque indicateur vous révèle et les actions qu'il permet d'engager**

*Type d'action : **S** = Stratégique (orientation long terme, allocation des ressources, positionnement) · **O** = Opérationnel (exécution immédiate, intervention sur un compte spécifique)*

*S'applique aux enquêtes conversationnelles VOÏA (IA) et aux enquêtes classiques structurées, sauf mention contraire.*

---

## Onglet 1 — Vue d'ensemble

| Indicateur / Graphique | Description | Questions auxquelles il répond | Actions qu'il permet d'identifier | Type | Catégorie |
|---|---|---|---|---|---|
| **Score NPS** | Score Net Promoter de la campagne (−100 à +100) | Quelle est la santé de nos relations clients ? Comment évoluons-nous par rapport à la période précédente ? | Établir une référence de santé relationnelle ; déclencher une intervention transverse si le score passe sous le seuil de référence | S | Santé relationnelle |
| **Total des réponses** | Nombre de réponses complètes collectées | Le volume est-il suffisant pour tirer des conclusions fiables ? | Prolonger la campagne ou envoyer des relances avant l'échéance d'analyse | O | Gestion de campagne |
| **Taux de réponse** | % des participants invités ayant complété l'enquête | Les clients s'engagent-ils ? Quels segments sont systématiquement silencieux ? | Cibler les comptes silencieux avec un suivi personnalisé ; diagnostiquer le désengagement avant même l'existence de données NPS | O | Gestion du risque de désabonnement |
| **Récents (30 jours)** | Réponses soumises au cours des 30 derniers jours | Les retours arrivent-ils de façon régulière ou concentrés au lancement ? | Ajuster la cadence des relances ; synchroniser les cycles d'analyse et d'action en conséquence | O | Gestion de campagne |
| **Comptes nécessitant une attention** *(carte KPI)* | Nombre de comptes signalés par l'IA comme nécessitant une réengagement | Combien de clients sont actuellement à risque ? | Escalader vers la direction ; prioriser les actions des responsables de compte | O | Gestion du risque de désabonnement |
| **Signal d'opportunité** | Score agrégé de potentiel de croissance basé sur la distribution NPS | Quelle est notre capacité de croissance organique à partir de la base clients existante ? | Activer les programmes promoteurs (recommandations, études de cas) quand le signal est élevé ; investir dans la reconstruction relationnelle quand il est faible | S | Croissance des comptes |
| **Distribution NPS** | Répartition Promoteurs / Passifs / Détracteurs en nombre et en % | Quelle proportion de clients sont des ambassadeurs fidèles ou à risque ? | Convertir les passifs par le renforcement de la valeur perçue ; traiter les détracteurs individuellement via le succès client | S + O | Santé relationnelle |
| **Comptes nécessitant une attention** *(panneau)* | Liste classée des entreprises à risque élevé avec liens directs vers les réponses | Quels comptes nécessitent une intervention relationnelle cette semaine ? | Déclencher des appels de responsables de compte, des interventions au niveau direction, ou des plans de récupération personnalisés | O | Gestion du risque de désabonnement |
| **Thèmes clés** | Fréquence des sujets mentionnés dans les retours textuels, classée par l'IA | De quoi parlent le plus les clients ? Les thèmes récurrents sont-ils positifs ou négatifs ? | Prioriser la feuille de route produit et les améliorations de service ; valider les points de douleur suspectés avec des preuves tangibles | S | Amélioration produit & service |

---

## Onglet 2 — Intelligence des comptes

| Indicateur / Graphique | Description | Questions auxquelles il répond | Actions qu'il permet d'identifier | Type | Catégorie |
|---|---|---|---|---|---|
| **Tableau d'intelligence des comptes** | Score par entreprise des opportunités (upsell / expansion / recommandation / renouvellement) face aux risques (Critique → Faible), produisant un ratio de santé : Fort potentiel / Équilibré / Risque dominant. Niveau de confiance basé sur le taux et le volume de réponses. | Quels comptes représentent les meilleures opportunités d'expansion ? Lesquels sont à risque ? Où les équipes commerciales doivent-elles concentrer leurs efforts ce trimestre ? | Prioriser les comptes à fort potentiel pour des conversations d'expansion ; construire des plans de récupération pour les comptes à risque dominant ; planifier des points de contact de maintenance pour les comptes équilibrés | S + O | Croissance des comptes / Gestion du risque de désabonnement |

---

## Onglet 3 — Analytique de croissance

| Indicateur / Graphique | Description | Questions auxquelles il répond | Actions qu'il permet d'identifier | Type | Catégorie |
|---|---|---|---|---|---|
| **Distribution de l'ancienneté client** | Répartition des répondants par cohorte d'ancienneté (< 1 an à 10+ ans) | Quel est le profil d'expérience des répondants ? Quelle cohorte est sur- ou sous-représentée ? | Concevoir un engagement différencié par cohorte : programmes d'onboarding pour les nouveaux clients ; reconnaissance de fidélité pour les clients de longue date | S | Cycle de vie client |
| **Analyse des opportunités basée sur le NPS** | Répartition Promoteurs / Passifs / Détracteurs en lien avec le potentiel de croissance | Quel segment NPS freine la croissance organique ? Perdons-nous plus à cause des détracteurs ou de l'échec à convertir les passifs ? | Lancer des campagnes d'activation des promoteurs ; fixer des objectifs de conversion des passifs ; définir des indicateurs de récupération des détracteurs | S | Croissance des comptes |
| **Analyse de sentiment** | Distribution IA du ton positif / neutre / négatif dans tous les retours textuels ouverts *(les deux types d'enquêtes)* | Quelle est la tonalité émotionnelle générale ? Le sentiment négatif progresse-t-il indépendamment du score NPS ? | Escalader si le sentiment négatif s'emballe ; utiliser comme indicateur avancé avant un mouvement du NPS | O | Santé relationnelle |
| **Notes moyennes** | Scores moyens pour la Satisfaction, le Service, la Valeur produit et le Prix | Où sommes-nous les plus forts et où existe-t-il un écart de performance mesurable ? | Cibler le sous-indicateur le plus faible pour une amélioration immédiate ; comparer entre campagnes pour mesurer l'efficacité des interventions | S + O | Amélioration produit & service |
| **Distribution CSAT** *(enquêtes classiques uniquement)* | Distribution des scores de satisfaction client | Dans quelle mesure les clients sont-ils satisfaits d'interactions spécifiques ? Quand les baisses de satisfaction surviennent-elles ? | Identifier les baisses corrélées à des changements produit ou des périodes données ; déclencher une investigation des causes racines | O | Amélioration produit & service |
| **Distribution CES** *(enquêtes classiques uniquement)* | Distribution des scores d'effort client — facilité perçue à travailler avec vous | Créons-nous des frictions dans nos processus ou notre prestation ? | Simplifier l'onboarding, le support ou les processus de demande de service là où l'effort est élevé | O | Amélioration produit & service |
| **Analyse des facteurs d'impact** *(enquêtes classiques uniquement)* | Classement pondéré par fréquence des facteurs cités comme les plus influents sur le NPS (qualité, prix, support, facilité d'utilisation, etc.) | Quels facteurs influencent le plus fortement la fidélité et la détraction ? Sont-ils les mêmes ? | Prioriser l'amélioration des facteurs négatifs à fort impact ; communiquer proactivement et renforcer les facteurs positifs | S | Amélioration produit & service |
| **Statut de recommandation** *(enquêtes classiques uniquement)* | Distribution selon les stades de recommandation : recommande activement → ne recommanderait pas | Combien de clients sont prêts à servir de référence aujourd'hui ? Qu'est-ce qui bloque l'ambassadeuriat ? | Construire un programme de références à partir du segment « recommande activement » ; traiter les freins cités par les clients « ne recommanderait pas » | S | Activation des promoteurs |
| **Corrélation NPS–CSAT–CES** *(enquêtes classiques uniquement)* | Alignement entre les scores NPS, satisfaction et effort par répondant ou segment | Une satisfaction élevée est-elle toujours corrélée à un NPS élevé ? Un faible effort produit-il de la fidélité ? | Investiguer les anomalies : CSAT élevé + NPS faible = client satisfait mais pas enthousiaste ; diagnostiquer si l'effort constitue un frein à l'ambassadeuriat | S | Santé relationnelle |
| **Adoption & satisfaction des fonctionnalités** *(enquêtes classiques uniquement)* | Fréquence d'utilisation, note d'importance et score de satisfaction par fonctionnalité | Quelles fonctionnalités sont très utilisées mais mal évaluées ? Lesquelles sont importantes mais sous-utilisées ? | Concentrer les améliorations produit sur les fonctionnalités à forte importance et faible satisfaction ; créer des programmes d'activation pour les fonctionnalités à forte importance et faible adoption | S | Amélioration produit & service |

---

## Onglet 4 — Aperçu des enquêtes

| Indicateur / Graphique | Description | Questions auxquelles il répond | Actions qu'il permet d'identifier | Type | Catégorie |
|---|---|---|---|---|---|
| **NPS par entreprise cliente** | NPS par entreprise, répartition promoteurs / passifs / détracteurs, moyennes des sous-indicateurs, thèmes principaux, score de risque de désabonnement et résumé IA — détail complet au survol | Comment se porte chaque relation individuelle ? Quelles entreprises tirent le score global vers le bas ? | Construire un plan d'action compte par compte ; préparer les responsables de compte grâce au résumé IA avant les appels clients | O | Gestion du risque de désabonnement / Croissance des comptes |
| **NPS par ancienneté client** | Score NPS par cohorte d'ancienneté avec Promoteurs, Passifs, Détracteurs par groupe | À quel stade du cycle de vie sommes-nous les plus forts ? Où la fidélité décline-t-elle ? | Intervenir plus tôt si les nouveaux clients obtiennent un score faible (lacune d'onboarding) ; créer des programmes de rétention à la cohorte où le NPS se dégrade ; activer les ambassadeurs de longue date | S | Cycle de vie client |

---

## Onglet 5 — Analytique de segmentation

| Indicateur / Graphique | Description | Questions auxquelles il répond | Actions qu'il permet d'identifier | Type | Catégorie |
|---|---|---|---|---|---|
| **NPS par rôle** | NPS ventilé par rôle du répondant (Direction, Manager, Utilisateur final, IT, Finance, etc.) | Les décideurs ressentent-ils les choses différemment des utilisateurs finaux ? Un rôle est-il systématiquement sous-servi ? | Adapter la communication et les messages de valeur par rôle ; investiguer l'ergonomie si le NPS des utilisateurs finaux est faible alors que celui de la direction est élevé | S | Segmentation & Ciblage |
| **NPS par région** | NPS ventilé par région géographique de l'entreprise cliente | Existe-t-il des disparités de performance régionales ? Un marché spécifique est-il sous-servi ? | Ajuster les ressources de service, la couverture du support ou les partenariats locaux par région ; identifier les marchés prêts pour l'expansion | S | Segmentation & Ciblage |
| **NPS par segment client** | NPS ventilé par segment (Entreprise, PME, Marché intermédiaire) | Les grands comptes sont-ils plus ou moins satisfaits que les petits ? Sommes-nous sur- ou sous-investis dans un segment ? | Réallouer les ressources succès client vers les segments sous-performants ; développer des modèles de service différenciés si l'écart NPS par segment est persistant | S | Segmentation & Ciblage |
| **NPS par secteur d'activité** | NPS ventilé par secteur d'activité de l'entreprise cliente | Performons-nous mieux dans certains secteurs ? Où l'adéquation produit-marché est-elle la plus forte ? | Affiner le positionnement commercial vers les secteurs à NPS élevé ; investiguer les lacunes produit ou de service dans les secteurs à faible NPS | S | Stratégie commerciale |
| **Composition Promoteurs / Passifs / Détracteurs** | Composition empilée des catégories NPS sur toutes les dimensions de segmentation simultanément | Où la concentration de détracteurs est-elle la plus élevée ? Quels segments ont la répartition la plus équilibrée ? | Identifier la combinaison de segments à risque le plus élevé pour une intervention ciblée ; construire des plans de récupération par segment | S + O | Segmentation & Ciblage / Gestion du risque de désabonnement |
| **Risque de désabonnement par segment** | Score moyen de risque de désabonnement dérivé par l'IA par segment, commutable : Segment / Rôle / Région | Quel segment concentre le risque de désabonnement le plus élevé ? Le risque est-il concentré selon une dimension particulière ? | Engager proactivement le segment à risque le plus élevé avec des programmes de rétention avant les fenêtres de renouvellement | O | Gestion du risque de désabonnement |
| **Analyse des cohortes par ancienneté** | NPS et satisfaction par cohorte d'ancienneté montrant l'évolution de la qualité relationnelle au fil du cycle de vie | À quel moment la fidélité atteint-elle son pic ou décline-t-elle ? Existe-t-il un effet de « fatigue de l'ancienneté » ? | Repenser l'expérience client aux points de rupture identifiés ; construire une reconnaissance des étapes pour les clients de longue date | S | Cycle de vie client |
| **Décomposition des sous-indicateurs par segment** | Scores moyens de Satisfaction, Service, Valeur produit et Prix par segment, commutable : Rôle / Région / Segment | Un segment évalue-t-il systématiquement le prix plus bas ? Certains rôles perçoivent-ils moins de valeur produit ? | Développer des propositions de valeur spécifiques au segment ; escalader les écarts structurels de prix ou de qualité de service vers la fonction métier concernée | S | Segmentation & Ciblage / Stratégie commerciale |

---

**Catégories d'actions :** Santé relationnelle · Croissance des comptes · Gestion du risque de désabonnement · Amélioration produit & service · Activation des promoteurs · Cycle de vie client · Segmentation & Ciblage · Stratégie commerciale · Gestion de campagne
