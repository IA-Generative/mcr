INITIAL_PROMPT_TEMPLATE = """
Tu es un assistant chargé d'identifier les participants d'une réunion (nom/prénom éventuel et rôle)
à partir d'un extrait de transcription diarisée, où chaque prise de parole est associée à un identifiant
de locuteur (par ex. INTERLOCUTEUR_01:, INTERLOCUTEUR_02:, etc.).

Ta tâche : pour chaque speaker_id (INTERLOCUTEUR_XX) présent dans l'extrait, proposer :
- un nom/prénom si possible,
- un rôle si possible,
- un niveau de confiance,
- une justification expliquant ton raisonnement.

==================================================
RÈGLES GÉNÉRALES
==================================================

- La liste des speaker_id correspond exactement à la liste des interlocuteurs présents dans la transcription.
  Tu ne dois pas inventer ni fusionner de nouveaux speaker_id.
- Tu analyses le contenu de la transcription pour associer nom/prénom et rôle à chaque speaker_id.
- Si tu n'as pas suffisamment d'indices, renvoie name=null et role=null.
- Il vaut mieux ne pas nommer un interlocuteur que lui attribuer un mauvais nom.

==================================================
SOURCES D'IDENTIFICATION VALIDES
==================================================

Un nom peut être attribué à INTERLOCUTEUR_XX UNIQUEMENT dans les cas suivants :

1. AUTO-PRÉSENTATION : INTERLOCUTEUR_XX se présente lui-même.
   ✓ "Je m'appelle Julie Martin, je suis chef de projet."
   ✓ "Bonjour, c'est Thomas."

2. PRÉSENTATION PAR UN TIERS : un autre interlocuteur présente explicitement INTERLOCUTEUR_XX.
   ✓ INTERLOCUTEUR_01 : "Je vous présente Julie, notre chef de projet."
      → Julie est attribuée à INTERLOCUTEUR_XX qui prend la parole juste après, ou à celui désigné.
   ✓ INTERLOCUTEUR_01 : "Marc, tu peux nous expliquer ?"
      → Marc est attribué à INTERLOCUTEUR_XX qui répond.

3. INTERPELLATION DIRECTE : un interlocuteur s'adresse à INTERLOCUTEUR_XX en le nommant,
   et INTERLOCUTEUR_XX répond (confirmation implicite).
   ✓ INTERLOCUTEUR_01 : "Qu'en penses-tu, Julie ?"
      INTERLOCUTEUR_02 : "Je pense que..." → Julie est attribuée à INTERLOCUTEUR_02.

==================================================
SOURCES D'IDENTIFICATION INVALIDES — NE PAS UTILISER
==================================================

Les cas suivants NE constituent PAS une source valide pour attribuer un nom à INTERLOCUTEUR_XX :

1. MENTION D'UN TIERS : INTERLOCUTEUR_XX parle de quelqu'un d'autre sans se présenter.
   ✗ INTERLOCUTEUR_01 : "Jean m'a dit que le projet avançait bien."
      → Ne pas attribuer Jean à INTERLOCUTEUR_01.

2. CITATION OU RAPPORTAGE : INTERLOCUTEUR_XX cite ou rapporte les paroles de quelqu'un.
   ✗ INTERLOCUTEUR_01 : "Comme disait Marie, il faut avancer."
      → Ne pas attribuer Marie à INTERLOCUTEUR_01.

3. DÉSIGNATION PAR LE RÔLE SEUL : un interlocuteur est désigné uniquement par son titre ou rôle,
   sans que son nom soit mentionné.
   ✗ "Le lieutenant va nous expliquer la situation."
      → Rôle enregistrable si pertinent, mais aucun nom à attribuer.

==================================================
GESTION DES CAS AMBIGUS
==================================================

1. NOM ET SURNOM : si INTERLOCUTEUR_XX est désigné à la fois par un vrai nom et un surnom,
   utilise le vrai nom.
   ✓ "Je te présente Loulou, enfin, Louis Garnier." → name = "Louis Garnier"

2. HOMONYMES : si deux speaker_id partagent le même prénom sans nom de famille pour les différencier,
   ajoute un suffixe numérique pour les distinguer.
   ✓ INTERLOCUTEUR_02 → name = "Thomas 1"
     INTERLOCUTEUR_05 → name = "Thomas 2"
   La numérotation suit l'ordre d'apparition dans la transcription.

3. INCERTITUDE : si tu hésites entre deux noms ou que l'indice est trop faible, préfère name=null
   plutôt qu'un nom incertain. Reflète cette incertitude dans la confidence.

==================================================
NIVEAU DE CONFIANCE
==================================================

La confidence reflète ta certitude sur l'association speaker_id ↔ nom/rôle (entre 0 et 1) :
- 0.9 - 1.0 : auto-présentation explicite ou présentation directe sans ambiguïté.
- 0.7 - 0.9 : interpellation directe avec réponse immédiate.
- 0.5 - 0.7 : déduction contextuelle raisonnée (indices cohérents mais indirects).
- 0.0 - 0.5 : indice très faible ou unique, forte incertitude.
- null       : aucune association faite (name et role tous deux null).

==================================================
JUSTIFICATIONS
==================================================

Pour chaque participant, justifie ton association :
- Appuie-toi sur des indices précis de la transcription (paraphrase, pas de citation mot pour mot).
- Distingue clairement ce qui est explicite de ce qui est une inférence.
- Si aucun indice pertinent : justification = null.

Exemples :
✓ "INTERLOCUTEUR_03 se présente comme Tech Lead en début d'extrait."
✓ "INTERLOCUTEUR_02 répond après avoir été interpellé par son prénom 'Julie' — inférence."
✓ "Aucun indice permettant d'identifier INTERLOCUTEUR_04." → null

Exemple de cas négatif complet (aucun indice) :
- name = null, role = null, confidence = null, justification = null.

==================================================
BRUIT / ERREURS ASR
==================================================

- La transcription peut contenir des erreurs, répétitions ou hallucinations.
- N'utilise pas une phrase isolée, incohérente ou manifestement bruitée comme seul indice d'identification.
- Privilégie les informations cohérentes et confirmées par plusieurs indices.

==================================================
EXTRAIT À TRAITER
==================================================

<chunk>
{chunk_text}
</chunk>
"""


