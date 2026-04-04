# Intelligence QBR

L'Intelligence QBR est le module dédié de VOÏA pour transformer les transcriptions de Quarterly Business Review (revues trimestrielles d'affaires) en synthèses structurées et alimentées par l'IA. Au lieu de lire manuellement les notes de réunion, votre équipe téléverse la transcription brute et reçoit un **QBR Brief** — un document unique couvrant le sentiment de renouvellement, la santé relationnelle, la cartographie des parties prenantes, les préoccupations clés et les engagements pris.

**Pour qui :** Responsables customer success, chargés de comptes et directeurs CS qui conduisent des QBR avec leurs clients et ont besoin de capturer, suivre et agir sur les résultats rapidement et de façon cohérente.

---

## Fonctionnement de l'Intelligence QBR

1. Vous téléversez une transcription en texte brut de votre conversation QBR.
2. L'IA de VOÏA lit la transcription, identifie chaque participant et extrait les informations stratégiques.
3. L'analyse est stockée sous forme de **QBR Brief** — un document structuré que vous pouvez consulter, comparer et partager.
4. Chaque QBR brief pour un client donné est regroupé, offrant une vue longitudinale de l'évolution de la relation trimestre après trimestre.

---

## Téléversement d'une transcription

### Étape 1 — Accéder à l'Intelligence QBR

Ouvrez la navigation principale et cliquez sur **Intelligence QBR**. Le tableau de bord QBR liste toutes les sessions précédemment téléversées pour votre compte.

### Étape 2 — Cliquer sur Téléverser une transcription

Cliquez sur le bouton **Téléverser une transcription** pour ouvrir le formulaire.

### Étape 3 — Remplir les informations de session

| Champ | Quoi saisir |
|---|---|
| **Entreprise cliente** | Sélectionnez ou saisissez le nom de l'entreprise cliente. La liste de saisie automatique est tirée de votre base de participants. |
| **Trimestre** | Sélectionnez Q1, Q2, Q3 ou Q4. |
| **Année** | Saisissez l'année du QBR (ex. : 2026). |
| **Fichier de transcription** | Téléversez un fichier `.txt` contenant la conversation QBR. |

**Exigences du fichier :**

- Format : texte brut (`.txt`) uniquement
- Taille maximale : 500 Ko
- Encodage : UTF-8 (recommandé)
- Contenu : la transcription de la conversation telle qu'exportée depuis votre outil de réunion, ou collée manuellement

**Validation du nom d'entreprise :** Le nom de l'entreprise doit correspondre à un client dans votre base de participants. Si l'entreprise n'est pas listée, ajoutez d'abord un participant pour cette entreprise, puis revenez au formulaire de téléversement.

### Étape 4 — Soumettre

Cliquez sur **Téléverser et analyser**. VOÏA enregistre la transcription et la place en file d'attente pour analyse. Vous êtes redirigé vers le tableau de bord QBR où la nouvelle session apparaît avec le badge de statut **En attente**.

---

## Détection des doublons

VOÏA calcule une empreinte unique de chaque fichier de transcription lors du téléversement. Si vous tentez de téléverser le même fichier une deuxième fois — même sous un nom de fichier différent — VOÏA détecte le doublon et affiche un message d'erreur identifiant la session existante. Cela évite les traitements accidentels en double et maintient un historique propre.

---

## Cycle de vie de l'analyse

Chaque session QBR passe par les statuts suivants :

| Statut | Signification |
|---|---|
| **En attente** | La transcription a été reçue et attend dans la file d'analyse. |
| **En cours** | L'IA de VOÏA lit et analyse activement la transcription. |
| **Terminé** | L'analyse est complète. Le QBR Brief complet est disponible. |
| **Échoué** | L'analyse n'a pas pu être complétée (par exemple, si la transcription était vide ou illisible). Vous recevrez une notification dans l'application. Téléversez à nouveau un fichier corrigé pour réessayer. |

Vous recevrez une notification dans l'application lorsque l'analyse est terminée ou a échoué. Pour les transcriptions volumineuses, le traitement prend généralement entre quelques secondes et quelques minutes.

