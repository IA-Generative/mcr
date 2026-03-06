from pydantic import BaseModel
from pydantic.fields import Field


class Content(BaseModel):
    discussions_summary: list[str] = Field(
        default_factory=list,
        description=(
            "Liste de 3 à 6 bullet points maximum résumant les faits saillants de la réunion, dans l'ordre chronologique d'apparition. "
            "Chaque entrée correspond à une idée unique (1 idée par bullet, jusqu'à 3 phrases maximum). "
            "Prioriser ce qui change quelque chose : décisions explicites, constats clés, blocages, risques, points à trancher. "
            "Formuler de manière factuelle et synthétique, sans paraphrase ni redondance."
        ),
    )
    to_do_list: list[str] = Field(
        default_factory=list,
        description=(
            "Liste dédupliquée des actions à faire identifiées dans la réunion, formulées de manière concise et claire. "
            "Chaque entrée correspond à une action concrète à entreprendre suite à la réunion. "
            "Préférer des formulations 'verbe + objet' (ex: 'Envoyer le compte-rendu à l'équipe'). "
            "Préciser si possible le responsable de l'action et la date limite pour la réaliser (ex: 'Envoyer le compte-rendu à l'équipe - Jean Dupont - 01/03/2026')."
        ),
    )
    to_monitor_list: list[str] = Field(
        default_factory=list,
        description=(
            "Liste dédupliquéedes points de vigilance à surveiller identifiés dans la réunion, formulés de manière concise et claire. "
            "Chaque entrée correspond à un point important à surveiller suite à la réunion. "
            "Préciser si possible le responsable du suivi de ce point (ex: 'Suivre l'évolution du projet X - Marie Curie )."
        ),
    )
