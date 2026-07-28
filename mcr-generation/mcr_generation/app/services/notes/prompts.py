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
    - Repérer s'il y a une PROCHAINE RÉUNION ou un ÉVÉNEMENT À VENIR auquel les participants prendront part (réunion, point, démo, revue, atelier, comité...), y compris quand un tel événement voit sa date FIXÉE ou CHANGÉE dans les notes (ex. "démo repoussée au 14/10").
    - Extraire :
      - date (format JJ/MM/AAAA ou relatif : "mardi prochain", "dans deux semaines", etc.),
      - heure (HH:MM ou relatif : "le matin", "même heure", etc.),
      - purpose : but ou nature de cet événement (une phrase très courte),
      - confidence : entre 0.0 et 1.0,
      - justification : quelques mots expliquant sur quels indices tu t'appuies.

    Règles :
    - Ne considère que l'événement à venir (pas les événements passés).
    - Un CHANGEMENT DE DATE d'un événement à venir (report, avancement) est une information à extraire : renvoie la NOUVELLE date et l'objet concerné.
    - N'invente rien : si les notes n'évoquent aucun événement à venir ni aucune date, mets date, time et purpose à null avec une faible confidence. C'est attendu et normal.

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


EXTRACT_MINUTES_HINT_PROMPT_TEMPLATE = """
Tu structures les NOTES d'un participant à une réunion en thèmes et décisions.
Tu ne résumes pas une transcription : tu réorganises UNIQUEMENT ce que l'utilisateur a noté.

Cette extraction sert d'INDICE ("hint") pour un pipeline downstream qui s'appuie aussi sur la transcription complète.
Les notes étant courtes et incomplètes, retourner themes: [] est attendu et normal si rien n'y est exploitable.

Règle n°1 — ZÉRO invention :
- N'ajoute aucun thème, décision, responsable (owner) ni échéance (due) absent des notes.
- En cas de doute sur un champ, mets null. Mieux vaut une décision sans owner qu'un owner inventé.
- Le summary lui-même ne reformule que ce qui est écrit : il n'ajoute aucun contexte extérieur.

Décision vs remarque :
- Ne mets dans "decisions" que ce qui ACTE quelque chose : un choix tranché ou une action à faire.
- Une simple observation, un constat ou une question ouverte reste dans le summary du thème, jamais dans decisions.

Regroupement :
- Regroupe les notes par thème cohérent (title court + summary optionnel de 1 à 3 phrases).
- Une note isolée sans thème clair va dans un thème générique (ex. "Divers"), pas dans une décision fabriquée.

Champs d'une décision :
- item : la décision/action formulée clairement et brièvement.
- owner : uniquement si un responsable est nommé ou trivialement déductible de la note (ex. "Yanis -> SSO").
  N'extrapole pas un owner depuis un pronom ambigu ou un simple rôle. Sinon null.
- due : recopie l'échéance telle qu'écrite (ex. "15/09", "fin de semaine", "S+2"), sans la normaliser. Sinon null.

Langue : français ; title et item courts et actionnables.

Schéma cible : une liste "themes" ; chaque thème = title + summary (optionnel) + decisions (liste de : item, owner, due).

Exemple (ce qu'il faut produire) :
Notes : "MVP : pas de messagerie (Claire). SSO à livrer 15/09 - Yanis. Budget +20k à valider. Perfs API un peu lentes ?"
-> themes:
  - title: "Périmètre MVP"
    summary: "La messagerie est exclue du MVP."
    decisions:
      - item: "Exclure la messagerie du MVP", owner: "Claire", due: null
      - item: "Livrer le SSO", owner: "Yanis", due: "15/09"
  - title: "Budget"
    summary: null
    decisions:
      - item: "Valider une rallonge de 20k€", owner: null, due: null
  - title: "Performances API"
    summary: "Interrogation sur des lenteurs de l'API."
    decisions: []
    (NB : "un peu lentes ?" est une remarque, PAS une décision -> reste dans summary)

Notes à structurer :
<notes>
{notes_content}
</notes>

Renvoie le résultat strictement au format JSON validant le schéma attendu : MinutesContent.
Si les notes ne contiennent aucun contenu de réunion exploitable, renvoie themes: [].
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
- Si la liste des éléments extraits de la transcription est **vide**, ne conclus pas à l'absence de contenu : rédige le résultat **à partir de ces notes uniquement**, sans rien inventer au-delà de leur contenu.
"""
