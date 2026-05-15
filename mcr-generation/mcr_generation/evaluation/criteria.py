"""Definition of the 6 quality criteria used to evaluate generated reports.

Each `Criterion` carries the LLM-judge prompt inline. To add a criterion, append
a new entry to `CRITERIA`. To modify a criterion, edit the existing entry.

The runner iterates over `CRITERIA` and routes each item through a `GEvalScorer`.
"""

from mcr_generation.evaluation.pipeline.types import Criterion

INFORMATION_PRECISION = Criterion(
    name="information_precision",
    scope="global",
    scale=(1, 5),
    description=(
        "Le CR généré ne contredit pas la référence et n'introduit aucun ajout "
        "factuel non-attesté (nom, chiffre, décision, engagement inventé). "
        "Les reformulations qui préservent le sens sont acceptées."
    ),
    prompt_template="""Tu es un évaluateur qualité. On te fournit un compte rendu généré et un compte rendu de référence rédigé à la main (considéré parfait). Ta tâche : noter la **précision d'information** du CR généré sur une échelle de 1 à 5 selon la grille ci-dessous.

Définition : toute information du CR généré doit être cohérente avec le CR de référence. Pénalise les ajouts factuels qui contredisent la référence ou qui introduisent des détails non-attestés (noms, chiffres, décisions, engagements). Les reformulations qui préservent le sens ne sont PAS des violations.

Raisonne étape par étape :
1. Parcours le CR généré et liste les affirmations factuelles (décisions, chiffres, noms, actions, engagements).
2. Pour chaque affirmation, vérifie si elle est cohérente avec la référence.
3. Classe les écarts : contradiction directe, ajout non-attesté, reformulation légitime.
4. Attribue un score selon la grille.

Retourne un JSON {"score": int, "justification": str} avec une justification de 1-2 phrases citant au besoin l'extrait fautif.

[Grille détaillée]
5 — Aucun ajout non-attesté, aucune contradiction. Chaque affirmation du CR généré est cohérente avec la référence.
4 — Une seule imprécision mineure (reformulation légèrement extrapolée) sans impact sur le sens.
3 — Un ajout non-attesté mineur (détail non présent dans la référence mais plausible) OU une contradiction sur un point secondaire.
2 — Plusieurs ajouts non-attestés, OU une contradiction majeure (décision inventée, chiffre faux, participant halluciné).
1 — CR largement divergent de la référence : multiples inventions ou contradictions structurantes.

Compte rendu généré : {{report}}
Compte rendu de référence : {{reference_report}}
""",
)

INFORMATION_RECALL = Criterion(
    name="information_recall",
    scope="global",
    scale=(1, 5),
    description=(
        "Toutes les informations significatives du CR de référence se retrouvent "
        "dans le CR généré (quitte à être reformulées). Pas d'oubli majeur de "
        "décision, d'action, d'arbitrage ou d'engagement."
    ),
    prompt_template="""Tu es un évaluateur qualité. On te fournit un compte rendu généré et un compte rendu de référence rédigé à la main (considéré parfait). Ta tâche : noter le **rappel d'information** du CR généré sur une échelle de 1 à 5 selon la grille ci-dessous.

Définition : toute information *significative* présente dans la référence doit apparaître dans le CR généré. Un détail peut être formulé différemment — ce qui compte, c'est la présence de l'information (décision, action, chiffre, participant, arbitrage). Une information mineure absente n'est pas un problème ; un engagement ou une décision absent(e) en est un.

Raisonne étape par étape :
1. Liste les informations significatives du CR de référence (décisions, actions, arbitrages, chiffres clés, blocages, engagements).
2. Pour chaque item, vérifie sa présence dans le CR généré.
3. Identifie les omissions et juge leur gravité.
4. Attribue un score selon la grille.

Retourne un JSON {"score": int, "justification": str} avec une justification de 1-2 phrases listant les éventuelles omissions.

[Grille détaillée]
5 — Toutes les informations significatives de la référence sont présentes dans le CR généré. Aucun oubli.
4 — Une information secondaire omise ou traitée trop superficiellement, sans impact sur la compréhension globale.
3 — Une information significative absente ou traitée très superficiellement (perd un engagement ou une décision secondaire de la référence).
2 — Plusieurs informations significatives omises, OU une information majeure (décision structurante, action critique) absente.
1 — CR largement partiel : couvre seulement une fraction du contenu de la référence.

Compte rendu généré : {{report}}
Compte rendu de référence : {{reference_report}}
""",
)

NON_REDUNDANCY = Criterion(
    name="non_redundancy",
    scope="global",
    scale=(1, 5),
    description=(
        "Chaque information utile apparaît une seule fois, au bon endroit dans "
        "le CR généré. Les rappels légitimes (une décision reprise comme action "
        "dans next_steps) ne comptent pas comme doublons. Critère intrinsèque : "
        "aucune référence nécessaire."
    ),
    prompt_template="""Tu es un évaluateur qualité. On te fournit un compte rendu généré. Ta tâche : noter la **non-redondance** du CR sur une échelle de 1 à 5. Une information ne doit pas être répétée à plusieurs endroits sans valeur ajoutée. Exception légitime : une décision prise dans un topic peut être rappelée en next_step sous forme d'action — c'est un angle différent, pas une redondance.

Retourne un JSON {"score": int, "justification": str} avec une justification de 1-2 phrases citant les doublons problématiques si applicable.

[Grille détaillée]
5 — Chaque information apparaît une seule fois, au bon endroit. Pas de doublon.
4 — Un rappel volontaire (ex : décision mentionnée dans un topic puis reprise en next_step sous forme d'action) — acceptable et attendu.
3 — Un doublon notable : la même information formulée à l'identique dans deux sections distinctes.
2 — Plusieurs doublons, OU une section entière redondante avec une autre (ex : topics qui dupliquent les detailed_discussions).
1 — Redondance massive : la moitié du CR répète l'autre moitié.

Compte rendu généré : {{report}}
""",
)

