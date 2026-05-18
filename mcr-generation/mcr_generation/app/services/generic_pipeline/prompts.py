MAP_PROMPT_TEMPLATE = """\
Tu reçois un extrait du transcript d'une réunion et une consigne.
Extrait UNIQUEMENT les faits, citations, décisions ou éléments de l'extrait
qui sont pertinents pour la consigne.

Consigne :
\"\"\"
{instruction}
\"\"\"

Extrait :
\"\"\"
{chunk_text}
\"\"\"

Règles strictes :
- N'invente rien qui ne soit pas dans l'extrait.
- Ne synthétise pas, ne reformule pas — tu collectes des faits bruts.
- Si rien dans l'extrait ne concerne la consigne, renvoie une liste vide.

Réponds en JSON : {{ "facts": [string, ...] }}.
"""


REDUCE_PROMPT_TEMPLATE = """\
Tu reçois une consigne et une liste de faits collectés depuis l'ensemble d'un transcript.
Rédige un texte en **markdown** qui répond à la consigne en t'appuyant sur ces faits.

Consigne :
\"\"\"
{instruction}
\"\"\"

Faits :
- {facts}

Règles strictes :
- N'invente rien qui ne soit pas dans les faits.
- Tu peux ignorer / omettre les faits redondants ou hors-sujet.
- **N'émets aucun titre de niveau `#` ou `##` au début ou ailleurs.** Le titre de
  la section est ajouté par l'appelant. Tu peux utiliser des sous-titres
  `###`/`####`, du gras, des listes à puces et des paragraphes.
- Sortie : un objet JSON {{ "markdown": string }}, où `markdown` est le corps
  de la section, sans titre top-level.
- Si aucun fait n'est pertinent, renvoie un markdown court qui dit explicitement
  "Aucun élément pertinent dans le transcript".
"""
