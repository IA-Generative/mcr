INITIAL_PROMPT_TEMPLATE = """
    Extrait de transcription d'une réunion.

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
    - Si aucune info exploitable, mets date, time et purpose à null avec une faible confidence.

    Extrait :
    <chunk>
    {chunk_text}
    </chunk>

    Retourne un JSON conforme au modèle NextMeeting.
"""

REFINE_PROMPT_TEMPLATE = """
    Tu reçois :
    - un JSON courant décrivant la prochaine réunion,
    - un NOUVEL extrait de transcription, plus tard dans la réunion.

    Tâche :
    - Mettre à jour le JSON SEULEMENT si ce nouvel extrait apporte :
      - une date/heure plus précise ou plus fiable,
      - un purpose plus clair,
      - ou contredit clairement une info précédente.

    Règle clé :
    - Le NOUVEL extrait a PLUS DE POIDS que les précédents.
      S'il corrige une date/heure/objet, tu DOIS remplacer l'ancienne valeur.

    Confiance :
    - Augmente-la si le nouvel extrait confirme ou précise (formulations du type "on valide", "c'est noté").
    - Réduis-la si tout devient flou ou incertain.
    - Mets à jour la justification en citant brièvement les nouveaux indices.

    JSON courant :
    <current>
    {current_json}
    </current>

    Nouvel extrait :
    <chunk>
    {chunk_text}
    </chunk>

    Retourne UNIQUEMENT le JSON mis à jour, conforme au modèle NextMeeting.
"""
