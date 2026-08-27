---
name: update-glossary
description: Met à jour le glossaire d'acronymes du pipeline de transcription (mcr-core/.../prompts/data/glossary.md) à partir du CSV métier de référence. Trouve les définitions manquantes, les re-synthétise au format du glossaire et les insère à leur position alphabétique. Utiliser quand une nouvelle version du glossaire métier (CSV) doit être répercutée dans l'application.
argument-hint: "[chemin du CSV source]"
---

# Mise à jour du glossaire d'acronymes

<purpose>
Le CSV métier contient des paragraphes de contexte longs, rédigés par des humains. Le glossaire embarqué dans le prompt contient des définitions d'une phrase, normalisées, triées.

Ton travail est la re-synthèse : transformer chaque paragraphe CSV en une ligne de glossaire qui obéit aux 7 règles ci-dessous. Le diff, l'insertion triée et la validation sont déterministes et délégués à `scripts/glossary_tool.py` — ne les refais jamais à la main.
</purpose>

## Fichiers

- **Source** : le CSV passé en argument. Colonnes utilisées : `Acronyme`, `Signification littérale`, `Contexte`, `Statut`. `isAcronym` et `Prononciation` ne servent pas à la re-synthèse.
- **Seules les lignes `Statut = Production` sont livrables.** Le CSV est un document de travail vivant : une ligne encore en brouillon porte un autre statut et ne doit jamais atteindre le prompt. Le filtrage est automatique, mais reste la principale source d'erreur — une ligne ajoutée par erreur n'est visible qu'à la relecture du diff.
- **Cible** : `mcr-core/mcr_meeting/app/infrastructure/llm/prompts/data/glossary.md`.
- **Consommateur** : `mcr-core/mcr_meeting/app/infrastructure/llm/prompts/acronyms.py` charge le fichier entier et l'injecte dans le prompt de correction d'acronymes. Chaque entrée ajoutée coûte des tokens à chaque transcription.

Si aucun CSV n'est passé en argument, demande-le. N'invente pas de source.

## Étape 1 — Lister les définitions manquantes

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/glossary_tool.py missing \
  --csv <CSV> \
  --glossary mcr-core/mcr_meeting/app/infrastructure/llm/prompts/data/glossary.md
```

La sortie donne, pour chaque ligne CSV non couverte, son acronyme, sa signification littérale et son contexte aplati. Elle rappelle en tête le nombre de brouillons écartés — relis cette liste, c'est ton garde-fou contre une livraison prématurée. Elle tient compte de deux subtilités que tu ne dois pas retraiter toi-même :

- `AC / ADCE` dans le CSV est **une** ligne couvrant deux orthographes. Elle est couverte si l'une des deux existe déjà.
- Un acronyme homonyme (`BPI`, `CCP`, `CTA`) partage **une seule** entrée. S'il est déjà présent avec un sens, la ligne portant l'autre sens n'est pas signalée comme manquante.

Cette seconde règle a une conséquence : le script ne détecte pas un **second sens manquant sur une entrée existante**. Après l'étape 1, relis les acronymes présents plusieurs fois dans le CSV et vérifie à la main que l'entrée du glossaire porte bien tous leurs sens.

## Étape 2 — Re-synthétiser

Rédige une ligne par entrée manquante, dans un fichier de travail (un par ligne, pas de ligne vide).

<rules>
1. **Format strict** : `**ACRO** - Signification littérale - Définition.` Trois champs, séparateur ` - `, la définition finit par un point.
2. **Signification littérale en casse de phrase**, pas la casse du CSV. `Agence Nationale pour la Rénovation Urbaine` → `Agence nationale pour la rénovation urbaine`. Les noms propres gardent leur majuscule.
3. **Définition en une seule phrase nominale**, 15 à 30 mots, commençant par un nom de catégorie : `Établissement public…`, `Service déconcentré…`, `Dispositif…`, `Instance…`, `Document…`, `Unité…`, `Protocole…`, `Application…`.
4. **Jamais de forme verbale « Le X est… »**, jamais de numéro de décret. Une date n'est gardée que lorsqu'elle distingue l'entrée : création, remplacement d'un autre organisme, entrée en vigueur.
5. **Apostrophe droite `'`**, jamais `’`. Le CSV utilise l'apostrophe typographique, le glossaire non. C'est l'erreur la plus fréquente d'un copier-coller depuis le CSV.
6. **Sens multiples** : séparés par ` / ` dans la signification littérale, puis désambiguïsés dans la définition par un `;`. Modèles existants : `CCP`, `CTA`, `CMS`, `BPI`. **Variantes orthographiques d'un même sigle** : `**X** ou **Y** - …`. Modèles : `AC` / `ADCE`, `DDETSPP` / `DDETS-PP`.
7. **Tri alphabétique** sur la clé accents supprimés en majuscules — `TéléRC` se classe à `TELERC`. Tu n'as pas à trier toi-même, `merge` s'en charge.
</rules>

Deux corrections que tu appliques en silence, sans les signaler : les fautes de frappe du CSV (`publoc` → `public`) et les significations littérales tronquées quand le contexte donne la forme exacte.

Une définition est bonne quand elle aide un LLM à **désambiguïser** un sigle mal transcrit. Garde donc les mots distinctifs du domaine (le territoire, la tutelle, le sigle parent) et jette la prose institutionnelle générique.

## Étape 3 — Insérer

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/glossary_tool.py merge \
  --glossary mcr-core/mcr_meeting/app/infrastructure/llm/prompts/data/glossary.md \
  --entries <fichier de travail>
```

`merge` insère chaque entrée à sa position alphabétique, rétablit la ligne vide entre entrées, et **échoue** sur un doublon ou sur une ligne hors format. Un échec est une erreur de rédaction à corriger, pas un obstacle à contourner.

## Étape 4 — Vérifier

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/glossary_tool.py check \
  --csv <CSV> \
  --glossary mcr-core/mcr_meeting/app/infrastructure/llm/prompts/data/glossary.md
```

`check` sort en code 1 tant qu'il reste une ligne CSV non couverte, une ligne mal formée, une définition sans point final, une apostrophe typographique ou une rupture de tri. Ne t'arrête pas avant `OK`.

## Étape 5 — Rendre compte

Annonce, dans cet ordre :

1. Le nombre d'entrées avant → après, et le nombre de lignes CSV traitées.
2. Les fusions décidées : homonymes réunis en une entrée, variantes orthographiques réunies par `ou`.
3. Les brouillons écartés et les doublons CSV sans conséquence (même sens à la casse près), avec la raison de l'inaction.
4. L'impact sur le prompt : le glossaire est injecté en entier à chaque correction d'acronymes, donc en tokens par appel.
5. Les sigles courts et ambigus nouvellement ajoutés (`PP`, `BR`, `FS`, `3E`…) qui présentent un risque de sur-correction.

Le libellé de version affiché dans l'application vit dans `mcr-frontend/src/locales/fr.json`, clé `header.notice.article-link-text`. Propose de le bumper si la nouvelle livraison du CSV porte un numéro de version.
