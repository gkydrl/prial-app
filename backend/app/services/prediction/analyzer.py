"""
Istatistiksel feature hesaplama — fiyat tahmin motoru icin.
Pure Python math, numpy gerekmez.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass
class PriceFeatures:
    """Tahmin motoru icin hesaplanan feature'lar."""
    current_price: float
    avg_30d: float | None
    avg_90d: float | None
    l1y_min: float | None
    l1y_max: float | None
    percentile: float | None  # 0.0 (en dusuk) - 1.0 (en yuksek)
    trend_7d: float | None    # % degisim
    trend_30d: float | None   # % degisim
    volatility_30d: float | None  # varyasyon katsayisi (CV)
    drop_frequency: int | None    # yilda kac kez >5% dusus
    seasonal_score: float | None  # mevcut ay vs yillik ort. farki
    near_historical_low: bool


@dataclass
class PricePoint:
    date: date
    price: float


def compute_features(
    current_price: float,
    price_history: list[PricePoint],
    l1y_min: float | None = None,
    l1y_max: float | None = None,
) -> PriceFeatures:
    """
    Fiyat gecmisi ve mevcut fiyattan tum feature'lari hesapla.
    price_history: kronolojik sira (eskiden yeniye)
    """
    today = date.today()

    # Filter to relevant periods
    last_7d = [p for p in price_history if (today - p.date).days <= 7]
    last_30d = [p for p in price_history if (today - p.date).days <= 30]
    last_90d = [p for p in price_history if (today - p.date).days <= 90]
    last_1y = [p for p in price_history if (today - p.date).days <= 365]

    # l1y min/max: use provided values or compute from history
    if l1y_min is None and last_1y:
        l1y_min = min(p.price for p in last_1y)
    if l1y_max is None and last_1y:
        l1y_max = max(p.price for p in last_1y)

    # Averages
    avg_30d = _mean([p.price for p in last_30d]) if last_30d else None
    avg_90d = _mean([p.price for p in last_90d]) if last_90d else None

    # Percentile: current price position within 1y range
    percentile = None
    if l1y_min is not None and l1y_max is not None and l1y_max > l1y_min:
        percentile = (current_price - l1y_min) / (l1y_max - l1y_min)
        percentile = max(0.0, min(1.0, percentile))

    # Trend calculations (% change)
    trend_7d = _calc_trend(last_7d, current_price) if len(last_7d) >= 2 else None
    trend_30d = _calc_trend(last_30d, current_price) if len(last_30d) >= 2 else None

    # Volatility: coefficient of variation (std/mean) for last 30 days
    volatility_30d = _calc_volatility([p.price for p in last_30d]) if len(last_30d) >= 3 else None

    # Drop frequency: times price dropped >5% in a week within last year
    drop_frequency = _calc_drop_frequency(last_1y) if len(last_1y) >= 7 else None

    # Seasonal score: current month average vs yearly average
    seasonal_score = _calc_seasonal_score(last_1y, today.month) if len(last_1y) >= 30 else None

    # Near historical low: within 5% of l1y_min
    near_low = False
    if l1y_min is not None and l1y_min > 0:
        near_low = current_price <= l1y_min * 1.05

    return PriceFeatures(
        current_price=current_price,
        avg_30d=avg_30d,
        avg_90d=avg_90d,
        l1y_min=l1y_min,
        l1y_max=l1y_max,
        percentile=percentile,
        trend_7d=trend_7d,
        trend_30d=trend_30d,
        volatility_30d=volatility_30d,
        drop_frequency=drop_frequency,
        seasonal_score=seasonal_score,
        near_historical_low=near_low,
    )


def _mean(values: list[float]) -> float | None:
    """Ortalama hesapla."""
    if not values:
        return None
    return sum(values) / len(values)


def _calc_trend(points: list[PricePoint], current: float) -> float | None:
    """
    Periyodun basindaki fiyattan mevcut fiyata % degisim.
    Pozitif = fiyat artti, negatif = fiyat dustu.
    """
    if not points:
        return None
    oldest = points[0].price
    if oldest == 0:
        return None
    return ((current - oldest) / oldest) * 100


def _calc_volatility(prices: list[float]) -> float | None:
    """Varyasyon katsayisi (CV) = stddev / mean."""
    if len(prices) < 3:
        return None
    mean = sum(prices) / len(prices)
    if mean == 0:
        return None
    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
    stddev = math.sqrt(variance)
    return stddev / mean


def _calc_drop_frequency(points: list[PricePoint]) -> int:
    """
    Yillik fiyat gecmisinde kac kez >5% haftalik dusus olmus.
    Bir "drop event": 7 gunluk pencerede %5'den fazla dusus.
    """
    if len(points) < 7:
        return 0

    drops = 0
    # Sort by date
    sorted_points = sorted(points, key=lambda p: p.date)

    i = 0
    while i < len(sorted_points) - 1:
        # Find price 7 days later
        start_price = sorted_points[i].price
        start_date = sorted_points[i].date
        target_date = start_date + timedelta(days=7)

        # Find closest point to target_date
        j = i + 1
        while j < len(sorted_points) and sorted_points[j].date < target_date:
            j += 1

        if j < len(sorted_points) and start_price > 0:
            end_price = sorted_points[min(j, len(sorted_points) - 1)].price
            change = (end_price - start_price) / start_price
            if change < -0.05:  # >5% drop
                drops += 1

        i += 1

    return drops


def _calc_seasonal_score(points: list[PricePoint], current_month: int) -> float | None:
    """
    Mevcut ayin ortalama fiyati vs yillik ortalama.
    Negatif = mevcut ay yillik ortalamadan ucuz, pozitif = pahali.
    Returns: -1.0 to 1.0 (normalized)
    """
    if not points:
        return None

    yearly_mean = _mean([p.price for p in points])
    if not yearly_mean or yearly_mean == 0:
        return None

    current_month_prices = [p.price for p in points if p.date.month == current_month]
    if not current_month_prices:
        return None

    month_mean = _mean(current_month_prices)
    if month_mean is None:
        return None

    # Normalized difference: (month_avg - yearly_avg) / yearly_avg
    score = (month_mean - yearly_mean) / yearly_mean
    return max(-1.0, min(1.0, score))
