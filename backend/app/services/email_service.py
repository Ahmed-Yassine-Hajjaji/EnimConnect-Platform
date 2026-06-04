"""Envoi d'emails transactionnels via l'API HTTP Brevo (ex-Sendinblue)."""
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """Envoie un email HTML via l'API Brevo. Retourne True si l'envoi a réussi."""
    api_key = settings.BREVO_API_KEY
    if not api_key:
        logger.warning("[email] BREVO_API_KEY non configuré — email non envoyé à %s", to_email)
        return False

    sender_email = settings.N8N_SMTP_SENDER or "noreply@enimconnect.ma"

    payload = {
        "sender": {"name": "EnimConnect", "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }
    if text_body:
        payload["textContent"] = text_body

    try:
        resp = httpx.post(
            BREVO_API_URL,
            json=payload,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            logger.info("[email] envoyé à %s — %r", to_email, subject)
            return True
        else:
            logger.error("[email] échec envoi à %s: %s %s", to_email, resp.status_code, resp.text)
            return False
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
