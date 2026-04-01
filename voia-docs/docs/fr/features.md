# Fonctionnalités de la plateforme VOÏA (Voix du Client)

VOÏA capture les retours clients via des interactions conversationnelles, transforme chaque réponse en données structurées (NPS, sentiment, drivers, signaux de risque) et agrège les résultats en insights exploitables, à l’échelle des campagnes comme des comptes.

Ce guide couvre l’ensemble des fonctionnalités disponibles dans la plateforme VOÏA.

---

## Intelligence de sondage pilotée par IA

### Moteur de sondage conversationnel

Au lieu de formulaires traditionnels, VOÏA engage des conversations naturelles avec vos clients grâce à l’IA.

**Fonctionnement :**
- Les clients répondent librement, avec leurs propres mots
- L’IA pose des questions de relance pertinentes
- L’échange est fluide et naturel
- Les données sont automatiquement structurées pour l’analyse

**Bénéfices :**
- Taux de complétion plus élevés
- Feedback plus riche et détaillé
- Réduction de la fatigue liée aux sondages
- Détection automatique de la langue

---

### Analyse automatique

VOÏA analyse chaque réponse automatiquement :

**Analyse de sentiment**  
Détecte si le feedback est positif, négatif ou neutre

**Thèmes clés**  
Identifie les sujets principaux mentionnés (ex. : prix, support, fonctionnalités)

**Risque de churn**  
Identifie les clients à risque de départ

**Opportunités de croissance**  
Met en évidence les axes d’amélioration ou d’expansion

**Aucune intervention manuelle requise** — tout est traité automatiquement en arrière-plan

---

### Rapports exécutifs

Les rapports exécutifs regroupent les enseignements clés d’une campagne dans un format prêt à être partagé avec des décideurs.

**Vue KPI**
- Tableau synthétique des indicateurs clés
- Sparklines pour visualiser les tendances
- NPS coloré (vert / orange / rouge)
- Phrase de synthèse générée par IA

**Comparaison de campagnes**
- Comparaison avec campagnes précédentes
- Flèches de tendance (↑ ↓)
- Barre de recherche en temps réel

**Module de tendances**
- 8 graphiques interactifs :
  - NPS dans le temps
  - sentiment
  - volume de réponses
  - taux de complétion
  - churn
  - opportunités de croissance
  - score global
  - évolution des thèmes

**Idéal pour :**
- dirigeants
- comités exécutifs
- parties prenantes

---

## Gestion des campagnes

### Cycle de vie

Chaque campagne suit un processus défini incluant une porte de validation obligatoire entre Prêt et Actif :

**Brouillon** → Créer et configurer le sondage  
**Prêt** → Réviser et compléter la porte de validation  
**[Porte de validation]** → Simuler le sondage, puis le faire valider par un gestionnaire  
**Actif** → Sondage en cours, collecte des réponses  
**Terminé** → Campagne clôturée, rapports finaux disponibles

La liste des campagnes indique le statut actuel de chaque campagne. Une infobulle d'aide sur le cycle de vie est disponible dans l'en-tête de la colonne **Statut** — survolez ou cliquez sur l'en-tête pour voir la description de chaque étape. Cette infobulle apparaît une seule fois au niveau de la colonne, et non sur chaque ligne de campagne. Chaque ligne affiche également des boutons d'action (Voir, Insights, Participants, Exporter, Rapport) dont la largeur est uniforme, ce qui assure une présentation visuelle cohérente quelle que soit la longueur du libellé.

**Porte de validation — obligatoire avant l'activation**

Une campagne en état Prêt ne peut pas être activée tant qu'elle n'a pas franchi une porte de validation en deux étapes. La porte comporte trois statuts possibles :

- **Non simulée** — La campagne n'a pas encore été simulée. La simulation est requise avant que le bouton Activer devienne disponible.
- **Simulée, non validée** — La simulation est terminée, mais un gestionnaire n'a pas encore validé la campagne. La validation est requise avant l'activation.
- **Prête à activer** — Les deux étapes sont complètes. Le bouton Activer est maintenant disponible.

**Une seule campagne active à la fois**

Par défaut, un seul campagne peut être active à la fois par compte. Si votre équipe a besoin d'exécuter plusieurs campagnes simultanément, l'activation parallèle est disponible sur demande — contactez votre administrateur de compte ou le support VOÏA.

---

### Création d’une campagne

**1. Informations**
- Nom
- Dates
- Description

**2. Type de sondage**
- Classique
- Conversationnel

**3. Personnalisation**
- Questions
- Durée estimée
- Branding
- **Indices de sujets personnalisés (JSON) :** Guidez optionnellement l'IA vers des sujets spécifiques en saisissant une liste JSON d'indices. Le champ dispose d'un bouton info (?) qui ouvre un exemple formaté illustrant la structure JSON correcte. À l'intérieur de ce panneau d'exemple, un bouton **Copier le JSON** vous permet de copier le modèle directement dans votre presse-papiers pour l'adapter sans avoir à saisir le format manuellement.

**4. Participants**
- Import CSV ou ajout manuel

---

### Mode simulation de sondage

Le mode simulation vous permet de vivre l'expérience du sondage exactement comme un répondant, avant l'envoi de toute invitation réelle. C'est une étape obligatoire de la porte de validation — vous ne pouvez pas activer une campagne sans avoir effectué une simulation.