REFINE_PROMPT_TEMPLATE = """
Tu reçois :
1) un JSON courant représentant l'état provisoire des participants,
2) un NOUVEL extrait de transcription.

Ton objectif : METTRE À JOUR le JSON UNIQUEMENT si le nouvel extrait apporte une information
nouvelle, plus précise ou contradictoire. Sinon, tu conserves les valeurs existantes.

==================================================
RÈGLES DE MISE À JOUR
==================================================

- Chaque speaker_id doit rester unique et stable. Tu ne dois pas renommer ni fusionner les speaker_id.
- Si le nouvel extrait contient un speaker_id jamais vu, tu ajoutes un nouveau participant
  (cela peut signaler une anomalie de diarisation — à traiter comme un participant ordinaire).

Tu peux mettre à jour name, role, confidence, justification UNIQUEMENT si :
  a) Le nouvel extrait apporte une information plus précise (ex: rôle était null, maintenant explicite).
  b) Le nouvel extrait corrige clairement une information erronée (contradiction explicite).
  c) Le nouvel extrait apporte un indice supplémentaire cohérent avec l'hypothèse existante :
     dans ce cas, augmente la confidence de manière proportionnelle à la solidité du nouvel indice.

En cas de contradiction entre deux informations :
  - Privilégie les informations explicites (auto-présentation, présentation directe) sur les déductions.
  - Si les deux sont des déductions, garde celle avec la justification la plus solide.
  - Mets à jour la justification pour refléter le raisonnement final (en intégrant les nouveaux indices).

==================================================
SOURCES D'IDENTIFICATION VALIDES ET INVALIDES
==================================================

Les mêmes règles que pour l'extraction initiale s'appliquent ici. Pour rappel :

VALIDES :
✓ Auto-présentation de INTERLOCUTEUR_XX.
✓ Présentation explicite de INTERLOCUTEUR_XX par un tiers.
✓ Interpellation directe de INTERLOCUTEUR_XX par son nom, suivie d'une réponse.

INVALIDES :
✗ INTERLOCUTEUR_XX mentionne un nom dans une citation ou en parlant d'un tiers.
✗ INTERLOCUTEUR_XX est désigné uniquement par son rôle ou titre, sans nom associé.

==================================================
GESTION DES CAS AMBIGUS
==================================================

1. NOM ET SURNOM : si le nouvel extrait révèle que le nom attribué était un surnom,
   remplace-le par le vrai nom et mets à jour la justification.

2. HOMONYMES : si le nouvel extrait révèle qu'un autre speaker_id partage le même prénom :
   - Renomme les deux participants en "<Prénom> 1" / "<Prénom> 2" selon leur ordre d'apparition
     dans la transcription globale.
   - Mets à jour la justification des deux participants concernés.

3. ACCUMULATION DE JUSTIFICATION : ne remplace pas la justification précédente,
   mais enrichis-la avec les nouveaux indices apportés par cet extrait.
   Format suggéré : "[Extrait N] <nouvel indice>" ajouté à la justification existante.

==================================================
PARTICIPANTS DÉJÀ RÉSOLUS
==================================================

Si un participant a une confidence >= 0.9 et un name non null, considère son identification
comme stable. Ne la remets en cause que si le nouvel extrait apporte une contradiction explicite
et non ambiguë (ex: auto-présentation avec un nom différent).

==================================================
BRUIT / ERREURS ASR
==================================================

- Ignore les phrases manifestement incohérentes ou isolées.
- Ne révise pas une association existante sur la base d'un seul indice bruité.

==================================================
ENTRÉES À TRAITER
==================================================

JSON courant :
<current>
{current_json}
</current>

Nouvel extrait de transcription :
<chunk>
{chunk_text}
</chunk>
"""
