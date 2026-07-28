SYNTHESIZE_PROMPT = """
Tu es un analyste chargé de compléter un compte-rendu structuré de réunion.

Objet de la réunion : {meeting_subject}
Mapping entre les interlocuteurs et leurs noms/rôles si disponible : {speaker_mapping}

Voici les thématiques consolidées et leurs décisions (au format JSON) :
<themes>
{themes_json}
</themes>

## Ta tâche

À partir de ces thématiques et décisions, produis deux éléments :

### 1. Points en suspens (open_points)
- Questions ouvertes laissées sans réponse durant la réunion.
- Sujets attendus dans ce type de réunion mais qui n'ont pas été abordés.
- Contradictions ou désaccords non résolus.
- Sois pertinent : n'invente pas de sujets ; appuie-toi sur ce qui ressort des thématiques.
- Liste vide si rien de pertinent.

### 2. Recommandations (recommendations)
- 2 à 5 recommandations maximum, concrètes et actionnables.
- Basées strictement sur le contenu de la réunion, pas sur des connaissances générales.
- Préfère des actions concrètes ("planifier un suivi avec X la semaine prochaine") aux conseils vagues.
- Liste vide si rien de pertinent.

## Règles STRICTES

- Tout en français.
- Ne pas inventer d'éléments absents des thématiques fournies.
- Chaque entrée doit être autonome et compréhensible sans contexte supplémentaire.

Tu dois renvoyer le résultat final strictement au format JSON validant le schéma attendu : MinutesSynthesisContent.
"""
