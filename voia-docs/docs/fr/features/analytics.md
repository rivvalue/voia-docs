# Analytics & Business Intelligence

---

## Dashboard

Votre tableau de bord principal affiche :
- **Score NPS :** Net Promoter Score (-100 à +100)
- **Taux de réponse :** Pourcentage de participants ayant répondu
- **Répartition du sentiment :** Positif, neutre, négatif
- **Campagnes actives :** Sondages en cours
- **Réponses récentes :** Derniers retours reçus

**Mise à jour en temps réel :** Le tableau de bord se rafraîchit automatiquement

---

## NPS

Le NPS mesure la fidélité client sur une échelle de -100 à +100.

**Calcul :**
- **Promoteurs (9-10) :** Clients satisfaits qui vous recommandent
- **Passifs (7-8) :** Satisfaits mais peu enthousiastes
- **Détracteurs (0-6) :** Clients insatisfaits à risque de départ

**NPS = % Promoteurs - % Détracteurs**

**Références sectorielles :**
- Excellent : 50+
- Bon : 30-50
- Moyen : 10-30
- À améliorer : En dessous de 10

---

## Analyse de sentiment

Chaque réponse est analysée pour détecter l'émotion :
- **Positif :** Le client est satisfait
- **Neutre :** Retour factuel, sans émotion marquée
- **Négatif :** Le client est frustré ou déçu

**Tendances visuelles :** Suivez l'évolution du sentiment dans le temps

---

## Thèmes clés

VOÏA extrait automatiquement les principaux sujets mentionnés par les clients et les présente sous forme de graphique à barres classé. Chaque barre représente un thème (par exemple, « tarification », « qualité du support » ou « onboarding ») et est colorée selon le sentiment dominant — vert pour un retour majoritairement positif, rouge pour majoritairement négatif, et gris pour neutre ou mixte. Les barres sont ordonnées du plus mentionné au moins mentionné. Chaque barre affiche à la fois le nombre brut de réponses et le pourcentage de répondants ayant abordé ce sujet. Sous le graphique, une phrase d'interprétation résume le constat le plus important.

**Utilisez les thèmes clés pour :**
- Repérer les préoccupations récurrentes avant qu'elles ne deviennent sérieuses
- Prioriser les axes d'amélioration de votre produit ou service
- Suivre l'évolution d'un thème après des changements apportés

---

## Insights de campagne (5 onglets)

Lorsque vous ouvrez une campagne et cliquez sur **Insights**, vous accédez à un espace analytique en cinq onglets. Chaque onglet se concentre sur une dimension différente de vos résultats. Vous pouvez naviguer librement entre les onglets sans perdre votre position.

**Overview**
Résumé de haut niveau de la campagne :
- Score NPS avec courbe de tendance sur la période
- Taux de réponse et nombre total de réponses
- Répartition du sentiment (positif, neutre, négatif) sous forme de graphique en anneau
- Graphique de distribution NPS montrant la proportion de Promoteurs, Passifs et Détracteurs parmi l'ensemble des répondants
- Synthèse IA en langage clair décrivant le constat le plus important

**Growth Analytics**
Se concentre sur les signaux d'expansion et de rétention :
- Comptages de Promoteurs, Passifs et Détracteurs avec variations hebdomadaires
- Volume de réponses dans le temps sous forme de graphique en aires
- Entonnoir de complétion montrant combien de participants ont ouvert le sondage vs. répondu
- Cartes de mise en évidence des segments avec le NPS le plus élevé et le plus faible

