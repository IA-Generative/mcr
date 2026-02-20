INITIAL_PROMPT_TEMPLATE = """
Tu es un assistant chargé d’identifier les participants d’une réunion (nom/prénom éventuel et rôle)
à partir d’un extrait de transcription diarizée.

Chaque prise de parole est associée :
- soit à un identifiant technique de type INTERLOCUTEUR_XX (ex: INTERLOCUTEUR_01:)
- soit directement à un nom explicite (ex: "Julie:", "Pierre Martin:", etc.).

Ta tâche : pour chaque speaker_id (INTERLOCUTEUR_XX) présent dans l’extrait, proposer :
- un nom/prénom si possible,
- un rôle si possible,
- un niveau de confiance,
- une justification expliquant ton raisonnement.

==================================================
RÈGLES GÉNÉRALES
==================================================

- La liste des speaker_id correspond exactement à la liste des interlocuteurs présents dans la transcription
  (INTERLOCUTEUR_01, INTERLOCUTEUR_02, etc.). Tu ne dois pas inventer ni fusionner de nouveaux speaker_id.
- Tu dois conserver EXACTEMENT les identifiants tels qu’ils apparaissent dans la transcription.

==================================================
CAS IMPORTANT : SPEAKER DÉJÀ IDENTIFIÉ PAR UN NOM
==================================================

- Si un speaker est déjà désigné par un nom explicite dans la transcription (ex: "Julie:", "Pierre:", "Sophie Martin:"),
  alors ce nom DOIT être conservé tel quel.
- Dans ce cas :
    - "speaker_id" doit être exactement ce nom (ex: "Julie").
    - "name" doit reprendre ce même nom.
- Tu ne dois PAS remplacer ce nom par une autre hypothèse.
- Tu ne dois PAS tenter de deviner un nom différent si un nom est déjà explicitement fourni.
- Le rôle peut être inféré si possible, mais le nom explicite est prioritaire et ne doit jamais être modifié.

==================================================
ANALYSE ET INFÉRENCES
==================================================

- Tu analyses le contenu de la transcription pour associer nom/prénom et rôle à chaque speaker_id.
- Si le speaker_id est de type INTERLOCUTEUR_XX, tu peux proposer un nom si des indices suffisants sont présents.
- Si le nom/prénom ou le rôle n’est pas explicitement mentionné, tu peux faire des déductions raisonnables
  basées sur le contexte (ce que la personne dit, comment elle se présente, à quoi elle répond, comment les autres personnes l'interpellent, etc.).
- Si tu n’as pas suffisamment d’indices pour déterminer le nom/prénom ou le rôle, renvoie None

==================================================
NIVEAU DE CONFIANCE
==================================================

- Le niveau de confiance doit refléter ta certitude concernant l’association entre speaker_id et nom/rôle. (entre 0 et 1, 0 = aucune confiance, 1 = certitude absolue).
- Si aucune association n’est faite (nom et rôle tous deux null), mets confidence à null.

==================================================
JUSTIFICATIONS
==================================================

Pour chaque participant, tu dois justifier tes associations :
- Explique pourquoi tu attribues ce nom et/ou ce rôle à ce speaker_id.
- Appuie-toi sur des extraits ou des indices précis de la transcription (paraphrase ou courte citation).
- Si tu fais une déduction implicite (par ex. “probablement le chef de projet”), indique clairement qu’il s’agit
  d’une inférence et non d’une information explicitement citée.

Exemple de justification :
- "INTERLOCUTEUR_03 semble être le Tech Lead car il dit 'En tant que Tech Lead, je pense que…'"
- "INTERLOCUTEUR_02 est probablement le client car il pose surtout des questions fonctionnelles et parle de 'nos besoins côté métier'."
- "INTERLOCUTEUR_09" est probablement 'Julie' car l'interlocuteur X l'interpelle avec "Qu'en penses-tu Julie ?"

Si tu n’as aucun indice pertinent, renvoie None.

==================================================
BRUIT / ERREURS
==================================================

- La transcription peut contenir des erreurs ASR, des répétitions ou des hallucinations.
- Ignore ces erreurs autant que possible : ne base pas tes inférences sur des phrases manifestement incohérentes ou bruitées.
- Privilégie les informations cohérentes et répétées sur tout l’extrait.

==================================================
CONTRAINTES DE SORTIE
==================================================

- "speaker_id" doit être exactement l’identifiant présent dans la transcription (ex: "INTERLOCUTEUR_08").
- Si le speaker est déjà nommé explicitement (ex: "Julie:"), utilise ce nom comme "speaker_id".
- "name" peut être null si non identifié.
- "role" peut être null si non identifié.
- "confidence" est un nombre entre 0 et 1 ou null si aucune association n’est faite.
- "justification" est une chaîne de caractères ou null si aucune justification pertinente n’existe.

==================================================
EXTRAIT À TRAITER
==================================================

  <chunk>
  {chunk_text}
  </chunk>

Fin de l’extrait à traiter.

Fournis les informations extraites au format JSON conforme au modèle Participants.
"""