TOPIC_RELEVANCE = Criterion(
    name="topic_relevance",
    scope="section:topics",
    scale=(1, 5),
    description=(
        "Les topics du CR généré couvrent les mêmes sujets que ceux de la "
        "référence, avec un niveau de granularité comparable et des titres "
        "informatifs (pas de 'Discussion' ou 'Tour de table' génériques)."
    ),
    prompt_template="""Tu es un évaluateur qualité. On te fournit la section **topics** d'un compte rendu généré et celle d'un compte rendu de référence rédigé à la main. Ta tâche : noter la **pertinence des topics** sur une échelle de 1 à 5. Évalue : (a) les topics du CR généré couvrent-ils les mêmes sujets que ceux de la référence (quitte à être formulés différemment) ? (b) la granularité est-elle comparable (ni trop large, ni sur-découpée par rapport à la référence) ? (c) les titres sont-ils informatifs ou génériques ?

Retourne un JSON {"score": int, "justification": str} avec une justification de 1-2 phrases.

[Grille détaillée]
5 — Chaque topic du CR généré correspond à un topic de la référence (1-pour-1 ou découpage équivalent), avec un titre informatif.
4 — Un topic au titre un peu générique mais défensable (ex : "Point d'avancement"), OU un léger décalage de granularité sans perte d'information.
3 — Un topic mal découpé par rapport à la référence (deux sujets fusionnés OU un sujet sur-découpé en plusieurs topics).
2 — Un topic inventé (absent de la référence) OU plusieurs titres génériques sans valeur ("Discussion", "Tour de table").
1 — Topics largement déconnectés de la référence : hallucinations ou découpe absurde (ex : un topic par participant).

Compte rendu généré (section topics) : {{report}}
Compte rendu de référence (section topics) : {{reference_report}}
""",
)

PARTICIPANTS_ACCURACY = Criterion(
    name="participants_accuracy",
    scope="section:participants",
    scale=(1, 5),
    description=(
        "La liste des participants du CR généré couvre les mêmes personnes que "
        "la référence, avec des noms correctement orthographiés et des rôles "
        "cohérents."
    ),
    prompt_template="""Tu es un évaluateur qualité. On te fournit la section **participants** d'un compte rendu généré et celle d'un compte rendu de référence rédigé à la main. Ta tâche : noter l'**exactitude des participants** sur une échelle de 1 à 5. Évalue deux axes : (a) couverture (la liste du CR généré contient-elle les mêmes personnes que la référence, avec une orthographe correcte ?) et (b) rôles (les rôles attribués sont-ils cohérents avec ceux de la référence ?). Tolère les variations mineures d'orthographe (accents, espaces) et les synonymes de rôle.

Retourne un JSON {"score": int, "justification": str} avec une justification de 1-2 phrases.

[Grille détaillée]
5 — Même ensemble de participants que la référence, noms bien orthographiés, rôles cohérents.
4 — Même ensemble, mais un rôle imprécis ou générique ("participant") alors que la référence était plus précise.
3 — Un participant manquant OU un nom notablement mal orthographié OU un rôle clairement divergent de la référence.
2 — Plusieurs participants manquants OU plusieurs rôles faux OU un participant halluciné (absent de la référence).
1 — Liste largement erronée : multiples hallucinations ou oublis, ensemble de participants incompatible avec la référence.

Compte rendu généré (section participants) : {{report}}
Compte rendu de référence (section participants) : {{reference_report}}
""",
)

NEXT_STEPS_ACTIONABILITY = Criterion(
    name="next_steps_actionability",
    scope="section:next_steps",
    scale=(1, 5),
    description=(
        "Chaque next step du CR généré est aussi actionable que celui de la "
        "référence : responsable identifié, action concrète, échéance présente "
        "quand la référence en mentionnait une."
    ),
    prompt_template="""Tu es un évaluateur qualité. On te fournit la section **next_steps** d'un compte rendu généré et celle d'un compte rendu de référence rédigé à la main. Ta tâche : noter l'**actionabilité** des next steps du CR généré sur une échelle de 1 à 5. Un next step actionable = on peut identifier QUI fait QUOI, et idéalement QUAND. Utilise la référence pour te calibrer : si la référence précise un responsable ou une échéance, le CR généré devrait aussi ; si la référence reste vague (car l'info n'était pas disponible), ne pénalise pas le CR généré d'être vague à son tour.

Retourne un JSON {"score": int, "justification": str} avec une justification de 1-2 phrases.

[Grille détaillée]
5 — Chaque next step a un responsable et une action claire, avec échéance quand la référence en mentionne une.
4 — La plupart des next steps sont actionables ; un ou deux manquent d'un responsable ou d'une échéance que la référence ne précisait pas non plus.
3 — Plusieurs next steps vagues alors que la référence était plus précise (perte d'un responsable ou d'une échéance précisé(e) par la référence).
2 — Majorité des next steps non-actionables, OU liste générique très éloignée de celle de la référence.
1 — Pas de next steps actionables : soit la section est vide alors que la référence en contient, soit elle ne contient que des formulations creuses.

Compte rendu généré (section next_steps) : {{report}}
Compte rendu de référence (section next_steps) : {{reference_report}}
""",
)

CRITERIA: list[Criterion] = [
    INFORMATION_PRECISION,
    INFORMATION_RECALL,
    NON_REDUNDANCY,
    TOPIC_RELEVANCE,
    PARTICIPANTS_ACCURACY,
    NEXT_STEPS_ACTIONABILITY,
]
