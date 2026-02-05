def get_transcription_generation_success_email_template(
    meeting_name: str,
    meeting_link: str,
) -> str:
    return f"""
            <p>Bonjour,</p>
            <p>La transcription de votre réunion {meeting_name} est prête.</p>
            <p><a href="{meeting_link}">Accéder à la page de la réunion</a> pour la télécharger.</p>
            <p>Merci d'utiliser notre service.</p>
            <p>Cordialement,</p>
            <p>L'équipe MIrAI Compte Rendu</p>
            """


def get_report_generation_success_email_template(
    meeting_name: str,
    meeting_link: str,
) -> str:
    return f"""
            <p>Bonjour,</p>
            <p>Le relevé de décisions de votre réunion {meeting_name} est prêt.</p>
            <p><a href="{meeting_link}">Accéder à la page de la réunion</a> pour le télécharger.</p>
            <p>Merci d'utiliser notre service.</p>
            <p>Cordialement,</p>
            <p>L'équipe MIrAI Compte Rendu</p>"""