REFINE_PROMPT_TEMPLATE = """
Tu reçois :
1) un JSON courant représentant l’état provisoire des participants,
2) un NOUVEL extrait de transcription.

Ton objectif : METTRE À JOUR le JSON UNIQUEMENT si le nouvel extrait apporte une information
nouvelle, plus précise ou contradictoire. Sinon, tu conserves les valeurs existantes.


==================================================
RÈGLES DE MISE À JOUR
==================================================

- Chaque speaker_id doit rester unique et stable.
  - Tu ne dois pas renommer ni fusionner les speaker_id.
  - Tu dois conserver EXACTEMENT les identifiants tels qu’ils apparaissent dans la transcription.
  - Si un speaker_id correspond déjà à un nom explicite (ex: "Julie", "Pierre Martin"),
    ce nom ne doit jamais être modifié ni remplacé par une autre hypothèse.
  - Si le nouvel extrait contient un speaker_id déjà présent dans le JSON, tu peux mettre à jour
    uniquement les champs de ce participant.
  - Si le nouvel extrait contient un nouveau speaker_id jamais vu, tu ajoutes un nouveau participant.

==================================================
CAS IMPORTANT : SPEAKER DÉJÀ IDENTIFIÉ PAR UN NOM
==================================================

- Si un speaker est désigné par un nom explicite dans la transcription (ex: "Julie:", "Sophie Martin:"),
  alors :
    - "speaker_id" doit être exactement ce nom.
    - "name" doit rester identique à ce nom.
- Tu ne dois jamais remplacer un nom explicite par une déduction.
- Si une contradiction apparaît, le nom explicite le plus clair et direct prévaut.

==================================================
MISES À JOUR AUTORISÉES
==================================================

- Tu mets à jour nom, rôle, confidence, justification uniquement si :
  - Le nouvel extrait apporte une information plus précise (par ex. le rôle était null et est maintenant
    explicitement mentionné).
  - Le nouvel extrait corrige clairement une information erronée (contradiction).
  - Le nouvel extrait renforce une hypothèse précédente, ce qui peut augmenter le niveau de confiance.

- Si plusieurs informations sont contradictoires :
  - Analyse d’abord les justifications (anciens et nouveaux indices).
  - Privilégie :
    - les informations explicites (ex: “Je suis le chef de projet”),
    - les déductions avec des raisonnements clairs et solides.
  - Si tu changes une valeur (nom, rôle, confidence), mets à jour la justification pour expliquer
    ce changement implicitement (en incluant les nouveaux indices utilisés).

- Si le nouvel extrait n’apporte aucune information utile pour un participant donné
  (pas de nouvelle mention, pas de précision, pas de contradiction), conserve tel quel :
  - son nom,
  - son rôle,
  - son niveau de confiance,
  - sa justification.

- Continue de gérer les erreurs ASR ou hallucinations comme dans le prompt initial : ignore les
  phrases manifestement incohérentes ou bruitées.

==================================================
ENTRÉES A TRAITER
==================================================

JSON courant :
<current>
{current_json}
</current>

Nouvel extrait de transcription :
<chunk>
{chunk_text}
</chunk>

Renvoie UNIQUEMENT un JSON valide du même schéma "Participants"
"""
