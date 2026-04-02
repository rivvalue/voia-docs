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

Account Intelligence vous donne une vue compte par compte des performances de vos relations clients.

**Score de balance**
Chaque compte reçoit un score de balance — un indicateur unique combinant le NPS, le sentiment, le risque de churn et les signaux d'opportunité de croissance. Un score positif indique une relation saine ; un score négatif est un signal d'alerte.

**Niveaux de confiance**
Chaque score est accompagné d'un niveau de confiance indiquant le poids à lui accorder :

- **Élevé** — Suffisamment de réponses et de données pour être statistiquement fiable. Vous pouvez agir en confiance sur ce score.
- **Moyen** — Signal raisonnable, mais envisagez un contact direct pour confirmer.
- **Faible** — Peu de données disponibles. Considérez-le comme un indicateur précoce plutôt qu'une conclusion ferme.
- **Insuffisant** — Trop peu de réponses pour générer un score significatif. La ligne du compte reste visible pour vous permettre de décider d'un suivi proactif.

**Badges de risque**
Chaque ligne affiche un badge de risque — **Critique**, **Élevé**, **Moyen** ou **Faible** — résumant le niveau de risque global du compte. Survoler le badge ouvre une infobulle qui explique précisément pourquoi ce niveau de risque a été attribué, en décrivant les signaux spécifiques (comme un NPS faible, un risque de churn élevé ou une tendance de sentiment négative) qui ont conduit à cette classification.

**Enrichissement au survol**
Survoler une ligne de compte ouvre une infobulle qui charge des détails supplémentaires à la demande. L'infobulle comprend les principaux thèmes mentionnés par les répondants de ce compte, une ventilation par sous-métrique couvrant la satisfaction, le service, la tarification et la valeur produit, le score moyen de risque de churn calculé par l'IA, ainsi qu'un résumé en langage clair généré par l'IA synthétisant l'ensemble des retours du compte. L'infobulle affiche également une **ventilation pondérée par l'influence** qui reflète le niveau hiérarchique de chaque répondant — les retours des dirigeants C-level et des VP sont mis en valeur pour vous indiquer si les signaux proviennent de décideurs ou d'utilisateurs finaux. Cela permet de garder le tableau principal lisible tout en offrant de la profondeur quand vous en avez besoin.

---

### Scoring pondéré par l'influence

Le moteur de scoring de VOÏA pondère chaque réponse en fonction du niveau hiérarchique de la personne qui l'a soumise. Les retours des parties prenantes seniors — celles qui disposent de la plus grande autorité sur le renouvellement, l'expansion et les décisions contractuelles — ont un poids proportionnellement plus élevé que les retours des utilisateurs finaux dans le calcul des signaux de risque et de croissance.

VOÏA reconnaît les niveaux hiérarchiques suivants, du plus influent au niveau de référence : dirigeants C-level, VP/Directeur, Manager, Team Lead, et utilisateur final / collaborateur individuel. Les répondants C-level et VP ont le poids le plus élevé ; les utilisateurs finaux servent de référence.

**Impact sur les signaux de risque**
Lorsqu'un dirigeant C-level donne un NPS faible ou signale son insatisfaction, le score de risque de churn du compte augmente nettement plus que pour le même score soumis par un utilisateur final. Cela reflète la réalité : un dirigeant insatisfait a l'autorité de résilier ou de ne pas renouveler un contrat, ce qui n'est généralement pas le cas d'un utilisateur final.

**Impact sur les signaux de croissance**
Les retours positifs des parties prenantes seniors — un VP exprimant une forte satisfaction, un dirigeant C-level indiquant une volonté d'élargir la relation — sont pondérés plus fortement dans les calculs d'opportunités de croissance. Cela aide vos équipes de customer success et de vente à prioriser les comptes où les signaux d'expansion sont véritablement stratégiques.

**Où voir l'effet**
- **Badge de risque** sur chaque ligne de compte dans Account Intelligence reflète le risque de churn pondéré par l'influence
- **Indicateur de score de balance** intègre les totaux d'opportunités et de risques pondérés par l'influence
- **Infobulle d'enrichissement au survol** affiche une ventilation pondérée pour voir si les signaux viennent de décideurs ou d'utilisateurs finaux
- **Signaux de croissance** dans l'onglet Growth Analytics reflètent la contribution pondérée des promoteurs seniors

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

### Tableau de bord Comptes stratégiques

Le tableau de bord Comptes stratégiques est une vue dédiée qui se concentre exclusivement sur vos relations clients les plus prioritaires — celles dont les participants sont classés en niveau **Stratégique** ou **Clé** dans la base de données des participants. Il est conçu pour les responsables customer success et les chargés de comptes qui doivent surveiller leurs comptes les plus importants sans être noyés dans la liste complète des comptes.

**Comment y accéder**

Ouvrez le tableau de bord principal et cliquez sur l'onglet **Comptes stratégiques** (signalé par une icône de couronne). La vue se charge automatiquement pour la campagne active. Si vous souhaitez voir les données d'une autre campagne, vous pouvez passer un identifiant de campagne via l'URL. Si aucune campagne n'est spécifiée et qu'une campagne est active, le tableau de bord utilise la campagne active par défaut.

**Ce que le tableau de bord affiche**

En haut de la vue, un bandeau de KPI vous donne un aperçu instantané de la santé globale de votre portefeuille de comptes stratégiques :

- **Comptes à risque** — le nombre de comptes stratégiques présentant au moins un facteur de risque actif
- **Opportunités de croissance** — le nombre de comptes stratégiques présentant au moins un signal de croissance positif
- **Sans réponse** — le nombre de comptes stratégiques n'ayant pas encore soumis de réponse dans la campagne en cours (un manque de couverture à adresser)
- **Taux de couverture** — le pourcentage de comptes stratégiques ayant répondu jusqu'à présent

En dessous du bandeau de KPI, la liste des comptes affiche tous les comptes de niveau Stratégique et Clé dans la campagne, triés du risque de churn le plus élevé au plus faible. Chaque ligne affiche :

- **Nom de l'entreprise** et son niveau client (Stratégique ou Clé)
- **Badge de risque** (Critique, Élevé, Moyen ou Faible) dérivé du risque de churn pondéré par l'influence
- **Indicateur de score de balance** indiquant si le compte est dominé par les risques, équilibré ou dominé par les opportunités
- **Nombre de réponses** pour la campagne en cours — les comptes sans réponse sont signalés visuellement pour indiquer où la couverture manque
- **Enrichissement au survol** avec la même infobulle détaillée disponible dans Account Intelligence, incluant la ventilation pondérée des niveaux hiérarchiques des répondants de ce compte

**Différence avec Account Intelligence**

Account Intelligence (dans l'espace de travail Insights) affiche toutes les entreprises ayant soumis au moins une réponse dans la campagne. Le tableau de bord Comptes stratégiques affiche toutes les entreprises de niveau Stratégique ou Clé, qu'elles aient répondu ou non — vous pouvez ainsi voir d'un coup d'œil quels sont vos comptes les plus importants qui n'ont pas encore participé au sondage.

**Utilisez Comptes stratégiques pour :**
- Passer en revue la santé de vos comptes principaux avant une réunion QBR ou un comité de direction
- Identifier quels comptes clés n'ont pas répondu et pourraient nécessiter une prise de contact proactive
- Prioriser le temps de votre équipe customer success

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