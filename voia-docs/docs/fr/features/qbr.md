# Intelligence QBR

L'Intelligence QBR est le module de VOÏA conçu pour transformer les transcriptions de réunions de bilan trimestriel (QBR) en synthèses structurées et pilotées par l'IA. Au lieu de lire manuellement les notes de réunion, votre équipe téléverse la transcription brute et reçoit un Bilan QBR — un document unique couvrant le sentiment de renouvellement, la santé de la relation, la cartographie des parties prenantes, les préoccupations clés et les actions engagées.

**Pour qui :** Responsables customer success, chargés de comptes et directeurs CS qui mènent des entretiens QBR avec leurs clients et ont besoin de capturer, suivre et agir rapidement et de manière cohérente sur les résultats.

---

## Fonctionnement de l'Intelligence QBR

1. Vous téléversez une transcription en texte brut de votre conversation QBR.
2. L'IA de VOÏA lit la transcription, identifie chaque participant et extrait l'intelligence stratégique.
3. L'analyse est stockée sous forme de **Bilan QBR** — un document structuré que vous pouvez consulter, comparer et partager.
4. Chaque bilan QBR d'un client est regroupé, offrant une vue longitudinale de l'évolution de la relation trimestre après trimestre.

---

## Téléversement d'une transcription

### Étape 1 — Accéder à l'Intelligence QBR

Ouvrez la navigation principale et cliquez sur **Intelligence QBR**. Le tableau de bord QBR liste toutes les sessions précédemment téléversées pour votre compte.

### Étape 2 — Cliquer sur Téléverser une transcription

Cliquez sur le bouton **Téléverser une transcription** pour ouvrir le formulaire.

### Étape 3 — Remplir les informations de session

| Champ | Contenu à saisir |
|---|---|
| **Entreprise cliente** | Sélectionnez ou saisissez le nom de l'entreprise cliente. La liste de saisie automatique est tirée de votre base de participants. |
| **Trimestre** | Sélectionnez T1, T2, T3 ou T4. |
| **Année** | Saisissez l'année du QBR (ex. : 2026). |
| **Fichier de transcription** | Téléversez un fichier `.txt` contenant la transcription de la conversation. |

**Exigences du fichier :**

- Format : texte brut (`.txt`) uniquement
- Taille maximale : 500 Ko
- Encodage : UTF-8 (recommandé)
- Contenu : la transcription de la conversation telle qu'exportée depuis votre outil de réunion, ou collée manuellement

**Validation du nom d'entreprise :** Le nom de l'entreprise doit correspondre à un client dans votre base de participants. Si l'entreprise n'est pas répertoriée, ajoutez d'abord un participant pour cette entreprise, puis revenez au formulaire.

### Étape 4 — Soumettre

Cliquez sur **Téléverser & Analyser**. VOÏA enregistre la transcription et la met en file d'attente pour analyse. Vous êtes redirigé vers le tableau de bord QBR où la nouvelle session apparaît avec le badge de statut **En attente**.

---

## Détection des doublons

VOÏA calcule une empreinte unique de chaque fichier de transcription lors du téléversement. Si vous tentez de téléverser le même fichier une deuxième fois — même sous un nom de fichier différent — VOÏA détectera le doublon et affichera un message d'erreur identifiant la session existante. Cela évite tout traitement accidentel en double et maintient un historique propre.

---

## Cycle de vie de l'analyse

Chaque session QBR passe par les statuts suivants :

| Statut | Signification |
|---|---|
| **En attente** | La transcription a été reçue et attend dans la file d'analyse. |
| **En cours** | L'IA de VOÏA lit et analyse activement la transcription. |
| **Terminé** | L'analyse est complète. Le Bilan QBR complet est disponible. |
| **Échec** | L'analyse n'a pas pu être complétée (par exemple, si la transcription était vide ou illisible). Vous recevrez une notification dans l'application. Téléversez un fichier corrigé pour réessayer. |

Vous recevrez une notification dans l'application lorsque l'analyse est terminée ou a échoué. Pour les transcriptions volumineuses, le traitement prend généralement entre quelques secondes et quelques minutes.

---

## Le Bilan QBR

Lorsqu'une session atteint le statut **Terminé**, cliquez sur la ligne de session pour ouvrir le Bilan QBR complet. Le bilan est organisé en sections suivantes.

### Synthèse exécutive

Un paragraphe concis généré par l'IA — pas plus de 300 caractères — qui capture le constat le plus important de la conversation QBR. Rédigé dans la même langue que la transcription. Utilisez-le pour informer rapidement les parties prenantes qui ont besoin du titre avant de lire le document complet.

### Sentiment de renouvellement

VOÏA classe la disposition générale du client envers le renouvellement en l'une des trois valeurs suivantes :