**Lancement d'une simulation**

1. Ouvrir une campagne en état Brouillon ou Prêt
2. Cliquer sur **Simuler** (ou **Aperçu** pour les sondages classiques)
3. Compléter le sondage comme un répondant
4. Confirmer la fin de la simulation — le statut de validation passe à **Simulée, non validée**

**Validation par le gestionnaire**

Après la simulation, le gestionnaire examine la campagne et clique sur **Valider** pour passer le statut à **Prête à activer**.

**Prérequis pour l'activation**

Le bouton Activer reste désactivé tant que les deux étapes ne sont pas complètes : la simulation doit être terminée et un gestionnaire doit avoir validé la campagne.

---

### Relances automatiques

- Rappel mi-campagne
- Dernière relance avant clôture

---

## Gestion des participants

### Base centralisée

- Nom / email
- Entreprise
- Rôle
- Champs personnalisés

---

### Ajout

**Manuel** ou **CSV**

Validation automatique (doublons, erreurs)

---

### Segmentation

- Entreprise
- Rôle
- Ancienneté

---

## Analytics & Business Intelligence

### Dashboard

- NPS
- taux de réponse
- sentiment
- campagnes actives
- réponses récentes

Mise à jour en temps réel

---

### NPS

- Promoteurs (9-10)
- Passifs (7-8)
- Détracteurs (0-6)

**NPS = % Promoteurs - % Détracteurs**

---

### Analyse de sentiment

- Positif
- Neutre
- Négatif

---

### Thèmes clés

Graphique des sujets principaux, classés et colorés par sentiment.

---

### Insights de campagne (5 onglets)

**Overview**
Résumé de haut niveau de la campagne :
- Score NPS avec courbe de tendance sur la période
- Taux de réponse et nombre total de réponses
- Répartition du sentiment (positif, neutre, négatif) sous forme de graphique en anneau
- Graphique de distribution NPS montrant la proportion de Promoteurs, Passifs et Détracteurs parmi l'ensemble des répondants
- Synthèse IA en langage clair décrivant le constat le plus important

**Growth**
- dynamique de croissance / rétention

**Account Intelligence**
- score par compte
- priorisation

**Survey Insights**
Plonge dans le contenu des retours clients :
- Graphique des thèmes clés
- Répartition des réponses question par question
- Extraits verbatim étiquetés avec le sentiment et les thèmes associés
- Tableau NPS par entreprise où chaque nom de société est un lien cliquable qui mène directement à la page Account Insights de ce compte, permettant de passer des données du sondage à une vue complète du compte en un seul clic

**Segmentation**
- analyse par groupe

---

### Account Intelligence

Score global par compte basé sur :
- NPS
- sentiment
- churn
- opportunités

**Niveaux de confiance :**
- élevé / moyen / faible / insuffisant

**Badges de risque**
Chaque ligne affiche un badge de risque — **Critique**, **Élevé**, **Moyen** ou **Faible** — résumant le niveau de risque global du compte. Survoler le badge ouvre une infobulle qui explique précisément pourquoi ce niveau de risque a été attribué, en décrivant les signaux spécifiques (comme un NPS faible, un risque de churn élevé ou une tendance de sentiment négative) qui ont conduit à cette classification.

**Enrichissement au survol**
Survoler une ligne de compte ouvre une infobulle qui charge des détails supplémentaires à la demande. L'infobulle comprend les principaux thèmes mentionnés par les répondants de ce compte, une ventilation par sous-métrique couvrant la satisfaction, le service, la tarification et la valeur produit, le score moyen de risque de churn calculé par l'IA, ainsi qu'un résumé en langage clair généré par l'IA synthétisant l'ensemble des retours du compte. Cela permet de garder le tableau principal lisible tout en offrant de la profondeur quand vous en avez besoin.

---

### Comparaison de campagnes

Comparer plusieurs campagnes :

- KPI
- tendances
- évolution par compte

---

### Account Insights

Vue détaillée par entreprise :
- NPS
- churn
- thèmes
- résumé IA

---

## Communication & Emails

### Configuration email

- VOÏA (par défaut)
- SMTP personnalisé

---

### Templates

- branding automatique
- logo
- message personnalisé

---

### Invitations

- en masse
- individuelles
- relances
- tracking

---

## Gestion des utilisateurs

### Rôles

- Admin
- Manager
- Viewer

---

### Ajout utilisateurs

Invitation email automatique

---

### Limites licence

- Core / Plus / Pro

---

## Branding

### Logo

Upload + affichage automatique

---

### White-label

- domaine personnalisé
- branding complet

---

## Sécurité & confidentialité

### Accès sécurisé

- tokens uniques
- expiration
- sans login

---

### Protection des données

- anonymisation
- chiffrement
- isolation multi-tenant

---

### Audit

Suivi complet des actions

---

## Licence

Voir page dédiée

---

## Mobile & accessibilité

- responsive
- WCAG 2.1

---

## Export & intégration

- CSV / Excel / PDF
- API (Plus / Pro)

---

## Performance

- rapide (<500ms)
- scalable
- 99.9% uptime

---

## Support

- documentation
- aide intégrée
- support email : support@rivvalue.com