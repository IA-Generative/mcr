# `logger.py` s'est mis à dépendre de Sentry — deux fichiers infra qui s'importent l'un l'autre

| ID | Date d'analyse | Issue (+PR) | Detection Stage | Statut | Owner | Données |
|----|----------------|-------------|-----------------|--------|-------|---------|
| dant-001 | 2026-07-22 | Sentry #2352 (PR framework erreurs) | B — Code Review | Corrigé | Thomas | `mcr-core/mcr_meeting/app/infrastructure/` |

## Description du défaut

- Pendant l'implémentation du correctif du bruit Sentry (#2352), un helper `sentry_logging_integrations()` — qui **construit des objets `sentry_sdk`** (`LoguruIntegration`, `LoggingIntegration`) — a été placé dans `infrastructure/logger.py`.
- Conséquence : `logger.py` importait désormais `sentry_sdk`, et `sentry.py` + `main.py` réimportaient ce helper **depuis `logger.py`**.
- Détecté en **revue** par l'utilisateur : « pourquoi `logger` importe Sentry, ce sont deux fichiers infra qui ne devraient pas s'importer ».
- Aucun impact runtime (défaut structurel) : les tests, mypy et ruff étaient verts. Le coût est architectural — érosion de la règle « une dépendance externe par fichier infra ».

- Chaînes : une seule (A) — placement du helper au mauvais fichier.

> **Constat** : la formulation spontanée « deux fichiers infra ne doivent pas s'importer » est **fausse dans ce dépôt** — `celery_consumer→logger`, `s3→retry`, `diarization→unleash` sont des imports infra→infra légitimes. La vraie règle est plus fine (cf. chaîne A).

## Chaîne A — Le helper d'intégration Sentry rangé dans le fichier du logging

