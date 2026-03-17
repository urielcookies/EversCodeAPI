from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    ENV: str = "development"
    BLOG_DEMO_API_KEY: str

    # ever_apply
    CLERK_JWKS_URL: str              # From Clerk Dashboard → API Keys
    DEEPSEEK_API_KEY: str            # From DeepSeek Platform → API Keys
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    APIFY_API_TOKEN: str
    R2_ACCOUNT_ID: str               # Cloudflare Account ID
    R2_ACCESS_KEY_ID: str            # R2 API Token → Access Key ID
    R2_SECRET_ACCESS_KEY: str        # R2 API Token → Secret Access Key
    R2_BUCKET_NAME: str              # e.g. "ever-apply-resumes"
    R2_PUBLIC_URL: str               # Public bucket URL (e.g. https://pub-xxx.r2.dev)
    EVER_APPLY_ADMIN_KEY: str        # Protect /admin/* routes
    EVER_APPLY_MAX_JOBS: int = 50    # Max jobs to fetch per Apify run
    EVER_APPLY_SCHEDULER_ENABLED: bool = True  # Set to false to disable cron jobs

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton — import this everywhere instead of instantiating Settings() again
settings = Settings()
