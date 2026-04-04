# Gestion des campagnes

---

## Cycle de vie

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

Par défaut, une seule campagne peut être active à la fois par compte. Si votre équipe a besoin d'exécuter plusieurs campagnes simultanément, l'activation parallèle est disponible sur demande — contactez votre administrateur de compte ou le support VOÏA.

---

## Création d'une campagne

**Étape 1 : Informations de base**
- Nom de la campagne
- Date de début (envoi des invitations)
- Date de fin (dernier jour pour répondre)
- Description (notes internes)

**Étape 2 : Type de sondage**
- **Sondage classique :** Questions fixes
- **Sondage conversationnel :** Conversations pilotées par l'IA

**Étape 3 : Personnalisation**
- Personnaliser les questions
- Définir la durée estimée de complétion
- Ajouter votre image de marque
- **Indices de sujets personnalisés (JSON) :** Guidez optionnellement l'IA vers des sujets spécifiques en saisissant une liste JSON d'indices. Le champ dispose d'un bouton info (?) qui ouvre un exemple formaté illustrant la structure JSON correcte. À l'intérieur de ce panneau d'exemple, un bouton **Copier le JSON** vous permet de copier le modèle directement dans votre presse-papiers pour l'adapter sans avoir à saisir le format manuellement.

**Étape 4 : Assignation des participants**
- Choisir qui reçoit le sondage
- Importer via CSV ou ajouter manuellement

---

## Mode simulation de sondage

Le mode simulation vous permet de vivre l'expérience du sondage exactement comme un répondant, avant l'envoi de toute invitation réelle. C'est une étape obligatoire de la porte de validation — vous ne pouvez pas activer une campagne sans avoir effectué une simulation.

**Ce qu'est la simulation**

La simulation lance un aperçu interactif en direct du sondage, en utilisant le même moteur IA et la même configuration que ceux rencontrés par les vrais répondants. Pour les sondages conversationnels, l'IA mène la conversation complète. Pour les sondages classiques, vous parcourez le questionnaire tel qu'il apparaîtra aux participants.

**Pourquoi elle existe**

La simulation vous protège d'envoyer un sondage mal configuré ou confus à vos clients. Elle donne à votre équipe la certitude que les questions sont bien formulées, que le déroulement est logique et que le sondage se comporte comme prévu — avant qu'une seule invitation ne soit envoyée.

**Comment lancer une simulation**

1. Ouvrir une campagne en état Brouillon ou Prêt
2. Cliquer sur **Simuler** (ou **Aperçu** pour les sondages classiques) dans la vue détail de la campagne
3. Compléter le sondage comme un répondant — essayez différentes réponses pour tester le comportement de relance de l'IA
4. Confirmer la fin de la simulation — le statut de validation passe à **Simulée, non validée**

**Ce que voit le gestionnaire**

Après la simulation, la page détail de la campagne affiche l'horodatage de la simulation et le badge de statut de validation. Le gestionnaire peut alors examiner les résultats et cliquer sur **Valider** pour faire passer le statut à **Prête à activer**.

**Tester différentes personas de répondants**

Pour les sondages conversationnels, vous pouvez exécuter la simulation plusieurs fois en utilisant différentes personas simulées — par exemple, un promoteur satisfait, un passif neutre ou un détracteur frustré — pour vérifier que l'IA adapte bien ses questions de relance à chaque scénario. Chaque exécution met à jour l'horodatage de simulation.

**Prérequis pour l'activation**

Le bouton Activer reste désactivé tant que les deux étapes ne sont pas complètes : la simulation doit être terminée et un gestionnaire doit avoir validé la campagne. Une fois les deux conditions remplies, le bouton Activer devient disponible.

---

## Relances automatiques

VOÏA envoie automatiquement des emails de relance pour augmenter les taux de réponse :

**Rappel mi-campagne**  
Envoyé à mi-parcours de votre campagne (ex. : jour 45 d'une campagne de 90 jours)

**Dernière relance**  
Envoyée 7 à 14 jours avant la clôture de la campagne (vous choisissez)

**Automatique et intelligent** — Aucune intervention manuelle requise.
