"""Envoi d'emails transactionnels via SMTP (réutilise la config N8N_SMTP_*)."""
import ssl
import smtplib
import logging
from email.message import EmailMessage
from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """Envoie un email HTML (avec repli texte). Retourne True si l'envoi a réussi."""
    host = settings.N8N_SMTP_HOST
    if not host or not settings.N8N_SMTP_USER:
        logger.warning("[email] SMTP non configuré — email non envoyé à %s", to_email)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.N8N_SMTP_SENDER or settings.N8N_SMTP_USER
    msg["To"] = to_email
    msg.set_content(text_body or "Veuillez utiliser un client compatible HTML pour lire cet email.")
    msg.add_alternative(html_body, subtype="html")

    try:
        context = ssl.create_default_context()
        if settings.N8N_SMTP_SSL:
            with smtplib.SMTP_SSL(host, settings.N8N_SMTP_PORT, context=context, timeout=15) as server:
                server.login(settings.N8N_SMTP_USER, settings.N8N_SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, settings.N8N_SMTP_PORT, timeout=15) as server:
                server.starttls(context=context)
                server.login(settings.N8N_SMTP_USER, settings.N8N_SMTP_PASS)
                server.send_message(msg)
        logger.info("[email] envoyé à %s — %r", to_email, subject)
        return True
    except Exception as e:
        logger.error("[email] échec envoi à %s: %s", to_email, e)
        return False


def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    """Email de réinitialisation de mot de passe (lien valable 1h)."""
    subject = "Réinitialisation de votre mot de passe — EnimConnect"
    html = f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;color:#1a1c1e">
  <h2 style="color:#1a4cc4">EnimConnect</h2>
  <p>Bonjour,</p>
  <p>Vous avez demandé la réinitialisation de votre mot de passe. Cliquez sur le bouton
     ci-dessous pour en choisir un nouveau :</p>
  <p style="text-align:center;margin:28px 0">
    <a href="{reset_link}"
       style="background:#1a4cc4;color:#fff;text-decoration:none;padding:12px 28px;
              border-radius:10px;font-weight:bold;display:inline-block">
      Réinitialiser mon mot de passe
    </a>
  </p>
  <p style="font-size:13px;color:#5a5d63">Ce lien expire dans 1 heure. Si vous n'êtes pas à
     l'origine de cette demande, ignorez simplement cet email — votre mot de passe restera inchangé.</p>
  <p style="font-size:12px;color:#9aa0a6;word-break:break-all">Si le bouton ne fonctionne pas,
     copiez ce lien dans votre navigateur :<br>{reset_link}</p>
</div>"""
    text = (
        "Vous avez demandé la réinitialisation de votre mot de passe EnimConnect.\n"
        f"Ouvrez ce lien (valable 1 heure) pour en choisir un nouveau :\n{reset_link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email."
    )
    return send_email(to_email, subject, html, text)
