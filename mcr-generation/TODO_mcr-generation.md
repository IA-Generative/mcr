# mcr-generation — pistes pour la suite (doc de passation)

> Doc de passation (dernière MAJ : 2026-05-29). Fait suite à l'épic « Notes utilisateur » puis à l'ajout de la facette `participants`.
> Aucun item ouvert ci-dessous n'est bloquant pour la prod ; ils sont ordonnés par valeur perçue / coût. Les estimations sont indicatives.

---

## ✅ Déjà livré (voir [PR-758](https://github.com/IA-Generative/mcr/pull/758))

### Facette de notes `participants` (ex-TODO #1)

Les notes utilisateur servent désormais à mieux **nommer/qualifier les participants** détectés
dans la transcription.

- `ExtractedNotes` a un champ `participants: ParticipantsHint | None` (modèle léger `name` +
  `role` optionnel, **sans `speaker_id`**, dans `schemas/base.py`).
- `NotesExtractor.extract_participants_hint` + prompt dédié (`EXTRACT_PARTICIPANTS_HINT_PROMPT_TEMPLATE`),
  branché dans le `match` de `extract_all`.
- `NotesFacet.PARTICIPANTS` ajouté à `_FACETS_BY_REPORT_TYPE` (`DECISION_RECORD` **et**
  `DETAILED_SYNTHESIS`) et `ParticipantsCollector.notes_facets = {PARTICIPANTS}` (flow custom).

**Décision d'archi importante (diffère du plan initial)** : l'indice n'est **pas** un `init_hint`
(seed), contrairement à ce qui était prévu, parce que les participants issus des notes n'ont pas de
`speaker_id` à amorcer (ça créerait des participants fantômes). Il est injecté comme **bloc de
contexte en lecture seule** dans les prompts :
- hook générique `_extra_prompt_vars()` ajouté sur `BaseInitThenRefine` (vide par défaut) ;
- `RefineParticipants(participants_hint=...)` rend l'indice via `render_participants_hint`
  (`sections/participants/prompts.py`) et remplit le placeholder `{notes_hint}` des prompts
  *init* et *refine* ;
- distinct de `init_hint` (seed typé, type de sortie) utilisé par `RefineIntent` / `RefineNextMeeting`.

Branché sur **tous** les appels `RefineParticipants` : `generate_header` (CR standards) +
`ParticipantsCollector`, `TopicsCollector`, `DetailedDiscussionsCollector` (CR custom).

> Résout aussi l'ancien TODO « `extracted_notes` inutilisé sur `ParticipantsCollector` » : le
> collecteur consomme maintenant la facette. L'idée de `CollectorContext` qui en découlait est
> reprise dans le TODO #1 ci-dessous.

---

## 1. Refacto duplication d'appels inter-collecteurs

**Contexte** : `TitleCollector`, `TopicsCollector` et `DetailedDiscussionsCollector` instancient
chacun `RefineIntent` en interne, et `Topics` / `DetailedDiscussions` instancient aussi
`RefineParticipants`. Un plan custom `[title, topics, detailed_discussions]` lance donc **3 fois**
`RefineIntent().init_then_refine(chunks)` et **2 fois** `RefineParticipants(...).init_then_refine(chunks)`
— soit autant de chaînes init+refine sur toute la transcription. La livraison de la facette
`participants` a **aggravé** ce point : chaque `RefineParticipants` est en plus reconstruit avec le
même `participants_hint`.

**Action** :
- Introduire un « contexte partagé » au niveau `CustomReportGenerator`, calculé une fois avant
  `_render_section` :
  ```python
  shared = SharedContext(
      intent=await RefineIntent().init_then_refine_async(chunks, init_hint=notes.intent),
      participants=await RefineParticipants(notes.participants).init_then_refine_async(chunks),
  )
  ```
- Pour passer ce contexte aux collecteurs sans polluer la signature de chacun, utiliser une
  enveloppe `CollectorContext` (dataclass / Pydantic) plutôt qu'un n-ième paramètre :
  ```python
  class CollectorContext(BaseModel):
      extracted_notes: ExtractedNotes | None = None
      shared: SharedContext | None = None   # intent / participants déjà raffinés

  async def collect(self, chunks: list[Chunk], context: CollectorContext | None = None) -> str: ...
  ```
  Chaque collecteur ne lit que ce dont il a besoin (`context.extracted_notes`, `context.shared`).
- Refactoriser les 3 collecteurs concernés pour consommer `shared.intent` / `shared.participants`
  au lieu de recréer un `RefineIntent` / `RefineParticipants`.
