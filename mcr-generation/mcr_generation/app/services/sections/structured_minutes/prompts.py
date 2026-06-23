MAP_PROMPT_TEMPLATE = """
Tu es un analyste qui produit un compte-rendu structuré d'une réunion à partir d'un extrait de sa transcription.

Analyse cet extrait et identifie les thématiques discutées ainsi que les décisions/actions explicitement décidées.

Pour chaque thématique extraite, fournis :
- topic : un titre court de la thématique
- topic_confidence : la confiance (0 à 1) que c'est bien une thématique pertinente
- summary : un résumé en 1 à 3 phrases (null si rien de pertinent)
- decisions : la liste des décisions/actions explicitement décidées sur cette thématique

Pour chaque décision, renseigne :
- decision : la décision ou l'action décidée, formulée clairement
- owner : la personne ou l'équipe qui doit la porter (null si non évoqué)
- due : l'échéance (date ou formulation relative ; null si non évoquée)

RÈGLES strictes :
- Ne liste que les décisions/actions EXPLICITEMENT énoncées, pas tes interprétations.
- Renseigne owner et due UNIQUEMENT s'ils sont évoqués dans la transcription, sinon null.
- N'invente rien : pas de thématique, décision, responsable ou échéance absent de l'extrait.
- 3 à 8 thématiques au maximum, sans redondance ni double-comptage.
- Tout en français.

Objet de la réunion : {meeting_subject}

Mapping entre les interlocuteurs et leurs noms/rôles si disponible : {speaker_mapping}

Extrait de la transcription :
{chunk_text}
Fin de l'extrait de la transcription.

Tu dois renvoyer le résultat final strictement au format JSON validant le schéma attendu : MappedMinutes.
"""


REDUCE_PROMPT_TEMPLATE = """
Tu es un analyste chargé de consolider un compte-rendu structuré de réunion à partir des thématiques extraites de chaque extrait.

Objet de la réunion : {meeting_subject}
Liste des participants mappés : {speaker_mapping}

Voici la liste initiale des thématiques extraites (au format JSON) :
<themes>
{themes}
</themes>

{notes_section}\
## Ta tâche de consolidation

1. **Regrouper et fusionner** les thématiques similaires ou redondantes en évitant les répétitions.
2. **Synthétiser** pour chaque thématique consolidée :
   - title : un titre court et explicite
   - summary : 1 à 3 phrases factuelles résumant la thématique (null si rien de pertinent)
   - decisions : la liste dédupliquée des décisions/actions explicitement décidées
3. **Décisions** : pour chacune, conserver
   - item : la décision/action formulée clairement
   - owner : le responsable (null si non évoqué)
   - due : l'échéance (null si non évoquée)

## Règles STRICTES

- Ne conserver que les décisions EXPLICITEMENT décidées ; ne pas inventer responsable ni échéance.
- Déduplication : une même décision ne doit apparaître qu'une seule fois.
- État final : si une décision a été modifiée ou annulée plus tard, ne garder que l'état final.
- Fidélité : ne pas inventer de thématiques ou décisions absentes des extraits fournis.
- 3 à 8 thématiques au maximum.
- Tout en français.

Tu dois renvoyer le résultat final strictement au format JSON validant le schéma attendu : MinutesContent.
"""