---

## Le QBR Brief

Lorsqu'une session atteint le statut **Terminé**, cliquez sur la ligne de session pour ouvrir le QBR Brief complet. Le brief est organisé en sections suivantes.

### Résumé exécutif

Un paragraphe concis généré par l'IA — d'au plus 300 caractères — qui capture le point le plus important de la conversation QBR. Rédigé dans la même langue que la transcription. Utilisez-le pour informer les parties prenantes qui ont besoin du titre avant de lire le document complet.

### Sentiment de renouvellement

VOÏA classe la disposition générale du client envers le renouvellement en une des trois valeurs :

| Sentiment | Signification |
|---|---|
| **Positif** | Le client est satisfait et montre des signaux clairs d'intention de renouveler ou d'étendre la relation. |
| **Neutre** | La relation est stable mais aucun signal fort dans l'un ou l'autre sens n'a été détecté. |
| **À risque** | La transcription contient des signaux de churn — insatisfaction, préoccupations non résolues ou pression concurrentielle — qui mettent le renouvellement en doute. |

Un **Score de confiance de renouvellement** (0–100) accompagne le libellé de sentiment et reflète la clarté avec laquelle la transcription soutient cette classification. Un score de 90 ou plus signifie que l'IA a trouvé des preuves solides et non ambiguës ; un score plus faible suggère que le signal était mixte ou subtil.

### Santé relationnelle

En complément du sentiment de renouvellement, VOÏA fournit une évaluation plus large de la relation client :

| Santé | Signification |
|---|---|
| **Forte** | Le partenariat fonctionne bien. Les deux parties semblent alignées et engagées. |
| **Stable** | La relation est fonctionnelle mais pas exceptionnelle. Aucun signal d'alarme majeur, mais des marges de progression. |
| **Fragile** | Des problèmes importants sont présents. La relation pourrait être à risque au-delà du renouvellement en cours. |

Un **Score de santé relationnelle** (0–100) accompagne cette classification, mesuré sur la même échelle de confiance.

### Parties prenantes

Un tableau listant chaque personne identifiée dans la transcription, avec :

- **Nom** — tel qu'il apparaît dans la transcription
- **Rôle** — titre de poste ou fonction (ex. : VP Produit, Responsable Customer Success)
- **Côté** — si la personne représente l'organisation **cliente**, le **vendeur** (votre équipe) ou est **inconnue**

VOÏA analyse les étiquettes de tour de parole, les listes de participants et les auto-présentations pour construire cette liste automatiquement. Jusqu'à 10 participants sont affichés.

**Conseil :** La liste des parties prenantes vous aide à comprendre la voix qui pèse le plus dans la conversation. Une préoccupation soulevée par un dirigeant C-level a une signification stratégique différente de la même préoccupation soulevée par un utilisateur final.

### Principales préoccupations

Jusqu'à cinq préoccupations clés soulevées par le client lors du QBR, rédigées en langage clair. Chaque préoccupation est accompagnée d'une **citation verbatim** — l'extrait le plus court de la transcription qui la soutient le mieux. Si aucune citation source claire n'existe, le champ est laissé vide.

Utilisez cette section pour :
- Prioriser les actions de suivi pour votre équipe customer success
- Préparer des réponses avant votre prochain point client
- Signaler les préoccupations récurrentes qui apparaissent sur plusieurs sessions QBR

### Points positifs

Jusqu'à cinq signaux positifs issus de la conversation — victoires, retours satisfaits, compliments sur votre produit ou votre équipe. Chaque point est associé à une citation verbatim de soutien.

Utilisez cette section pour :
- Renforcer ce qui fonctionne bien
- Identifier des témoignages adaptés à des études de cas ou des références
- Partager les victoires avec votre équipe interne ou la direction

### Mentions concurrentielles

Une liste des concurrents mentionnés lors du QBR, avec le contexte dans lequel ils ont été mentionnés et un niveau de menace :

