"""
Döviz kuru servisi — TCMB (birincil) + Open Exchange Rate API (fallback).
Saatlik scheduler ile çağrılır, exchange_rates tablosuna kaydeder.
"""
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.exchange_rate import ExchangeRate

logger = logging.getLogger(__name__)

# ─── TCMB XML API ────────────────────────────────────────────────────────────

TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"


async def _fetch_tcmb() -> dict | None:
    """
    TCMB günlük kur XML'inden USD/TRY ve EUR/TRY alış kurlarını çeker.
    Returns: {"USD/TRY": Decimal, "EUR/TRY": Decimal} veya None (hata durumunda).
    """
    try:
        import xml.etree.ElementTree as ET

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(TCMB_URL)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        rates = {}

        for currency in root.findall(".//Currency"):
            code = currency.get("CurrencyCode", "")
            if code in ("USD", "EUR"):
                # ForexBuying = döviz alış kuru
                buying_el = currency.find("ForexBuying")
                if buying_el is not None and buying_el.text:
                    try:
                        rates[f"{code}/TRY"] = Decimal(buying_el.text)
                    except InvalidOperation:
                        pass

        if "USD/TRY" in rates and "EUR/TRY" in rates:
            logger.info(f"[TCMB] USD/TRY={rates['USD/TRY']}, EUR/TRY={rates['EUR/TRY']}")
            return rates

        logger.warning(f"[TCMB] Eksik veri: {rates}")
        return None

    except Exception as e:
        logger.warning(f"[TCMB] Hata: {e}")
        return None


# ─── Fallback: Open Exchange Rate API ────────────────────────────────────────

OPEN_ER_URL = "https://open.er-api.com/v6/latest/USD"


async def _fetch_open_er() -> dict | None:
    """
    Open Exchange Rate API'den USD/TRY ve EUR/TRY hesaplar.
    USD bazlı kur → EUR/TRY = USD/TRY ÷ USD/EUR
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(OPEN_ER_URL)
            resp.raise_for_status()

        data = resp.json()
        usd_try = data.get("rates", {}).get("TRY")
        usd_eur = data.get("rates", {}).get("EUR")

        if not usd_try or not usd_eur:
            logger.warning("[OpenER] TRY veya EUR kuru bulunamadı")
            return None

        usd_try_d = Decimal(str(usd_try))
        eur_try_d = usd_try_d / Decimal(str(usd_eur))

        rates = {
            "USD/TRY": usd_try_d.quantize(Decimal("0.000001")),
            "EUR/TRY": eur_try_d.quantize(Decimal("0.000001")),
        }
        logger.info(f"[OpenER] USD/TRY={rates['USD/TRY']}, EUR/TRY={rates['EUR/TRY']}")
        return rates

    except Exception as e:
        logger.warning(f"[OpenER] Hata: {e}")
        return None


# ─── Fetch & Store ───────────────────────────────────────────────────────────


async def fetch_and_store_rates() -> dict:
    """
    TCMB → fallback → DB kaydet. Saatlik scheduler çağırır.
    Returns: {"USD/TRY": float, "EUR/TRY": float, "source": str}
    """
    # TCMB öncelikli
    rates = await _fetch_tcmb()
    source = "tcmb"

    if not rates:
        rates = await _fetch_open_er()
        source = "exchangerate_api"

    if not rates:
        logger.error("[ExchangeRate] Hiçbir kaynaktan kur alınamadı!")
        return {"error": "no_source_available"}

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # Önceki kayıttan değişim yüzdesi hesapla
        for pair, rate in rates.items():
            prev = await db.execute(
                select(ExchangeRate.rate)
                .where(ExchangeRate.currency_pair == pair)
                .order_by(ExchangeRate.recorded_at.desc())
                .limit(1)
            )
            prev_rate = prev.scalar_one_or_none()

            change_pct = None
            if prev_rate and prev_rate > 0:
                change_pct = ((rate - prev_rate) / prev_rate * 100).quantize(Decimal("0.0001"))

            record = ExchangeRate(
                currency_pair=pair,
                rate=rate,
                change_pct=change_pct,
                source=source,
                recorded_at=now,
            )
            db.add(record)

        await db.commit()

    logger.info(f"[ExchangeRate] Kayıt edildi: {source} — {rates}")
    return {
        "USD/TRY": float(rates["USD/TRY"]),
        "EUR/TRY": float(rates["EUR/TRY"]),
        "source": source,
    }


# ─── Query Functions ─────────────────────────────────────────────────────────


async def get_latest_rates(db: AsyncSession) -> dict:
    """
    Son USD/TRY, EUR/TRY kurlarını döner.
    {"USD/TRY": 38.45, "EUR/TRY": 41.20, "usd_change_pct": 0.3, "eur_change_pct": -0.1, ...}
    """
    result = {}

    for pair in ("USD/TRY", "EUR/TRY"):
        row = await db.execute(
            select(ExchangeRate)
            .where(ExchangeRate.currency_pair == pair)
            .order_by(ExchangeRate.recorded_at.desc())
            .limit(1)
        )
        record = row.scalar_one_or_none()
        if record:
            prefix = pair[:3].lower()  # "usd" or "eur"
            result[pair] = float(record.rate)
            result[f"{prefix}_change_pct"] = float(record.change_pct) if record.change_pct else None
            result[f"{prefix}_source"] = record.source
            result[f"{prefix}_recorded_at"] = record.recorded_at.isoformat()

    return result


async def get_rate_trend(db: AsyncSession, days: int = 30) -> list[dict]:
    """
    Son N gün kur trendi. AI yorum üretimi için.
    Returns: [{"date": "2026-03-29", "USD/TRY": 38.4, "EUR/TRY": 41.1}, ...]
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Her gün ve pair için en son kaydı al (subquery ile günlük gruplama)
    rows = await db.execute(
        select(
            func.date(ExchangeRate.recorded_at).label("day"),
            ExchangeRate.currency_pair,
            func.max(ExchangeRate.rate).label("rate"),
        )
        .where(ExchangeRate.recorded_at >= since)
        .group_by(func.date(ExchangeRate.recorded_at), ExchangeRate.currency_pair)
        .order_by(func.date(ExchangeRate.recorded_at))
    )

    # Pivotla: her gün için USD/TRY ve EUR/TRY
    day_map: dict[str, dict] = {}
    for day, pair, rate in rows:
        day_str = str(day)
        if day_str not in day_map:
            day_map[day_str] = {"date": day_str}
        day_map[day_str][pair] = float(rate)

    return list(day_map.values())