| Sentiment | Signification |
|---|---|
| **Positif** | Le client est satisfait et montre des signaux clairs d'intention de renouveler ou d'élargir la relation. |
| **Neutre** | La relation est stable mais aucun signal fort dans un sens ou dans l'autre n'a été détecté. |
| **À risque** | La transcription contient des signaux de churn — insatisfaction, préoccupations non résolues ou pression concurrentielle — qui mettent le renouvellement en doute. |

Un **Score de confiance de renouvellement** (0–100) accompagne le label de sentiment et reflète la clarté avec laquelle la transcription soutient cette classification.

### Santé de la relation

En complément du sentiment de renouvellement, VOÏA fournit une évaluation plus large de la relation client :

| Santé | Signification |
|---|---|
| **Solide** | Le partenariat fonctionne bien. Les deux parties semblent alignées et engagées. |
| **Stable** | La relation est fonctionnelle mais pas exceptionnelle. Pas de signaux d'alerte majeurs, mais une marge de progression. |
| **Fragile** | Des problèmes importants sont présents. La relation peut être à risque au-delà du renouvellement actuel. |

Un **Score de santé de la relation** (0–100) accompagne cette classification.

### Parties prenantes

Un tableau listant chaque personne identifiée dans la transcription :

- **Nom** — tel qu'il apparaît dans la transcription
- **Rôle** — titre ou fonction (ex. : VP Produit, Responsable customer success)
- **Partie** — si la personne représente le **client**, le **fournisseur** (votre équipe) ou est **inconnue**

Jusqu'à 10 participants sont affichés.

### Préoccupations principales

Jusqu'à cinq préoccupations clés soulevées par le client lors du QBR, rédigées en langage clair. Chaque préoccupation est accompagnée d'une **citation verbatim** — l'extrait le plus court de la transcription qui l'illustre le mieux.

### Points positifs

Jusqu'à cinq signaux positifs de la conversation — victoires, retours satisfaits, compliments sur votre produit ou votre équipe. Chaque point est associé à une citation verbatim.

### Mentions concurrentielles

Liste des concurrents mentionnés lors du QBR, avec le contexte et un niveau de menace :

| Niveau de menace | Signification |
|---|---|
| **Faible** | Le concurrent a été mentionné en passant ou sans urgence. |
| **Moyen** | Le concurrent est évalué ou le client a exprimé de l'intérêt pour son offre. |
| **Élevé** | Le client a fait des comparaisons directes, posé un ultimatum ou envisage activement de changer. |

### Actions engagées

Jusqu'à dix engagements ou actions de suivi identifiés dans la transcription. Chaque action est associée à une citation verbatim.

### Signaux d'expansion

Jusqu'à cinq signaux indiquant que le client pourrait être ouvert à élargir la relation — intérêt pour des fonctionnalités supplémentaires, nouveaux cas d'usage, ou demandes de nouvelles capacités.

### Thèmes clés

Jusqu'à cinq thèmes transversaux ayant émergé de la conversation — par exemple, « complexité d'intégration », « réactivité du support » ou « alignement sur la feuille de route ».

---

## Vue historique par entreprise

Chaque entreprise cliente dispose d'une page d'historique dédiée qui affiche toutes les sessions QBR téléversées pour cette entreprise, de la plus récente à la plus ancienne. Cliquez sur le nom de l'entreprise dans n'importe quelle ligne du tableau de bord QBR pour ouvrir cette vue.

---

## Conseils d'interprétation

**Combinez sentiment et scores de santé.** Un sentiment de renouvellement « Neutre » avec un score de santé faible est plus urgent qu'un sentiment « Neutre » avec un score de santé solide.

**Priorisez les mentions concurrentielles à menace élevée.** Si un concurrent apparaît à un niveau « Élevé » dans deux bilans QBR consécutifs pour le même client, escaladez le compte en interne avant la prochaine conversation de renouvellement.

**Utilisez les actions comme tableau de bord QBR.** Avant le prochain QBR, ouvrez les actions du bilan précédent et confirmez lesquelles ont été réalisées.

**Surveillez les changements dans la composition des parties prenantes.** L'apparition de nouveaux dirigeants C-level absents des sessions précédentes peut signaler une réorganisation interne ou une surveillance exécutive accrue.

**Les scores de confiance guident l'intensité du suivi.** Un score de confiance de renouvellement inférieur à 50 signifie que l'IA n'a pas trouvé de signal directionnel fort — planifiez un appel de vérification direct plutôt que de vous fier uniquement à la transcription.

**La langue est préservée automatiquement.** Si votre QBR a été conduit en français, VOÏA rédigera le bilan dans cette même langue. Les valeurs d'énumération (sentiment de renouvellement, classification de santé, niveau de menace) restent en anglais quelle que soit la langue de la transcription.