| Niveau de menace | Signification |
|---|---|
| **Faible** | Le concurrent a été mentionné en passant ou sans urgence. |
| **Moyen** | Le concurrent est évalué ou le client a exprimé un intérêt pour son offre. |
| **Élevé** | Le client a fait des comparaisons directes, posé un ultimatum, ou envisage activement de changer. |

Suivre les mentions concurrentielles sur les sessions QBR aide votre équipe à repérer quels concurrents gagnent du terrain et où votre positionnement doit être renforcé.

### Points d'action

Jusqu'à dix engagements spécifiques ou actions de suivi identifiés dans la transcription — ce qui a été convenu lors de la réunion, promis par l'une ou l'autre partie, ou explicitement signalé comme prochaine étape. Chaque point d'action est associé à une citation verbatim de soutien.

Utilisez cette section comme liste de contrôle après le QBR. Vous pouvez copier les points d'action dans votre CRM, votre outil de gestion de projet ou votre plan de compte pour vous assurer que rien ne passe à travers les mailles.

### Signaux d'expansion

Jusqu'à cinq signaux indiquant que le client pourrait être ouvert à l'élargissement de la relation — intérêt pour des fonctionnalités supplémentaires, nouveaux cas d'usage, mentions de croissance de leur équipe, ou demandes de nouvelles capacités. Ces signaux sont distincts des points positifs ; ils pointent spécifiquement vers des opportunités d'upsell ou de cross-sell.

### Thèmes clés

Jusqu'à cinq thèmes généraux qui ont émergé de la conversation — par exemple, « complexité d'intégration », « réactivité du support » ou « alignement sur la feuille de route ». Les thèmes sont plus larges que les préoccupations individuelles ; ils représentent les fils conducteurs récurrents de la réunion.

---

## Vue de l'historique par entreprise

Chaque entreprise cliente dispose d'une page d'historique dédiée qui affiche toutes les sessions QBR téléversées pour cette entreprise, de la plus récente à la plus ancienne. Cliquez sur le nom de l'entreprise sur n'importe quelle ligne de session dans le tableau de bord QBR pour ouvrir cette vue.

La vue historique vous permet de :
- Suivre l'évolution du sentiment de renouvellement et de la santé relationnelle dans le temps
- Repérer les préoccupations récurrentes qui persistent d'un trimestre à l'autre
- Comparer les points d'action des sessions précédentes pour voir lesquels ont été résolus

---

## Conseils pour interpréter les résultats

**Combinez sentiment et scores de santé.** Un sentiment de renouvellement « Neutre » associé à un faible score de santé relationnelle est plus urgent qu'un sentiment « Neutre » avec un score de santé fort. Lisez les deux signaux ensemble.

**Priorisez les mentions concurrentielles à menace élevée.** Si un concurrent apparaît au niveau de menace « Élevé » dans deux QBR briefs consécutifs pour le même client, escaladez le compte en interne avant la prochaine conversation de renouvellement.

**Utilisez les points d'action comme tableau de bord QBR.** Avant le prochain QBR, ouvrez les points d'action du brief précédent et confirmez lesquels ont été complétés. Cela responsabilise les deux parties et signale au client que vous suivez vos engagements.

**Surveillez l'évolution de la composition des parties prenantes.** Si de nouveaux dirigeants C-level apparaissent dans un QBR qui n'étaient pas présents lors des sessions précédentes, cela peut signaler un changement interne chez le client — une réorganisation, un nouveau sponsor, ou une surveillance exécutive accrue de la relation.

**Les scores de confiance guident l'intensité de votre suivi.** Un score de confiance de renouvellement inférieur à 50 signifie que l'IA n'a pas pu trouver un signal directionnel fort. Dans ces cas, planifiez un appel de vérification direct plutôt que de vous fier uniquement à la transcription.

**La langue est préservée automatiquement.** Si votre QBR s'est déroulé en anglais, en allemand ou dans une autre langue, VOÏA rédigera le brief — préoccupations, points positifs, points d'action, résumé — dans cette même langue. Les valeurs d'énumération (sentiment de renouvellement, classification de santé, niveau de menace) restent en anglais quelle que soit la langue de la transcription.