**Account Intelligence**
Vue par entreprise du risque et des opportunités sur l'ensemble des comptes de la campagne :
- Score de balance pour chaque entreprise — un indicateur unique combinant NPS, sentiment, risque de churn et opportunité de croissance
- Niveau de confiance (Élevé, Moyen, Faible ou Insuffisant) accompagnant chaque score
- Liste de comptes triable pour identifier rapidement les comptes les plus à risque ou les plus susceptibles d'expansion
- Survolez une ligne de compte pour charger à la demande les thèmes détaillés, sous-métriques et extraits verbatim
- Consultez la section [Account Intelligence](#account-intelligence) ci-dessous pour une explication complète

**Survey Insights**
Plonge dans le contenu des retours clients :
- Graphique des thèmes clés
- Répartition des réponses question par question
- Extraits verbatim étiquetés avec le sentiment et les thèmes associés
- Tableau NPS par entreprise où chaque nom de société est un lien cliquable qui mène directement à la page Account Insights de ce compte, permettant de passer des données du sondage à une vue complète du compte en un seul clic

**Segmentation Insights**
Décompose les résultats par groupes :
- NPS et sentiment segmentés par entreprise, rôle ou ancienneté
- Comparaison de segments côte à côte pour identifier les groupes les plus satisfaits et ceux nécessitant attention
- Contrôles de filtre pour isoler un segment et explorer ses thèmes et réponses

---

## Account Intelligence

Account Intelligence vous donne une vue compte par compte des performances de vos relations clients.

**Score de balance**
Chaque compte reçoit un score de balance — un indicateur unique combinant le NPS, le sentiment, le risque de churn et les signaux d'opportunité de croissance. Un score positif indique une relation saine ; un score négatif est un signal d'alerte nécessitant attention.

**Niveaux de confiance**
Chaque score est accompagné d'un niveau de confiance indiquant le poids à lui accorder :

- **Élevé** — Suffisamment de réponses et de données pour être statistiquement fiable. Vous pouvez agir en confiance sur ce score.
- **Moyen** — Signal raisonnable, mais envisagez un contact direct pour confirmer.
- **Faible** — Peu de données disponibles. Considérez-le comme un indicateur précoce plutôt qu'une conclusion ferme.
- **Insuffisant** — Trop peu de réponses pour générer un score significatif. La ligne du compte reste visible pour vous permettre de décider d'un suivi proactif.

**Badges de risque**
Chaque ligne affiche un badge de risque — **Critique**, **Élevé**, **Moyen** ou **Faible** — résumant le niveau de risque global du compte. Survoler le badge ouvre une infobulle qui explique précisément pourquoi ce niveau de risque a été attribué, en décrivant les signaux spécifiques (comme un NPS faible, un risque de churn élevé ou une tendance de sentiment négative) qui ont conduit à cette classification. Cela permet de comprendre non seulement quel est le niveau de risque, mais aussi pourquoi il a été attribué.

**Enrichissement au survol**
Survoler une ligne de compte ouvre une infobulle qui charge des détails supplémentaires à la demande. L'infobulle comprend les principaux thèmes mentionnés par les répondants de ce compte, une ventilation par sous-métrique couvrant la satisfaction, le service, la tarification et la valeur produit, le score moyen de risque de churn calculé par l'IA, ainsi qu'un résumé en langage clair généré par l'IA synthétisant l'ensemble des retours du compte. L'infobulle affiche également une **ventilation pondérée par l'influence** qui reflète le niveau hiérarchique de chaque répondant — les retours des dirigeants C-level et des VP sont mis en valeur pour vous indiquer si les signaux proviennent de décideurs ou d'utilisateurs finaux.

**Utilisez Account Intelligence pour :**
- Prioriser les comptes à risque pour votre équipe customer success
- Identifier les opportunités d'expansion avec les comptes sains et engagés
- Allouer les efforts de suivi là où ils auront le plus d'impact

---

## Scoring pondéré par l'influence

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

## Comparaison de campagnes

La comparaison de campagnes vous permet de placer deux campagnes ou plus côte à côte pour comprendre comment vos résultats ont évolué dans le temps. Elle est particulièrement utile lorsque vous avez mené une campagne plusieurs fois — par exemple, un cycle annuel ou trimestriel — et souhaitez savoir si les choses s'améliorent, stagnent ou se dégradent.

**Comment l'utiliser :**
- Ouvrez la section **Rapports exécutifs** d'une campagne et faites défiler jusqu'au tableau de comparaison, ou accédez-y directement depuis l'espace **Insights**
- Sélectionnez les campagnes précédentes à inclure dans la comparaison
- Utilisez la barre de recherche en temps réel pour filtrer les lignes par nom de métrique

**Ce que vous voyez :**
- Un tableau de métriques affichant chaque KPI (NPS, sentiment, taux de réponse, risque de churn, et autres) pour chaque campagne comparée
- Un indicateur directionnel à côté de chaque valeur — une flèche vers le haut signifie une amélioration, vers le bas un déclin, et un tiret une stabilité
- Un tableau de comparaison par compte montrant, pour chaque entreprise, le delta NPS entre la campagne actuelle et la précédente

**Quand utiliser la comparaison de campagnes :**
- À la fin de chaque cycle de sondage pour informer votre direction des progrès
- Lorsque vous suspectez qu'un changement produit ou une amélioration de service a eu un effet sur le sentiment client
- Pour identifier les comptes dont les scores ont significativement baissé depuis la dernière campagne, afin d'intervenir rapidement

---

## Account Insights

Account Insights est un panneau par entreprise qui apparaît sur la page **Réponses par entreprise** lorsque vous cliquez sur un nom d'entreprise. Il vous donne une vue concentrée de tout ce que VOÏA sait sur ce compte dans la campagne en cours.

**Le panneau comprend :**
- **Répartition NPS** — le nombre de Promoteurs, Passifs et Détracteurs de cette entreprise, avec leur NPS calculé
- **Barres de progression des sous-métriques** — indicateurs visuels pour le risque de churn et l'opportunité de croissance, sur une échelle de 0 à 100
- **Jauge de risque de churn** — une jauge proéminente mettant en évidence les comptes les plus à risque de ne pas renouveler
- **Pills de sujets** — petites étiquettes affichant les thèmes les plus fréquemment mentionnés par les répondants de cette entreprise ; cliquer sur une pill filtre la liste de réponses pour n'afficher que les réponses mentionnant ce sujet
- **Synthèse IA repliable** — un paragraphe généré par l'IA qui synthétise toutes les réponses de cette entreprise en un récit en langage clair ; il explique le sentiment dominant, les préoccupations clés et les signaux positifs notables ; dépliez-le pour un briefing rapide avant un appel client

**Utilisez Account Insights lorsque :**
- Vous vous préparez pour un entretien de revue ou de renouvellement client
- Votre équipe customer success souhaite comprendre les retours d'une entreprise spécifique sans lire toutes les réponses individuelles
- Vous devez décider d'escalader un compte à la direction en fonction de son sentiment et de son risque de churn

---

## Tableau de bord Comptes stratégiques

Le tableau de bord Comptes stratégiques est une vue dédiée qui se concentre exclusivement sur vos relations clients les plus prioritaires — celles dont les participants sont classés en niveau **Stratégique** ou **Clé** dans la base de données des participants. Il est conçu pour les responsables customer success et les chargés de comptes qui doivent surveiller leurs comptes les plus importants sans être noyés dans la liste complète.

**Comment y accéder**

Ouvrez le tableau de bord principal et cliquez sur l'onglet **Comptes stratégiques** (signalé par une icône de couronne). La vue se charge automatiquement pour la campagne active. Si vous souhaitez voir les données d'une autre campagne, vous pouvez passer un identifiant de campagne via l'URL. Si aucune campagne n'est spécifiée et qu'une campagne est active, le tableau de bord utilise la campagne active par défaut.

**Ce que le tableau de bord affiche**

En haut de la vue, un bandeau de KPI vous donne un aperçu instantané de la santé globale de votre portefeuille de comptes stratégiques :

- **Comptes à risque** — le nombre de comptes stratégiques présentant au moins un facteur de risque actif
- **Opportunités de croissance** — le nombre de comptes stratégiques présentant au moins un signal de croissance positif
- **Sans réponse** — le nombre de comptes stratégiques n'ayant pas encore soumis de réponse dans la campagne en cours
- **Taux de couverture** — le pourcentage de comptes stratégiques ayant répondu jusqu'à présent

En dessous du bandeau de KPI, la liste des comptes affiche tous les comptes de niveau Stratégique et Clé dans la campagne, triés du risque de churn le plus élevé au plus faible. Chaque ligne affiche :

- **Nom de l'entreprise** et son niveau client (Stratégique ou Clé)
- **Badge de risque** (Critique, Élevé, Moyen ou Faible) dérivé du risque de churn pondéré par l'influence
- **Indicateur de score de balance** indiquant si le compte est dominé par les risques, équilibré ou dominé par les opportunités
- **Nombre de réponses** pour la campagne en cours — les comptes sans réponse sont signalés visuellement
- **Enrichissement au survol** avec la même infobulle détaillée disponible dans Account Intelligence, incluant la ventilation pondérée des niveaux hiérarchiques

**Différence avec Account Intelligence**

Account Intelligence affiche toutes les entreprises ayant soumis au moins une réponse dans la campagne. Le tableau de bord Comptes stratégiques affiche toutes les entreprises de niveau Stratégique ou Clé, qu'elles aient répondu ou non — vous pouvez ainsi voir d'un coup d'œil quels sont vos comptes les plus importants qui n'ont pas encore participé au sondage.

**Utilisez Comptes stratégiques pour :**
- Passer en revue la santé de vos comptes principaux avant une réunion QBR ou un comité de direction
- Identifier quels comptes clés n'ont pas répondu et pourraient nécessiter une prise de contact proactive
- Prioriser le temps de votre équipe customer success
