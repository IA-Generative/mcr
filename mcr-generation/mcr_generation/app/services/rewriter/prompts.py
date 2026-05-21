REWRITER_PROMPT_TEMPLATE = """\
Tu reçois une consigne utilisateur courte et imprécise pour la génération d'un
compte rendu de réunion. Tu dois la transformer en plan structuré.

Chaque section du plan doit avoir l'une des deux formes ci-dessous :

1. **Soit** déléguer à un collecteur prédéfini parmi ceux listés ci-dessous :
{collectors_doc}

   Si une section utilisateur correspond clairement à un collecteur prédéfini,
   **utilise-le** en produisant une section de la forme :
   `{{"kind": "collector", "heading": "...", "collector_id": "<id exact>"}}`.

2. **Soit** fournir une consigne libre, qui sera passée à un pipeline générique
   pour produire le contenu de la section :
   `{{"kind": "custom", "heading": "...", "instruction": "<consigne libre>"}}`.

Le champ `kind` est obligatoire pour chaque section et détermine la forme
attendue (les champs autorisés diffèrent entre les deux variantes).

Règles strictes :
- Au moins 1 section, au plus 6.
- Reste fidèle à l'intention utilisateur ; n'ajoute pas de sections « bonus ».
- N'utilise QUE les `collector_id` listés ci-dessus. Si tu hésites, préfère le
  pipeline générique.
- Si l'utilisateur ne précise pas de titre, mets `title` à `null`.

Consigne brute fournie par l'utilisateur :
\"\"\"
{raw_prompt}
\"\"\"
"""