- Gain : un plan `[title, topics, detailed_discussions]` passe de 3 → 1 `RefineIntent` et 2 → 1
  `RefineParticipants` (et le `participants_hint` n'est rendu qu'une fois).
- Effet de bord : il faut passer `init_then_refine` en async (cf. #3) ou encapsuler dans
  `asyncio.to_thread` pour rester compatible avec le caller async de `CustomReportGenerator`.

## 2. Notes-aware `Rewriter`

**Contexte** : aujourd'hui le `Rewriter` ne voit que `raw_prompt`. Si l'utilisateur écrit « fais-moi
un CR à partir de mes notes » sans préciser de structure, le rewriter ne sait pas que des notes
existent et risque de produire un plan peu pertinent.

**Action** :
- Étendre la signature de `Rewriter.rewrite(raw_prompt, notes_preview: str | None)`.
- Injecter un extrait court de `notes_content` (premiers N caractères) dans le prompt du rewriter
  pour qu'il puisse anticiper.
- À débattre : est-ce qu'on veut que le rewriter ajoute des collecteurs spontanément si les notes
  mentionnent une todo / une décision ? Ou est-ce qu'il doit rester strict sur l'intention
  utilisateur ?

## 3. Migration progressive vers `async/await`

**Contexte** : `NotesExtractor` et `GenericMapReducePipeline` sont async ; `BaseInitThenRefine`,
`BaseMapReduceGenerator` et les collecteurs sont sync (wrappés via `asyncio.to_thread` ou
`asyncio.run`). Cette asymétrie introduit de la complexité (deux helpers
`call_llm_with_structured_output` / `acall_llm_with_structured_output` à maintenir, threading
inutile dans le flow custom). C'est aussi un **prérequis** pour les TODO #1 (contexte partagé async)
et #4.

**Action** :
- Migrer `BaseInitThenRefine` en async.
- Migrer `BaseMapReduceGenerator` en async.
- Migrer les collecteurs en async natif (suppression d'`asyncio.to_thread`).
- Mutualiser sur `acall_llm_with_structured_output` ; supprimer la version sync si elle devient
  inutilisée.

## 4. Évaluation de l'héritage `GenericMapReducePipeline` ← `BaseMapReduce`

**Contexte** : les deux pipelines map-reduce (`BaseMapReduce` pour les sections structurées du flow
standard et des `CollectorSection` du flow custom ; `GenericMapReducePipeline` pour les
`CustomSection`) portent conceptuellement la même séquence « map en parallèle puis reduce LLM ».
Question légitime : faut-il les unifier dans une seule hiérarchie d'héritage ?

Analyse menée pendant la planification d'EPIC2 : **techniquement faisable mais avec ~12 différences
structurelles à neutraliser**. Les 3 principales :
- **Sync vs async** : `BaseMapReduce` utilise `ThreadPoolExecutor` + sync OpenAI client ;
  `GenericMapReducePipeline` est en `asyncio.gather` + `AsyncOpenAI`. Pas de partage de méthode
  possible sans migration préalable.
- **Configuration `ClassVar` vs param runtime** : `BaseMapReduce` est entièrement déclaratif
  (7 `ClassVar` figés par sous-classe) ; `GenericMapReducePipeline` reçoit l'`instruction` à chaque
  appel (différent par `CustomSection`).
- **Forme des items map** : `list[MappedT]` typé (Pydantic avec `topic`, `topic_confidence`,
  `chunk_id`) vs `list[str]` plat. Pas le même contrat.

Autres différences à neutraliser : output `BaseModel` vs `str`, gestion d'erreurs map (per-chunk vs
propagée), spans Langfuse dynamiques vs statiques, validation no-top-heading côté Generic uniquement,
absence de `topic_confidence` côté Generic, args constructeur différents.

**Action** :
- **Prérequis dur** : la migration async (#4) doit être livrée d'abord — sans elle, les deux
  pipelines restent sur des paradigmes incompatibles.
- Une fois async migré, ré-évaluer si l'inheritance devient suffisamment trivial pour mériter une
  US dédiée.
- Si oui : faire hériter `GenericMapReducePipeline(BaseMapReduce[str, str])` en relaxant les
  contraintes de typage générique (`ContentT: BaseModel` → accepter `str`, items pouvant être des
  strings non Pydantic, `topic_confidence` opt-in via `ClassVar bool`, `instruction` thread via
  kwarg).
- Si non (probable) : documenter pourquoi le partage ne s'impose pas et clore la question
  définitivement.

**après** #4 — uniquement si la valeur est confirmée à ce moment-là. La duplication actuelle est
faible (~10 lignes de structure haut-niveau) et le ratio coût/bénéfice est probablement défavorable.
