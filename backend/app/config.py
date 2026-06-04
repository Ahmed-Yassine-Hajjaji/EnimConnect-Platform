from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    OPENAI_API_KEY: str
    # N8n webhook — reçoit les infos d'une nouvelle offre pour notifier les chefs
    N8N_WEBHOOK_URL: str
    # N8n webhook — reçoit la décision (validée/rejetée) pour notifier l'entreprise
    N8N_COMPANY_WEBHOOK_URL: str = ""
    HMAC_SECRET: str
    FRONTEND_URL: str = "https://enimconnect.duckdns.org"
    BACKEND_URL: str = "https://enimconnect.duckdns.org"   # URL publique du backend (pour les liens email)
    STORAGE_PATH: str = "./storage"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stockage des CV : "local" (disque) ou "s3" (Amazon S3).
    STORAGE_BACKEND: str = "local"
    S3_BUCKET: str = ""
    AWS_REGION: str = "eu-north-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    # Durée de validité des URL présignées servant les CV (secondes)
    S3_PRESIGN_EXPIRE: int = 300

    # SMTP — utilisé pour les emails transactionnels (ex: réinitialisation mot de passe)
    # Réutilise les variables N8N_SMTP_* déjà présentes dans .env
    N8N_SMTP_HOST: str = "smtp.gmail.com"
    N8N_SMTP_PORT: int = 587
    N8N_SMTP_USER: str = ""
    N8N_SMTP_PASS: str = ""
    N8N_SMTP_SENDER: str = "noreply@enimconnect.ma"
    N8N_SMTP_SSL: bool = False

    # Brevo (ex-Sendinblue) — API HTTP pour emails transactionnels
    BREVO_API_KEY: str = ""

    # Google OAuth — seul le domaine @enim.ac.ma est autorisé (étudiants)
    GOOGLE_CLIENT_ID: str = ""

    # Phase de test : si renseigné, TOUTES les notifications de décision destinées
    # aux entreprises sont redirigées vers cette adresse (au lieu de l'email réel
    # de l'entreprise), comme les CHEF_*_EMAIL pour les chefs. Laisser vide en prod.
    COMPANY_EMAIL_OVERRIDE: str = ""

    # Emails des chefs de département (configurables depuis .env)
    CHEF_INFO_EMAIL: str = ""
    CHEF_MAT_EMAIL: str = ""
    CHEF_EM_EMAIL: str = ""
    CHEF_GI_EMAIL: str = ""
    CHEF_GPI_EMAIL: str = ""
    CHEF_ST_EMAIL: str = ""
    CHEF_MINES_EMAIL: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore unknown vars (ex: N8N_SMTP_* utilisées par docker-compose)


settings = Settings()
