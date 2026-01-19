MAP_PROMPT_TEMPLATE = """
Analyse cet extrait de transcription de réunion et identifie tous les sujets ainsi que les décisions associées qui y ont été prises. 

Pour chaque sujet extrait, tu dois fournir :
- Le titre du sujet (clair et concis)
- Les détails de ce sujet (MappedTopicDetails) : sous-sujet si pertinent, faits atomiques importants (max 5)
- Les décisions liées à ce sujet (liste de MappedDecision) : décision claire avec décideur et actions de suivi complètes
- Le niveau de confiance indiquant qu'il s'agit d'un sujet pertinent pour le rapport final

RÈGLES de remplissage:
- facts: lister tous les faits importants de manière concise et factuelle
- facts_justification: remplir SI le fait mentionne un interlocuteur ou nécessite contexte, sinon null
- facts_quotes: inclure SI la citation apporte une valeur (chiffres précis, formulation importante), sinon null
- decision_facts: lister les raisons/contexte de la décision qui ne sont pas déjà dans les facts du sujet
- followup_actions: toujours remplir owner et due_date si mentionnés dans la transcription
- justification dans followup_actions: remplir si la raison de l'action n'est pas évidente

Objet de la réunion : {meeting_subject}

Mapping entre les interlocuteurs et leurs noms/rôles si disponible : {speaker_mapping}

Extrait de la transcription :
{chunk_text}
Fin de l'extrait de la transcription.

Tu dois renvoyer le résultat final strictement au format JSON validant le schéma attendu : MappedTopics.
"""


REDUCE_PROMPT_TEMPLATE = """
Tu es un assistant chargé de générer un compte rendu de réunion consolidé en deux parties : les sujets discutés et les prochaines étapes.

Objectif principal de la réunion : {meeting_subject}
Liste des participants mappés : {speaker_mapping}

Voici la liste initiale des topics extraits (au format JSON) :  
<topics>
{topics}
</topics>

## Ta tâche de consolidation

1. **Regrouper et fusionner** les sujets similaires ou redondants:
   - Identifier les sujets ayant des faits ou décisions qui se recoupent
   - Fusionner leurs détails (facts, justifications, citations) en évitant les répétitions
   - Si un sujet contient plusieurs faits et decisons, voir s'il peut être divisé en sujets distincts.
2. **Filtrer** les sujets non pertinents par rapport à l'objectif de la réunion
3. **Synthétiser les détails par sujet** :
    - Utilise facts, facts_justification et facts_quotes pour créer 2-3 phrases factuelles riches
    - Chaque phrase = 1 fait concret avec chiffres/noms/contexte si disponibles
    - Intègre naturellement les justifications dans la formulation
    - Exemple: "15 postes Noemi et 10 docks Lenovo doivent être renouvelés, avec un budget disponible de 8000€"
    - SUPPRIME toute redondance avec le titre et l'introduction
4. **Créer une introduction concise** :
   - UNE phrase courte présentant le contexte général si utile
   - Mettre null si le titre est explicite OU si redondant avec details
5. **Sélectionner LA décision principale par sujet** :
   - Choisis la décision la plus IMPACTANTE parmi toutes celles du sujet
   - Format: "[Décideur] a décidé de [action]. [Action de suivi: responsable - échéance si disponibles]"
   - Intègre l'action de suivi principale directement dans la décision
   - Exemple: "Nicolas a décidé de commander 10 docks cette semaine. Alex s'en charge."
   - Mettre null si aucune décision n'a été prise
6. **Extraire les prochaines étapes (next_steps)** :
   - Actions concrètes qui ne sont PAS déjà mentionnées dans les main_decision
   - Format: "[Action] - [Responsable] - [Échéance]"
   - Exemple: "Tester l'externalisation des sauvegardes - Alex - avant le 30 novembre"
   - Liste vide si toutes les actions sont déjà dans les décisions

## Règles STRICTES d'élimination des redondances

AVANT de remplir chaque champ, vérifie:
- **introduction_text** : apporte-t-elle vraiment une info nouvelle par rapport au titre? Si non → null
- **details** : chaque phrase apporte-t-elle un fait concret non mentionné ailleurs? Si non → supprime-la
- **main_decision** : reformule-t-elle simplement un détail déjà listé? Si oui → reformule ou supprime
- **followup actions dans main_decision** : l'action est-elle déjà incluse dans main_decision text ? Si oui → supprimer la followup action
- **next_steps** : l'action est-elle déjà dans une main_decision? Si oui → ne pas l'inclure

RÈGLE D'OR: Chaque information ne doit apparaître qu'UNE SEULE FOIS dans le résultat final.

Si un sujet n'a pas de détails pertinents après élimination des redondances → liste vide pour details
Si un sujet n'a pas de décision → null pour main_decision
Si pas de prochaines étapes supplémentaires → liste vide pour next_steps

## Format de sortie attendu

Structure Content avec :
- **topics** : liste de sujets consolidés (champ Topic avec title, introduction_text, details, main_decision)
- **next_steps** : liste de prochaines étapes concrètes non redondantes (liste vide si aucune)

Tu dois renvoyer le résultat final strictement au format JSON validant le schéma attendu : Content.
"""
