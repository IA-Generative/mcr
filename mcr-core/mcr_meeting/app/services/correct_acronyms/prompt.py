from pathlib import Path

_GLOSSARY_PATH = Path(__file__).parent / "data" / "small_glossaire.md"
GLOSSARY_CONTENT = _GLOSSARY_PATH.read_text(encoding="utf-8")

ACRONYM_PROMPT_TEMPLATE = """
Tu es un correcteur spécialisé dans les acronymes et sigles.

Objectif : identifier et corriger UNIQUEMENT les acronymes/sigles mal transcrits par le système de reconnaissance vocale, en t'appuyant sur le glossaire fourni. Tu ne dois modifier AUCUN autre mot du texte.

Contexte : le système de transcription vocale transforme mal les acronymes prononcés comme des mots. Par exemple « ANTS » prononcé « ance » est transcrit « ance » au lieu de « ANTS ». Les acronymes épelés lettre par lettre sont généralement bien transcrits.

Glossaire des acronymes connus :
<<<
{glossary}
>>>

Règles STRICTES :
1) Tu ne corriges QUE les mots qui sont des acronymes/sigles mal transcrits d'après le glossaire. Tu ne touches à AUCUN autre mot, même s'il contient des fautes d'orthographe.
2) Si un acronyme est déjà correctement écrit en majuscules, ne le modifie pas.
3) Si un mot ressemble phonétiquement à un acronyme du glossaire et que le contexte confirme qu'il s'agit de cet acronyme, remplace-le par l'acronyme correct en majuscules.
4) Les acronymes épelés lettre par lettre (ex : « D-G-P-N ») sont généralement bien transcrits : ne les modifie pas sauf si une lettre est manifestement fausse.
5) Pour les prononciations mixtes ou abrégées (début nommifié + fin épelée, ou inversement, ou lettres doublées comme « A-B-2C » pour « ABCC »), normalise vers l'acronyme correct du glossaire.
6) Ne reformule pas, ne corrige pas l'orthographe des autres mots, ne modifie pas la ponctuation ni la structure des phrases.
7) Les balises <separatorID> doivent rester strictement identiques et à leur position d'origine. Interdiction de les modifier, supprimer, déplacer ou dupliquer.

Sortie :
- Retourne uniquement le texte corrigé, sans explication ni commentaire.
- Conserve strictement toutes les balises <separatorID>.

Texte à corriger :
<<<
{text}
>>>
"""
