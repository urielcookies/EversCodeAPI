from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
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
    CLERK_WEBHOOK_SECRET: str = ""   # Clerk Dashboard → Webhooks → signing secret
    EVER_APPLY_MAX_JOBS: int = 50             # Max jobs to fetch per Apify run
    EVER_APPLY_SCHEDULER_ENABLED: bool = True  # Set to false to disable cron jobs
    EVER_APPLY_PRICE: int = 40                # Monthly subscription price in USD
    EVER_APPLY_APIFY_PPR: float = 5.0         # Apify price per 1,000 results (PPR)
    EVER_APPLY_DEEPSEEK_COST: float = 1.47    # Estimated DeepSeek cost per active user/month
                                               # Based on: 6000 jobs x 800 input tokens x $0.28/1M
                                               #         + 6000 jobs x 50 output tokens x $0.42/1M
                                               # Update if pricing changes: platform.deepseek.com/docs/pricing
    EVER_APPLY_TRIAL_DAYS: int = 7            # Free trial length in days
    ATS_DAILY_LIMIT_DEFAULT: int = 5          # Max ATS resume generations per day for regular users
    ATS_DAILY_LIMIT_WHITELISTED: int = 20    # Max ATS resume generations per day for whitelisted users

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton — import this everywhere instead of instantiating Settings() again
settings = Settings()
