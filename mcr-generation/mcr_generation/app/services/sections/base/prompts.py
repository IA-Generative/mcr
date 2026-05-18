NOTES_SECTION_TEMPLATE = """\
## Notes du rédacteur (signal humain)

{notes_hint_json}

### Comment utiliser ces notes
- Les notes ci-dessus sont une **information supplémentaire et plus fiable** que les extraits de transcription. Elles signalent les éléments que le rédacteur du meeting a jugés notables.
- Si une information apparaît dans la transcription mais **pas** dans les notes : tu la **gardes** ; les notes ne sont pas exhaustives et leur silence sur un point n'invalide pas la transcription.
- Si une information apparaît dans **les notes** et **pas dans la transcription** : tu peux légitimement l'inclure dans le résultat final si elle a du sens dans le contexte du meeting.
- Si une information de la transcription **contredit** une information des notes : **les notes priment**, c'est leur version que tu retiens.
"""
