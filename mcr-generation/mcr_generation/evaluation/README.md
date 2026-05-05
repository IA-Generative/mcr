# Évaluation offline des comptes rendus

Pipeline locale qui exécute la génération de CR sur le dataset golden, score
chaque CR sur 6 critères qualité (LLM-judge G-Eval), et produit un CSV
comparable d'un run à l'autre.

## Vue d'ensemble

```
data/
├── transcripts/<uid>.docx          # transcripts d'entrée
└── expected/
    ├── reports/<uid>.docx          # CR de référence rédigé à la main (critères globaux)
    ├── topics/<uid>.docx           # section topics de référence
    ├── participants/<uid>.docx     # section participants de référence
    └── next_steps/<uid>.docx       # section next steps de référence
```

Pour chaque transcript, le runner :

1. Lance la chaîne de génération existante (`mcr_generation.app.services.report_generator`).
2. Sauvegarde le CR généré dans `outputs/generated_reports/<uid>.docx`.
3. Score chaque critère :
   - critères `scope=global` → comparaison du CR complet à `expected/reports/<uid>.docx`,
   - critères `scope=section:X` → extraction de la section X du CR généré, comparaison à `expected/<X>/<uid>.docx`,
   - critère intrinsèque (`non_redundancy`) → noté seul, sans référence.
4. Écrit `outputs/metrics/<run_id>.csv` (une ligne par item, ligne `MEAN` finale)
   et `outputs/metrics/<run_id>_summary.json`.

## Lancer un run

```bash
cd mcr-generation

# Run complet
make report-eval

# Smoke test sur 2 items
make report-eval-quick
```

Variables d'environnement :

- `EVALUATION_DATA_DIR` (défaut `./mcr_generation/evaluation/data`).
- `EVALUATION_OUTPUT_DIR` (défaut `$EVALUATION_DATA_DIR/outputs`).
- Le scorer G-Eval consomme les mêmes credentials LLM que le report generator
  (`LLM_HUB_API_URL`, `LLM_HUB_API_KEY`).
- `LANGFUSE_TRACING_ENABLED` est **forcé à `False`** par le CLI : les `@observe`
  des modules de prod deviennent des no-ops et l'export OTel est désactivé.
  Override en exportant explicitement `LANGFUSE_TRACING_ENABLED=True` (et en
  configurant `LANGFUSE_HOST` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`)
  si vous voulez tracer le run.

`run_id` = `<YYYYMMDD-HHMMSS>_<sha7>` (UTC + commit court). Il devient le nom
du CSV et du résumé JSON.

## Lecture du CSV

```
uid,information_precision,information_recall,non_redundancy,topic_relevance,participants_accuracy,next_steps_actionability
daily_0420,4,3,5,4,5,2
...
MEAN,3.33,2.67,4.00,3.00,3.33,2.67
```

- Une ligne par item (un transcript), une colonne par critère.
- Une cellule vide signale un critère non scoré (référence manquante, erreur
  LLM-judge non-fatale). La ligne `MEAN` ignore ces cellules.
- La ligne `MEAN` finale donne la moyenne par critère sur l'ensemble du dataset.

## Critères d'évaluation

Les définitions vivent dans `criteria.py`. Pour ajouter un critère, instancier
un nouvel objet `Criterion` et l'ajouter à la liste `CRITERIA`. Pour modifier
un critère (prompt, grille), éditer son entrée. Aucune autre modification
n'est requise — le runner itère sur `CRITERIA`.

| Critère | `scope` | Référence | Définition |
|---|---|---|---|
| `information_precision` | `global` | `expected/reports/<uid>.docx` | Le CR généré ne contredit pas la référence et n'introduit aucun ajout factuel non-attesté. Les reformulations qui préservent le sens sont acceptées. |
| `information_recall` | `global` | `expected/reports/<uid>.docx` | Toutes les informations significatives de la référence se retrouvent dans le CR généré (quitte à être reformulées). Pas d'oubli majeur de décision, action, arbitrage ou engagement. |
| `non_redundancy` | `global` | — (intrinsèque) | Chaque information utile apparaît une seule fois, au bon endroit. Les rappels légitimes (décision reprise comme action dans `next_steps`) ne comptent pas comme doublons. |
| `topic_relevance` | `section:topics` | `expected/topics/<uid>.docx` | Les topics du CR généré couvrent les mêmes sujets que la référence, à granularité comparable, avec des titres informatifs (pas de "Discussion"/"Tour de table"). |
| `participants_accuracy` | `section:participants` | `expected/participants/<uid>.docx` | Liste des participants alignée sur la référence (mêmes personnes, orthographe correcte, rôles cohérents). Tolère les variantes mineures (accents, synonymes de rôle). |
| `next_steps_actionability` | `section:next_steps` | `expected/next_steps/<uid>.docx` | Chaque next step est aussi actionable que celui de la référence : qui, quoi, quand quand la référence le précisait. |

Tous les critères sont scorés par G-Eval sur l'échelle 1-5. Le prompt de chaque
critère (incluant la grille détaillée) est inline dans `criteria.py` ; c'est
la source de vérité unique.

## Structure du module

```
evaluation/
├── README.md
├── criteria.py                  # définition des 6 Criterion (source de vérité)
├── cli/cli.py                   # entry point (uv run python -m ...)
├── pipeline/
│   ├── evaluation_pipeline.py   # orchestration générer → scorer → écrire
│   ├── report_renderer.py       # BaseReport → markdown
│   ├── section_splitter.py      # extraction de section par titre
│   ├── docx_loader.py           # .docx → texte (python-docx)
│   ├── csv_writer.py            # CSV + summary JSON
│   └── types.py                 # Criterion, ScoreResult, EvalItem, RunSummary
└── scorers/
    ├── base.py                  # Protocol Scorer
    └── g_eval.py                # implémentation LLM-judge
```
