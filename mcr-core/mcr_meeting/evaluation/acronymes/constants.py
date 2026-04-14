# Closed list of the 20 acronyms spoken once in each audio file of the dataset
# `mcr_meeting/evaluation/data/acronymes/audio/`. Order is preserved to
# guarantee stable CSV output across runs.
#
# Collision check (regex \b...\b): no acronym in this list is a whole-word
# substring of another. In particular:
#   - "ANTS" and "ANTAI" have different endings (S vs AI)
#   - all "DG*" acronyms differ in the last 2 letters
#   - "DNPJ" / "DNPAF" / "DNSP" / "DNRT" are distinct
ACRONYMES: list[str] = [
    "DGPN",
    "DGGN",
    "DGSI",
    "DGEF",
    "DGCL",
    "ANTS",
    "ANTAI",
    "ANFSI",
    "DNPJ",
    "DNPAF",
    "DNSP",
    "DNRT",
    "IGPN",
    "CNAPS",
    "ACMOSS",
    "CCMI",
    "DCIS",
    "SSMSI",
    "DCCRS",
    "SNPS",
]