- **Mécanisme** (échelle des pourquoi jusqu'à la racine) :
  - Le helper instancie `LoguruIntegration(...)` / `LoggingIntegration(...)`, classes **du paquet `sentry_sdk`** → il encapsule la dépendance *Sentry*, pas *loguru*.
  - Pourtant il a été rangé dans `logger.py`. Pourquoi ?
    - Parce que le placement a été décidé sur le **nom du domaine** (« ça configure le *logging* → fichier `logger` ») et non sur la **dépendance externe réellement importée** (`sentry_sdk`).
      - Pourquoi ce raccourci ? Deux leurres cumulés :
        - **Leurre lexical** : le nom du helper (« logging integration ») partage un mot avec le fichier (`logger`).
        - **Leurre du « fichier neutre partagé »** : les deux init Sentry (API `main.py` + worker `sentry.py`) avaient besoin du helper ; j'ai cherché un fichier que *les deux importaient déjà* (`logger`) au lieu de voir que le **propriétaire naturel de `sentry_sdk` existait déjà** (`sentry.py`) et pouvait être importé par les deux.
    - **Racine** : confusion sur ce qui définit un fichier infra. Un fichier infra est nommé et délimité par le **service/SDK externe qu'il possède** (`keycloak.py`, `redis.py`, `s3.py`, `sentry.py`), pas par le nom fonctionnel de la donnée qu'il manipule. `sentry_sdk` a **un seul propriétaire** : `sentry.py`.

- **Lignes fautives** (chemin d'import, pas de runtime) :

```python
# infrastructure/logger.py  — AVANT
from sentry_sdk.integrations.loguru import LoguruIntegration   # ❌ logger.py acquiert
from sentry_sdk.integrations.logging import LoggingIntegration #    une 2ᵉ dépendance : sentry_sdk

def sentry_logging_integrations() -> list[Integration]:        # ❌ builder d'objets sentry_sdk
    return [LoguruIntegration(event_level=None, ...), LoggingIntegration(event_level=None, ...)]

# infrastructure/sentry.py  — AVANT
from mcr_meeting.app.infrastructure.logger import sentry_logging_integrations  # ❌ sentry → logger
```

- **Idées fausses** :
  - « `logger.py` est le foyer de tout ce qui touche au logging » → en réalité il encapsule **loguru** (l'émission de logs). Configurer une intégration Sentry encapsule **sentry_sdk**.
  - « Un fichier infra porte le nom du domaine fonctionnel » → en réalité il porte le nom de **la dépendance externe possédée** ; le critère de placement est « quel paquet ce code instancie-t-il ? ».
  - « `loguru` est partout dans infra, donc ajouter un import externe de plus est anodin » → `loguru` est une **facilité ambiante** (comme la stdlib) présente dans presque tous les fichiers ; `sentry_sdk` est un **service avec un domicile unique**. Les deux ne pèsent pas pareil.

- **Contre-mesures** :
  - (P1 — fait) Déplacer `logging_integrations()` dans `sentry.py` (propriétaire de `sentry_sdk`) ; `logger.py` ne connaît plus Sentry. `main.py` importe `setup_logging` de `logger` et `logging_integrations` de `sentry`. Chaque fichier infra reprend un seul service externe. Dépendances désormais unidirectionnelles : `main → {logger, sentry}`.

## Angle mort de détection

- **Prévention — typing / import-linter** : les contrats `import-linter` (`pyproject.toml`) encodent uniquement le **layering vertical** (`api > use_cases > {domain, db, infrastructure}`), l'I/O-lessness de `domain`, et l'indépendance des `use_cases`. **Aucun contrat ne régit la structure interne d'`infrastructure/`** → un fichier infra qui s'approprie un 2ᵉ SDK est *irreprésentable-invisible* : rien ne pouvait le refuser. C'est le garde-fou aveugle candidat.
- **Prévention — ruff/mypy** : muets par nature ; un import supplémentaire valide est syntaxiquement et typiquement correct.
- **Détection — tests** : les tests vérifient le **comportement** (pas d'event Sentry, 500 générique) ; un défaut purement topologique (qui importe qui) ne change aucun comportement observable → aucun test ne pouvait le voir, et c'est normal.
- **Détection — revue** : c'est le seul filet qui a fonctionné, et il a fonctionné (l'utilisateur a tiqué). Mais il reposait sur la vigilance humaine, pas sur un garde-fou outillé.

> **Fil conducteur** : le seul filet outillé capable d'attraper cette classe (import-linter) ne couvre que l'axe vertical ; l'axe « propriété des dépendances externes à l'intérieur d'une couche » n'est pas modélisé.

- **Contre-mesures détection** :
  - (P2 — à décider) Contrat `import-linter` `forbidden` : `infrastructure.logger` (et les autres wrappers non-Sentry) ne doivent pas importer `sentry_sdk`. Simple, mais **point fix** (ne couvre que Sentry).
  - (P3 — candidat, garder-fou anti-classe) Petit test CI/AST parcourant `infrastructure/*.py` et vérifiant que chaque SDK externe « service » (hors ambiants : `loguru`, `pydantic`, stdlib) n'a **qu'un seul fichier importateur**. Encode la vraie règle. ⚠️ à ne faire que si la classe se reproduit — sinon risque de garde-fou-bloat (principe 7).

## Éradication

- **Balayage effectué** (2026-07-22) : comptage des paquets externes importés par fichier dans `infrastructure/`. `loguru` est ambiant (quasi tous les fichiers) ; **aucun autre fichier ne co-importe `sentry_sdk`** après correction — `sentry.py` en est l'unique propriétaire. Le défaut était un **one-off introduit dans cette session**, pas une classe pré-existante dans le dépôt.
- Éradication retenue : **partage de l'apprentissage** (ce Dantotsu) — critère de placement d'un fichier infra = « quel SDK externe ce code instancie-t-il ? », pas le nom du domaine. Pour un one-off, c'est une éradication valide (principe 7) ; ne pas inventer de garde-fou lourd tant que la classe ne récidive pas.

## Mesures écartées

- « Interdire tout import infra→infra » — écarté : faux besoin, le dépôt a des imports infra→infra légitimes (helpers internes : `retry`, `compute_devices`, `logger.setup_logging`). La règle n'est pas « pas d'import mutuel » mais « un service externe = un propriétaire ».

## Reste à instruire

- Trancher P2 vs P3 : un contrat `import-linter` ciblé sur `sentry_sdk` suffit-il, ou vaut-il la peine d'outiller la règle générale « un SDK service = un fichier » ? À réévaluer si un 2ᵉ cas apparaît.
</content>
