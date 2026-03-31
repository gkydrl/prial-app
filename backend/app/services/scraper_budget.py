"""
ScraperAPI günlük bütçe kontrolü.
Günlük kredi kullanımını takip eder, limit aşılırsa sadece HIGH priority scrape'lere izin verir.

Kullanım:
    from app.services.scraper_budget import can_scrape, record_credit

    if await can_scrape(priority=3):
        result = await scrape_url(url)
        await record_credit()
"""
from __future__ import annotations

from datetime import datetime, timezone, date

# ── Ayarlar ──
MONTHLY_CREDIT_LIMIT = 1_000_000  # ScraperAPI $149 plan
DAILY_SAFE_LIMIT = 25_000         # Günlük güvenli limit (aylık/30 + %25 margin)
DAILY_HARD_LIMIT = 40_000         # Günlük sert limit (sadece HIGH priority)

# In-memory günlük sayaç (process başına — Railway tek process)
_daily_count: int = 0
_count_date: date | None = None


def _reset_if_new_day() -> None:
    """Yeni gün başladıysa sayacı sıfırla."""
    global _daily_count, _count_date
    today = date.today()
    if _count_date != today:
        _daily_count = 0
        _count_date = today


async def record_credit(count: int = 1) -> None:
    """Kullanılan krediyi kaydet."""
    global _daily_count
    _reset_if_new_day()
    _daily_count += count


async def can_scrape(priority: int = 3) -> bool:
    """
    Scrape yapılabilir mi kontrol et.

    priority 1 (HIGH): Her zaman izin ver (alarm tetikleme kritik)
    priority 2 (MEDIUM): DAILY_HARD_LIMIT altındaysa izin ver
    priority 3 (LOW): DAILY_SAFE_LIMIT altındaysa izin ver
    """
    _reset_if_new_day()

    if priority <= 1:
        return True  # HIGH priority her zaman geçer

    if priority == 2:
        return _daily_count < DAILY_HARD_LIMIT

    # LOW priority
    return _daily_count < DAILY_SAFE_LIMIT


def get_budget_status() -> dict:
    """Güncel bütçe durumunu döner (admin endpoint için)."""
    _reset_if_new_day()
    return {
        "date": str(_count_date),
        "credits_used_today": _daily_count,
        "daily_safe_limit": DAILY_SAFE_LIMIT,
        "daily_hard_limit": DAILY_HARD_LIMIT,
        "monthly_limit": MONTHLY_CREDIT_LIMIT,
        "utilization_pct": round(_daily_count / DAILY_SAFE_LIMIT * 100, 1) if DAILY_SAFE_LIMIT > 0 else 0,
        "status": (
            "ok" if _daily_count < DAILY_SAFE_LIMIT
            else "throttled" if _daily_count < DAILY_HARD_LIMIT
            else "critical"
        ),
    }
