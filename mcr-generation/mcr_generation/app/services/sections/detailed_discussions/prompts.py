MAP_PROMPT_TEMPLATE = """
Analyse cet extrait de transcription de réunion et identifie toutes les discussions détaillées qui s'y tiennent, avec les informations clés et les décisions associées.

Pour chaque discussion extraite, tu dois fournir :
- Le sujet de la discussion : courts, factuels, sans intention ni interprétation (ex. "Préparation de la démo de fin d'année", "Optimisation du plan de recrutement")
- Le niveau de confiance sur l'identification du sujet
- Les informations clés (takeaways) : faits importants, détails pertinents, citations si utiles
- Les décisions prises : décision claire avec décideur, faits contextuels, actions de suivi et points de vigilance

RÈGLES sur les sujets :
- Respecter l'ordre chronologique d'apparition des sujets dans l'extrait
- Si un sujet déjà traité dans cet extrait revient plus tard, créer une nouvelle entrée avec le suffixe "(reprise)" (ex. "Préparation du séminaire", puis "Préparation du séminaire (reprise)")

RÈGLES de remplissage:
- takeaway: formuler chaque information importante de manière concise et factuelle
- takeaway_details: remplir SI des précisions supplémentaires apportent de la valeur, sinon null
- takeaway_quote: inclure SI la citation apporte une valeur ajoutée (chiffres précis, formulation importante), sinon null
- decision_facts: lister les raisons/contexte de la décision qui ne sont pas déjà évidents dans le sujet ou la décision elle-même
- followup_actions: toujours remplir owner et due_date si mentionnés dans la transcription
- monitoring_points: inclure les points de vigilance à surveiller suite à la décision ou à la discussion ; quatre natures possibles : (1) risques à anticiper, (2) questions ouvertes non résolues, (3) validations à obtenir, (4) points de suivi de mise en œuvre d'une décision — liste vide si aucun
- justification dans followup_actions et monitoring_points: remplir si la raison n'est pas évidente, sinon null
- relevance_score et confidence_score: entre 0 et 1, refléter objectivement la pertinence et le niveau de certitude

Objet de la réunion : {meeting_subject}

Mapping entre les interlocuteurs et leurs noms/rôles si disponible : {speaker_mapping}

Extrait de la transcription :
{chunk_text}
Fin de l'extrait de la transcription.

Tu dois renvoyer le résultat final strictement au format JSON validant le schéma attendu : MappedDetailedDiscussions.
"""


REDUCE_PROMPT_TEMPLATE = """
Tu es un assistant chargé de générer la section "discussions détaillées" d'un compte-rendu de réunion consolidé.

Objectif principal de la réunion : {meeting_subject}
Liste des participants mappés : {speaker_mapping}

Voici la liste initiale des discussions détaillées extraites (au format JSON) :
<detailed_discussions>
{detailed_discussions}
</detailed_discussions>

## Ta tâche de consolidation

1. **Regrouper et fusionner** les discussions similaires ou redondantes :
   - Identifier les discussions portant sur le même sujet ou des sujets très proches
   - Fusionner leurs takeaways et décisions en évitant les répétitions
   - Si une discussion contient des sujets vraiment distincts, la scinder en plusieurs discussions séparées
   - **Conserver l'ordre chronologique** : la liste finale doit suivre l'ordre d'apparition des sujets dans la réunion
   - **Règle "(reprise)"** : si un même sujet apparaît à nouveau plus tard dans la réunion, conserver les deux entrées distinctes en suffixant la seconde (et les suivantes) avec "(reprise)" — ex. "Préparation du séminaire", puis "Préparation du séminaire (reprise)"
2. **Titres de sujets** : courts, factuels, sans intention ni interprétation (ex. "Préparation de la démo de fin d'année", "Optimisation du plan de recrutement")
3. **Filtrer** les discussions non pertinentes par rapport à l'objectif de la réunion
4. **Synthétiser les key_ideas par discussion** :
   - Formuler entre **3 et 10 bullets** factuels et concrets à partir des takeaways (texte, détails, citations) — adapter le nombre à la densité du sujet
   - Chaque bullet = 1 idée clé avec chiffres/noms/contexte si disponibles
   - Intégrer naturellement les justifications dans la formulation
   - Exemple : "Le budget alloué au projet est de 50 000€, dont 30% sont déjà engagés"
   - Supprimer toute redondance avec le titre
5. **Consolider les décisions** :
   - Formuler chaque décision de manière claire : "[Décideur] a décidé de [action]."
   - Inclure le décideur s'il est connu
   - Une décision par entrée dans la liste
   - Exemple : "Nicolas a décidé de reporter le lancement au T2."
6. **Extraire les actions (actions)** :
   - Actions concrètes à réaliser suite aux décisions
   - Format : "[Action] - [Responsable] - [Échéance]"
   - Exemple : "Envoyer le compte-rendu à l'équipe - Marie - avant vendredi"
   - Liste vide si aucune action n'est mentionnée
7. **Identifier les points de vigilance (focus_points)** :
   - Trois natures possibles, à distinguer clairement :
     - **Risques** : éléments susceptibles de compromettre une décision ou un objectif (ex. "Risque de dépassement de budget si les délais glissent")
     - **Questions ouvertes** : points non tranchés qui nécessitent une réponse (ex. "Question ouverte : quelle équipe prend en charge la migration ?")
     - **Validations à obtenir** : approbations ou confirmations requises avant d'avancer (ex. "Validation à obtenir : accord de la direction juridique avant signature")
     - **Suivi de mise en œuvre** : vérifications que les décisions prises sont bien appliquées dans les faits (ex. "Vérifier que le nouveau process de validation est bien appliqué par l'équipe d'ici fin mars")
   - Formuler de manière concise et actionnable
   - Liste vide si aucun point de vigilance n'est pertinent

## Règles STRICTES d'élimination des redondances

AVANT de remplir chaque champ, vérifie :
- **key_ideas** : chaque idée apporte-t-elle un fait concret non mentionné ailleurs ? Si non → supprime-la
- **decisions** : reformule-t-elle simplement un détail déjà listé dans key_ideas ? Si oui → reformule ou supprime
- **actions** : l'action est-elle déjà incluse dans une décision ? Si oui → ne pas la dupliquer
- **focus_points** : le point est-il déjà couvert par une décision ou une action ? Si oui → supprimer

RÈGLE D'OR : Chaque information ne doit apparaître qu'UNE SEULE FOIS dans le résultat final.

Si une discussion n'a pas de décisions → liste vide pour decisions
Si une discussion n'a pas d'actions → liste vide pour actions
Si une discussion n'a pas de points de vigilance → liste vide pour focus_points

## Format de sortie attendu

Structure Content avec :
- **detailed_discussions** : liste de discussions consolidées, chacune avec title, key_ideas, decisions, actions, focus_points

Tu dois renvoyer le résultat final strictement au format JSON validant le schéma attendu : Content.
"""
