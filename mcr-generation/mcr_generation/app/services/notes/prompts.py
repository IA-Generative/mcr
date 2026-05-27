EXTRACT_INTENT_PROMPT_TEMPLATE = """
    Tu dois extraire l'en-tête d'une réunion à partir des notes prises pendant le meeting (texte humain synthétique).

    Objectif :
    1. Identifier ou déduire le titre de la réunion (court et spécifique).
    2. Résumer l'objet de la réunion en une phrase très concise.
    3. Donner un niveau de confiance (0.0 à 1.0) indiquant ton degré de certitude.
    4. Fournir une justification brève : quels éléments du texte t'ont permis cette extraction.

    Règles :
    - Utilise uniquement les informations explicitement présentes dans les notes ou une inférence raisonnable fondée sur le sujet dominant.
    - Les notes sont courtes et incomplètes : si aucun titre n'est mentionné, déduis le titre le plus plausible (ex : "Point budgétaire", "Daily Stand Up").
    - L'objet doit être bref, factuel, et refléter la finalité principale évoquée.
    - Si aucune info exploitable n'est présente, renvoie les champs à null avec une faible confiance.

    Notes prises pendant le meeting :
    <notes>
    {notes_content}
    </notes>

    Renvoie un JSON strictement conforme au modèle Intent.
"""


EXTRACT_NEXT_MEETING_PROMPT_TEMPLATE = """
    Notes prises pendant un meeting (texte humain synthétique).

    Tâche :
    - Repérer s'il y a une PROCHAINE RÉUNION décidée ou clairement envisagée.
    - Extraire :
      - date (format JJ/MM/AAAA ou relatif : "mardi prochain", "dans deux semaines", etc.),
      - heure (HH:MM ou relatif : "le matin", "même heure", etc.),
      - purpose : but principal de cette prochaine réunion (une phrase très courte),
      - confidence : entre 0.0 et 1.0,
      - justification : quelques mots expliquant sur quels indices tu t'appuies.

    Règles :
    - Ne considère que la prochaine réunion à venir (pas les réunions passées).
    - Utilise les mentions explicites en priorité ("on se revoit", date/heure, "prochain point", etc.).
    - Les notes peuvent ne rien mentionner sur ce point : dans ce cas, mets date, time et purpose à null avec une faible confidence. C'est attendu et normal.

    Notes prises pendant le meeting :
    <notes>
    {notes_content}
    </notes>

    Renvoie un JSON conforme au modèle NextMeeting.
"""


EXTRACT_TOPICS_HINT_PROMPT_TEMPLATE = """
Tu reçois les notes prises pendant un meeting (texte humain synthétique).
Identifie les sujets discutés ainsi que les décisions associées qui y apparaissent.

Cette extraction sert d'INDICE ("hint") pour un pipeline downstream qui s'appuie aussi sur la transcription complète.
Les notes étant courtes et incomplètes, retourner des listes vides est attendu et normal si l'information n'y figure pas.
Ne devine pas, n'invente pas : ne retourne un sujet ou une décision QUE si les notes le mentionnent explicitement.

Pour chaque sujet identifié dans les notes, fournis :
- Le titre du sujet (clair et concis)
- Les détails (sous-sujet si pertinent, faits atomiques importants, max 5)
- Les décisions liées (décision claire avec décideur et actions de suivi si mentionnés)
- Le niveau de confiance

RÈGLES de remplissage :
- facts : lister uniquement les faits explicitement présents dans les notes
- facts_justification, facts_quotes : null si non disponibles dans les notes (cas fréquent)
- decision_facts, followup_actions : remplir uniquement si présents dans les notes
- next_steps : prochaines étapes mentionnées dans les notes, non redondantes avec les décisions

Notes prises pendant le meeting :
<notes>
{notes_content}
</notes>

Renvoie le résultat strictement au format JSON validant le schéma attendu : TopicsContent.
Retourner topics=[] et next_steps=[] est valide si les notes ne contiennent pas d'information exploitable.
"""


EXTRACT_DISCUSSIONS_HINT_PROMPT_TEMPLATE = """
Tu reçois les notes prises pendant un meeting (texte humain synthétique).
Identifie les discussions détaillées qui s'y tiennent, avec les informations clés et les décisions associées.

Cette extraction sert d'INDICE ("hint") pour un pipeline downstream qui s'appuie aussi sur la transcription complète.
Les notes étant courtes et incomplètes, retourner une liste vide est attendu et normal si l'information n'y figure pas.
Ne devine pas, n'invente pas : ne retourne une discussion QUE si les notes la mentionnent explicitement.

Pour chaque discussion identifiée dans les notes, fournis :
- Le titre de la discussion (court, factuel, sans intention ni interprétation)
- Les key_ideas : 1 à 5 bullets factuels et concrets issus des notes
- Les décisions prises (format : "[Décideur] a décidé de [action]." si décideur connu)
- Les actions concrètes (format : "[Action] - [Responsable] - [Échéance]" quand disponibles)
- Les focus_points (risques, questions ouvertes, validations à obtenir, suivi de mise en œuvre) — liste vide si aucun

RÈGLES :
- Respecter l'ordre chronologique d'apparition dans les notes si perceptible
- Ne pas redonder : chaque information UNE SEULE FOIS
- Champs vides (listes vides) si les notes ne contiennent pas l'information correspondante

Notes prises pendant le meeting :
<notes>
{notes_content}
</notes>

Renvoie le résultat strictement au format JSON validant le schéma attendu : DiscussionsContent.
Retourner detailed_discussions=[] est valide si les notes ne contiennent pas d'information exploitable.
"""


EXTRACT_CUSTOM_FACTS_PROMPT_TEMPLATE = """
Tu reçois des notes prises pendant un meeting (texte humain synthétique) et une CONSIGNE libre rédigée par l'auteur du compte-rendu personnalisé.

Tâche :
- Extraire UNIQUEMENT les faits, citations ou éléments présents dans les notes qui sont pertinents pour la consigne.
- Pas de reformulation, pas de synthèse, pas d'interprétation.
- Cette extraction sert d'INDICE ("hint") pour un pipeline downstream qui s'appuie aussi sur la transcription complète.

Règles strictes :
- N'invente rien qui ne soit pas explicitement présent dans les notes.
- Si rien dans les notes ne concerne la consigne, renvoie une liste vide. C'est attendu et normal.
- Un fact = une phrase courte et factuelle, en français.

Consigne :
<instruction>
{instruction}
</instruction>

Notes prises pendant le meeting :
<notes>
{notes_content}
</notes>

Renvoie le résultat strictement au format JSON : une liste de faits courts en français dans le champ "facts".
"""


NOTES_SECTION_TEMPLATE = """\
## Notes du rédacteur (signal humain)

{notes_block}

### Comment utiliser ces notes
- Les notes ci-dessus sont une **information supplémentaire et plus fiable** que les extraits de transcription. Elles signalent les éléments que le rédacteur du meeting a jugés notables.
- Si une information apparaît dans la transcription mais **pas** dans les notes : tu la **gardes** ; les notes ne sont pas exhaustives et leur silence sur un point n'invalide pas la transcription.
- Si une information apparaît dans **les notes** et **pas dans la transcription** : tu peux légitimement l'inclure dans le résultat final si elle a du sens dans le contexte du meeting.
- Si une information de la transcription **contredit** une information des notes : **les notes priment**, c'est leur version que tu retiens.
"""