async def get_currency_impact(db: AsyncSession) -> dict:
    """
    Son 7/30 gün kur değişimi + tahmini fiyat etkisi.
    AI yorum üreteci için context sağlar.
    """
    now = datetime.now(timezone.utc)

    impacts = {}
    for pair in ("USD/TRY", "EUR/TRY"):
        prefix = pair[:3].lower()
        data: dict = {"pair": pair}

        # Son kur
        latest_row = await db.execute(
            select(ExchangeRate.rate, ExchangeRate.recorded_at)
            .where(ExchangeRate.currency_pair == pair)
            .order_by(ExchangeRate.recorded_at.desc())
            .limit(1)
        )
        latest = latest_row.first()
        if not latest:
            impacts[prefix] = {"pair": pair, "available": False}
            continue

        current_rate = latest[0]
        data["current_rate"] = float(current_rate)

        # 7 ve 30 gün önceki kur
        for label, delta_days in [("7d", 7), ("30d", 30)]:
            target_date = now - timedelta(days=delta_days)
            old_row = await db.execute(
                select(ExchangeRate.rate)
                .where(
                    and_(
                        ExchangeRate.currency_pair == pair,
                        ExchangeRate.recorded_at <= target_date,
                    )
                )
                .order_by(ExchangeRate.recorded_at.desc())
                .limit(1)
            )
            old_rate = old_row.scalar_one_or_none()
            if old_rate and old_rate > 0:
                change = float((current_rate - old_rate) / old_rate * 100)
                data[f"change_{label}_pct"] = round(change, 2)
            else:
                data[f"change_{label}_pct"] = None

        # Tahmini etki yorumu
        change_7d = data.get("change_7d_pct")
        if change_7d is not None:
            if change_7d > 1:
                data["impact_summary"] = (
                    f"{pair.split('/')[0]} son 7 günde %{change_7d:.1f} arttı "
                    f"→ ithal elektronik fiyatları yükselebilir"
                )
            elif change_7d < -1:
                data["impact_summary"] = (
                    f"{pair.split('/')[0]} son 7 günde %{abs(change_7d):.1f} düştü "
                    f"→ ithal ürünlerde fiyat düşüşü beklenebilir"
                )
            else:
                data["impact_summary"] = (
                    f"{pair.split('/')[0]} son 7 günde stabil (%{change_7d:+.1f}) "
                    f"→ kur kaynaklı fiyat değişimi beklenmez"
                )

        impacts[prefix] = data

    return impacts
