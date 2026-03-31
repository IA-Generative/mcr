## But

Fermer le bug (`Deliverable.AVAILABLE` commité avant l'upload S3) **en
introduisant les nouveaux dossiers `use_cases/`, `domain/`,
`infrastructure/`** sur exactement la tranche concernée. La tranche sert de
tête de pont pour la migration ;

## Validation

- **Test de non-régression** : injecter une exception dans
  `render_report` ou `upload_report_to_s3` ; asserter :
  - `deliverable.status == PENDING` (pas de bascule AVAILABLE),
  - aucun objet S3 écrit pour ce livrable,
  - l'endpoint renvoie 5xx,
  - le retry du worker mcr-generation converge après correction.

Test d'acceptation manuel sur staging après:

1. Démarrer une réunion, transcrire, demander un rapport personnalisé avec
   un prompt qui produit un tableau Markdown (le scénario du dant-01).
2. Injecter (via feature flag de dev ou monkeypatch local) une exception
   dans `render_report`.
3. Observer côté DB :
   - `deliverable.status = PENDING` (pas `AVAILABLE`),
   - `meeting.status = REPORT_PENDING` (inchangé, ou rétabli par projection),
   - aucune entrée dans le bucket S3 pour ce livrable.
4. Retirer l'injection ; relancer la requête `POST /deliverables/{id}/success`
   manuellement. Tout doit converger en un seul essai.

## Stratégie

### Migration vers les use cases

- Créer `mcr-core/mcr_meeting/app/domain/` (premier dossier `domain/`).
- Extraire `domain/report_rendering.py::render_report(report_response) -> BytesIO`
  depuis la logique de rendu de `services/report_task_service.py::persist_report_docx`.
  - Pure : prend la `ReportResponse`, renvoie un BytesIO. Aucune écriture DB / S3.
- Créer `mcr-core/mcr_meeting/app/infrastructure/`.
- Créer `infrastructure/s3.py` qui :
  - expose une fonction publique
    `upload_report_to_s3(meeting_id, deliverable_type, content) -> str`
    renvoyant l'`object_name`,
  - contient en privé `_object_name_for_deliverable(meeting_id, deliverable_type)`
    (la convention de format reste dans l'infra),
  - peut ré-exposer les helpers existants (`get_file_from_s3`,
    `get_report_object_name`, `put_file_to_s3`) en alias temporaires
    pour ne casser aucun appelant.
- `persist_report_docx` existe toujours, appelle désormais `render_report`
  - l'API S3 existante. Les anciens callers ne bougent pas.
- Tests : test unitaire pur sur `render_report` ; le test existant
  `test_custom_report_generation.py` continue de passer.
- **Idempotency** : la clé S3 est dérivée de `(meeting_id, deliverable_type)` ;
  un second appel écrase. Pour un même livrable, c'est idempotent par
  construction.
- **Blast radius** : minimal. Reverter le PR n'a aucun impact, aucun appelant
  ne dépend des nouveaux modules.

### Fix du bug

- Créer `domain/deliverable_transitions.py` :
  - `_ALLOWED: dict[DeliverableStatus, frozenset[DeliverableStatus]]`
  - `mark_available(deliverable, external_url) -> Deliverable`
  - `mark_failed(deliverable) -> Deliverable`
  - `soft_delete(deliverable) -> Deliverable`
  - `_assert_transition(current, target)` qui lève
    `DeliverableStateConflictException`.
- Créer `use_cases/mark_deliverable_success.py` :
  ```
  render → upload_report_to_s3 → UoW {
      deliverable_repo.get
      mark_available(deliverable, external_url=None)   # external_url reste None
      deliverable_repo.save
      meeting_repo.update_status(meeting_id, REPORT_DONE)   # temporaire — remplacé par projection en PR-T3
  } → notify_report_ready (best-effort post-commit, try/except/log)
  ```
- Router POST `/deliverables/{id}/success` : swap, appelle désormais
  `use_cases.mark_deliverable_success.mark_deliverable_success`.
- **Suppression** :
  - `orchestrators/deliverable_orchestrator.py::mark_deliverable_success`
    (plus aucun appelant après le swap router).
  - `services/deliverable_service.py::mark_deliverable_available`
    (le use case appelle directement le repo + la transition domain).
- **Pas de suppression** (dépend de la route legacy) :
  - `after_complete_report_handler` reste vivant (la route legacy
    `/meetings/{id}/report/success` l'utilise encore). Il continue
    de faire son rendu + upload sur ce chemin — Bug y demeure mais
    cette route est marquée pour suppression dans un ticket séparé.
  - `complete_report` orchestrator et l'event SM `COMPLETE_REPORT`
    restent pour la même raison.
  - `persist_report_docx`, `save_formatted_report` restent
    (toujours appelés par le hook legacy).
- **Migration data** : ce PR ne nettoie pas les livrables AVAILABLE
  orphelins préexistants (meetings 1183 et 1184). Recovery script
  séparé requis (cf. dant-01 §contre-mesures n°6).
- **Blast radius** : moyen. Le chemin `/deliverables/{id}/success`
  change de pipeline ; tests d'intégration sur ce endpoint impératifs.
