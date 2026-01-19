INITIAL_PROMPT_TEMPLATE = """
    Tu dois extraire l'en-tête d'une réunion à partir d'un extrait de transcription avec diarisation.

    Objectif :
    1. Identifier ou déduire le titre de la réunion (court et spécifique).
    2. Résumer l'objet de la réunion en une phrase très concise.
    3. Donner un niveau de confiance (0.0 à 1.0) indiquant ton degré de certitude.
    4. Fournir une justification brève : quels éléments du texte t'ont permis cette extraction.

    Règles :
    - Utilise uniquement les informations explicites OU une inférence raisonnable fondée sur le sujet dominant.
    - Si aucun titre n'est donné, déduis le titre le plus plausible (ex : “Point budgétaire”, “Daily Stand Up”, “Réunion technique”).
    - L'objet doit être bref, factuel, et refléter la finalité principale évoquée.
    - Ignore les salutations, apartés, petites blagues, digressions.
    - Si aucune info exploitable n'est présente, renvoie les champs à null avec une faible confiance.

    Extrait :
    <chunk>
    {chunk_text}
    </chunk>

    Fin de l'extrait à traiter. 
    
    Fournis les informations extraites au format JSON strictement conforme au modèle Intent.
"""

REFINE_PROMPT_TEMPLATE = """
    Tu reçois :
    - un JSON courant représentant l'en-tête partiellement extrait,
    - un nouvel extrait de transcription.

    Ta mission :
    Mettre à jour le JSON UNIQUEMENT si le nouvel extrait apporte :
    - un titre plus clair, plus précis ou explicitement nommé,
    - OU un objet mieux défini, plus fiable ou plus pertinent.

    Si le nouvel extrait n'apporte rien de nouveau ni de plus précis, conserve les valeurs actuelles.

    Si tu mets à jour le titre ou l'objet :
    - ajuste le niveau de confiance en conséquence,
    - mets à jour la justification en citant les nouveaux indices.

    JSON courant :
    <current>
    {current_json}
    </current>

    Nouvel extrait :
    <chunk>
    {chunk_text}
    </chunk>

    Renvoie UNIQUEMENT le JSON mis à jour et valide au schéma conforme au modèle Intent.`
"""
