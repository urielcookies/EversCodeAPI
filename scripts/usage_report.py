"""
EverApply — Usage Report
Run: python scripts/usage_report.py
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from apps.ever_apply.models import User
from core.config import settings

# Scraper runs 2x/day on weekdays, 1x/day on weekends
# Average across 30 days: (22 weekdays × 2 + 8 weekend days × 1) / 30 ≈ 1.73 runs/day
# Simplified to 2 runs/day (conservative, matches weekday schedule)
RUNS_PER_DAY = 2
DAYS_PER_MONTH = 30


async def fetch_users():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
    await engine.dispose()
    return users


def calculate_apify_cost(n_active: int) -> float:
    jobs_per_month = settings.EVER_APPLY_MAX_JOBS * RUNS_PER_DAY * DAYS_PER_MONTH
    cost_per_user = (jobs_per_month / 1000) * settings.EVER_APPLY_APIFY_PPR
    return n_active * cost_per_user


def run_report(users: list, apify_balance: float, deepseek_balance: float):
    now = datetime.utcnow()
    trial_cutoff = now - timedelta(days=settings.EVER_APPLY_TRIAL_DAYS)

    free_users    = [u for u in users if u.is_whitelisted]
    trial_users   = [u for u in users if not u.is_whitelisted and u.created_at >= trial_cutoff]
    paying_users  = [u for u in users if not u.is_whitelisted and u.created_at < trial_cutoff]

    n_free    = len(free_users)
    n_trial   = len(trial_users)
    n_paying  = len(paying_users)
    n_active  = n_trial + n_paying  # both burn Apify + DeepSeek credits
    total     = len(users)

    monthly_revenue = n_paying * settings.EVER_APPLY_PRICE
    apify_cost      = calculate_apify_cost(n_active)
    deepseek_cost   = n_active * settings.EVER_APPLY_DEEPSEEK_COST
    total_cost      = apify_cost + deepseek_cost
    net_margin      = monthly_revenue - total_cost

    apify_daily    = apify_cost / DAYS_PER_MONTH if apify_cost > 0 else 0
    deepseek_daily = deepseek_cost / DAYS_PER_MONTH if deepseek_cost > 0 else 0
    apify_runway    = int(apify_balance / apify_daily) if apify_daily > 0 else None
    deepseek_runway = int(deepseek_balance / deepseek_daily) if deepseek_daily > 0 else None

    today = now.strftime("%Y-%m-%d")
    jobs_per_month = settings.EVER_APPLY_MAX_JOBS * RUNS_PER_DAY * DAYS_PER_MONTH

    print()
    print(f"EverApply — Usage Report ({today})")
    print("=" * 44)
    print(f"Total users:         {total:>4}")
    print(f"  Free (bypassed):   {n_free:>4}")
    print(f"  Active trial:      {n_trial:>4}")
    print(f"  Paying:            {n_paying:>4}")
    print()
    print("Revenue")
    print(f"  Monthly (est):     ${monthly_revenue:>6}  ({n_paying} x ${settings.EVER_APPLY_PRICE})")
    print()
    print("API costs (est/month)")
    print(f"  Active users:      {n_active:>4}  (trial + paying)")
    print(f"  Jobs/user/month:   {jobs_per_month:>4}  ({settings.EVER_APPLY_MAX_JOBS} jobs x {RUNS_PER_DAY} runs x {DAYS_PER_MONTH} days)")
    print(f"  Apify:             ${apify_cost:>7.2f}  ({n_active} x ${apify_cost / n_active:.2f})" if n_active else f"  Apify:             $  0.00")
    print(f"  DeepSeek:          ${deepseek_cost:>7.2f}  ({n_active} x ${settings.EVER_APPLY_DEEPSEEK_COST:.2f})" if n_active else f"  DeepSeek:          $  0.00")
    print(f"  Total:             ${total_cost:>7.2f}")
    print()
    if net_margin >= 0:
        print(f"Net margin (est):    ${net_margin:.2f}/month")
    else:
        print(f"Net margin (est):    -${abs(net_margin):.2f}/month  *** LOSS ***")
    print()
    print("Balances")
    print(f"  Apify:             ${apify_balance:.2f}")
    if apify_runway is not None:
        print(f"    Runway:          ~{apify_runway} days  (${apify_daily:.2f}/day)")
    else:
        print(f"    Runway:          N/A (no active users)")
    print(f"  DeepSeek:          ${deepseek_balance:.2f}")
    if deepseek_runway is not None:
        print(f"    Runway:          ~{deepseek_runway} days  (${deepseek_daily:.2f}/day)")
    else:
        print(f"    Runway:          N/A (no active users)")
    print()


async def main():
    print("\nFetching users from database...")
    users = await fetch_users()

    print(f"Found {len(users)} user(s).\n")
    apify_balance    = float(input("Apify current balance ($): ") or 0)
    deepseek_balance = float(input("DeepSeek current balance ($): ") or 0)

    run_report(users, apify_balance, deepseek_balance)


if __name__ == "__main__":
    asyncio.run(main())
