from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://oson:oson_secret@db:5432/oson_ijara"
    secret_key: str = "please-change-this-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    upload_dir: str = "uploads"
    base_url: str = "http://localhost:8000"

    # Optional: Cloudflare R2 (S3-compatible) object storage for uploads.
    # If any of these are left empty, uploads fall back to local disk
    # storage automatically (fine for local dev; on a host with no
    # persistent disk like Render's free tier, files won't survive a
    # restart unless these are set).
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_url: str = ""  # e.g. https://pub-xxxxxxxx.r2.dev or a custom domain

    @property
    def r2_configured(self) -> bool:
        return bool(
            self.r2_account_id
            and self.r2_access_key_id
            and self.r2_secret_access_key
            and self.r2_bucket_name
            and self.r2_public_url
        )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

