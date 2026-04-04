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

Par défaut, un seul campagne peut être active à la fois par compte. Si votre équipe a besoin d'exécuter plusieurs campagnes simultanément, l'activation parallèle est disponible sur demande — contactez votre administrateur de compte ou le support VOÏA.

---

## Création d'une campagne

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

## Mode simulation de sondage

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

## Relances automatiques

- Rappel mi-campagne
- Dernière relance avant clôture
