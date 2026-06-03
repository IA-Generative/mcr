NARRATIVE_PROMPT_TEMPLATE = """
Tu es un rédacteur qui transforme une transcription verbatim en synthèse narrative.

Ta mission : tourner le dialogue ci-dessous en **discours indirect** sous la forme
« X a dit que Y », « Z a répondu que A », « W a demandé… ». Le résultat doit se lire
comme une synthèse fluide de ce qui s'est dit, **pas** comme une retranscription
mot-à-mot.

Mapping entre les interlocuteurs et leurs noms/rôles si disponible : {speaker_mapping}

Règles :
- Conserve l'identité et l'ordre chronologique des interventions.
- Une phrase indirecte par intervention significative ; tu peux regrouper plusieurs
  phrases courtes d'un même interlocuteur en une seule phrase « X a évoqué A et B ».
- Garde les chiffres, dates et noms propres exacts.
- Ne change pas le sens. Si une intervention est ambiguë, conserve l'ambiguïté plutôt
  que d'inventer une interprétation.
- Pas d'analyse ni d'opinion : tu ne fais que rapporter.
- Si un interlocuteur est étiqueté Intervenant_NN (ou ancien format SPEAKER_NN) faute
  de nom détecté, garde cette étiquette telle quelle.

Tu réponds avec **uniquement** la version reformulée, sans commentaire ni préambule,
en français.

Texte à reformuler :
---
{chunk_text}
---
"""
