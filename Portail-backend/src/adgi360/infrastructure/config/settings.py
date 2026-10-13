from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration centralisée, chargée depuis les variables d'environnement / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de données
    database_url: str = "postgresql+asyncpg://adgi360:adgi360@localhost:5433/adgi360"

    # Stockage fichiers (MinIO en local, S3 en production)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "adgi360"
    s3_secret_key: str = "adgi360secret"
    s3_bucket: str = "adgi360-files"
    s3_region: str = "us-east-1"
    # Endpoint annoncé au NAVIGATEUR dans les URL pré-signées. En production, le
    # backend parle à MinIO par le réseau interne Docker (s3_endpoint_url) mais
    # le navigateur, lui, a besoin d'un domaine public. Vide = même endpoint,
    # ce qui correspond au poste de développement.
    s3_public_endpoint_url: str = ""
    # Endpoint utilisé pour SIGNER les URL remises à n8n. Il diffère de
    # s3_endpoint_url en développement : le navigateur joint MinIO sur
    # localhost, le conteneur n8n sur host.docker.internal. L'hôte fait partie
    # des en-têtes signés en SigV4 — on ne peut donc pas réécrire l'URL après
    # coup, il faut signer avec le bon endpoint dès le départ.
    # En production, les deux valeurs pointent sur le même domaine public.
    s3_n8n_endpoint_url: str = "http://host.docker.internal:9000"

    # n8n — workflow d'analyse (un seul webhook, pas d'envoi de mail)
    n8n_webhook_url: str = "http://localhost:5678/webhook/auto-review"
    # Adresse à laquelle n8n rappelle le backend. Vue depuis le conteneur n8n,
    # l'hôte s'appelle host.docker.internal — pas localhost.
    backend_public_url: str = "http://host.docker.internal:8001"

    # --- Bot Telegram (via n8n)
    # Secret partagé entre n8n et le backend pour les routes /api/v1/bot.
    # n8n l'envoie dans l'en-tête X-Bot-Token. Vide = routes du bot désactivées.
    bot_api_token: str = ""

    # --- Sécurité
    # Valeur de développement uniquement : en production, SECRET_KEY doit être
    # fournie par l'environnement, sinon les jetons de toutes les instances
    # seraient interchangeables.
    secret_key: str = "dev-secret-a-remplacer-en-production"
    # Clé distincte utilisée pour chiffrer les jetons des régies publicitaires.
    # Vide en développement = repli sur secret_key. En production, fournir une
    # valeur dédiée et stable : la changer rend les identifiants existants
    # illisibles.
    credentials_encryption_key: str = ""
    access_token_ttl_minutes: int = 60 * 12

    # Version de l'API Graph utilisée pour Meta Ads et Instagram.
    meta_graph_api_version: str = "v23.0"

    # CORS
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
