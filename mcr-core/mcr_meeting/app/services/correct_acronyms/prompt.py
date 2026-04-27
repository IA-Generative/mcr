from pathlib import Path

_GLOSSARY_PATH = Path(__file__).parent / "data" / "small_glossaire.md"
GLOSSARY_CONTENT = _GLOSSARY_PATH.read_text(encoding="utf-8")

ACRONYM_PROMPT_TEMPLATE = """
Tu corriges les acronymes mal transcrits dans une transcription vocale en français. Tu ne modifies RIEN d'autre.

# Types d'erreurs à corriger

1. Acronyme transcrit en mot français courant
   « opaque » → « OPAC », « café » → « CAF », « eau nue » → « ONU »

2. Acronyme commençant par A avec liaison avalée (uniquement après « la » ou « le »)
   « la NTS » → « l'ANTS », « la NTAI » → « l'ANTAI »

3. Chiffre dans un sigle indiquant une lettre doublée
   Quand un sigle contient un chiffre (souvent « 2 »), c'est généralement que le locuteur a dit « deux X » pour signaler que la lettre X est doublée dans l'acronyme.
   « AN2SI » → « ANSSI » (deux S) ; « A2IM » → « AAIM » (deux A) ; « CN2L » → « CNLL » (deux L).

4. Acronyme en majuscules très proche d'un acronyme connu (lettre manquante ou modifiée)
   « CMI » → « CCMI ».

# Source des acronymes de correction

Tu corriges en priorité vers les acronymes du glossaire fourni plus bas.
Tu peux aussi corriger vers un acronyme ABSENT du glossaire, mais UNIQUEMENT si cet acronyme est un sigle français très connu du grand public (ex : ONU, OTAN, SNCF, ANSSI, CNIL, INSEE, SMIC, RATP…) ET que la correction est évidente et sans ambiguïté.

Si l'acronyme cible est obscur, technique, ou que tu hésites sur sa forme exacte : NE CORRIGE PAS.

# Règles

1. Corrige UNIQUEMENT si : (a) ressemblance forte avec un acronyme connu ET (b) le contexte confirme sans effort.
2. En cas de doute, ne corrige pas. Une non-correction vaut mieux qu'une correction erronée.
3. Ne touche à aucun autre mot, même fautif. Ne modifie pas la ponctuation.
4. Garde les balises <separatorID> strictement identiques et à leur place.
5. Les acronymes corrigés s'écrivent en majuscules sans points (« ANTS », pas « A.N.T.S. »).

# Ce que tu ne dois JAMAIS faire

- Remplacer une forme développée par son acronyme.
  « direction générale des étrangers en France » RESTE tel quel, pas « DGEF ».
- Remplacer un acronyme par un autre très différent.
  « AN2SI » peut devenir « ANSSI » (le 2 = double S), mais PAS « DGSI » (trop différent).
- Inventer un acronyme que tu ne connais pas avec certitude.
- Corriger un acronyme déjà bien écrit (« ANTS » reste « ANTS »).
- Corriger un acronyme épelé (« D-G-P-N » reste « D-G-P-N »).
- Modifier « une NTS », « de NTS », « du NTS » — la règle de liaison ne s'applique qu'à « la » et « le ».

# Exemples

Glossaire pour les exemples : **OPAC**, **ANTS**, **DGEF**, **CCMI**, **DGSI**.

Entrée : Le locataire a contacté l'opaque pour signaler le problème.
Sortie : Le locataire a contacté l'OPAC pour signaler le problème.

Entrée : La NTS a transmis le dossier à la direction générale des étrangers en France.
Sortie : L'ANTS a transmis le dossier à la direction générale des étrangers en France.

Entrée : Le CMI a été signé avant la réunion avec l'AN2SI.
Sortie : Le CCMI a été signé avant la réunion avec l'ANSSI.

Entrée : Je suis ambassadeur de la France à l'eau nue.
Sortie : Je suis ambassadeur de la France à l'ONU.

# Glossaire à utiliser en priorité pour la correction
<<<
{glossary}
>>>

# Texte à corriger
<<<
{text}
>>>

Réponds uniquement avec le texte corrigé. Pas de préambule, pas d'explication, pas de commentaire.
"""
