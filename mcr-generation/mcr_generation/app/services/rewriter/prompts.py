REWRITER_PROMPT_TEMPLATE = """\
Tu reçois une consigne utilisateur courte et imprécise pour la génération d'un
compte rendu de réunion. Tu dois la transformer en plan structuré.

Pour chaque section du compte rendu, tu peux :

1. **Soit** utiliser un collecteur prédéfini parmi ceux listés ci-dessous :
{collectors_doc}

   Si une section utilisateur correspond clairement à un collecteur prédéfini,
   **utilise-le**, en mettant son identifiant exact dans `collector_id` et en
   laissant `instruction` à `null`.

2. **Soit** fournir une consigne libre dans `instruction`, qui sera passée à un
   pipeline générique pour produire le contenu de la section. Dans ce cas,
   `collector_id` doit être `null`.

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
