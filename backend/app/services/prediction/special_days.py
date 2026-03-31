"""
Ozel gunler takvimi — AL/BEKLE tahmin motoru icin.
2-3 hafta ilerideki indirim donemlerini tespit eder.

Turkiye ve global alisveris etkinlikleri:
- Sabit tarihli: Black Friday, 11.11, yilbasi, vb.
- Degisken tarihli: Ramazan/Kurban bayrami (Hicri takvim)
- Mevcut yil + sonraki yil icin hesaplanir
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class EventCategory(str, Enum):
    """Etkinlik kategorisi."""
    GLOBAL_SALE = "global_sale"        # Black Friday, 11.11, vb.
    NATIONAL_HOLIDAY = "national_holiday"  # Bayramlar
    SEASONAL_SALE = "seasonal_sale"    # Yaz/kis indirimleri
    BACK_TO_SCHOOL = "back_to_school"  # Okul donemi
    NEW_PRODUCT = "new_product"        # Yeni urun lansman donemi


@dataclass
class SpecialDay:
    """Tek bir ozel gun/donem."""
    name: str
    start: date
    end: date
    category: EventCategory
    # Ortalama indirim etkisi (negatif = fiyat duser)
    expected_discount_pct: float
    # Hangi kategorileri etkiler (bos = hepsini)
    affected_categories: list[str]


# -- Sabit tarihli etkinlikler (her yil ayni) --

def _fixed_events(year: int) -> list[SpecialDay]:
    """Sabit tarihli yillik etkinlikler."""
    return [
        # Yilbasi indirimleri (Aralik sonu - Ocak basi)
        SpecialDay(
            name="Yılbaşı İndirimleri",
            start=date(year, 12, 20),
            end=date(year, 12, 31),
            category=EventCategory.SEASONAL_SALE,
            expected_discount_pct=-10,
            affected_categories=[],  # Hepsi
        ),
        SpecialDay(
            name="Yeni Yıl İndirimleri",
            start=date(year, 1, 1),
            end=date(year, 1, 10),
            category=EventCategory.SEASONAL_SALE,
            expected_discount_pct=-8,
            affected_categories=[],
        ),

        # Sevgililer Gunu (14 Subat oncesi)
        SpecialDay(
            name="Sevgililer Günü",
            start=date(year, 2, 7),
            end=date(year, 2, 14),
            category=EventCategory.SEASONAL_SALE,
            expected_discount_pct=-5,
            affected_categories=["Akıllı Saat", "Kol Saati", "Kulaklık", "Telefon", "Tablet"],
        ),

        # 8 Mart (Kadinlar Gunu)
        SpecialDay(
            name="Kadınlar Günü",
            start=date(year, 3, 4),
            end=date(year, 3, 8),
            category=EventCategory.SEASONAL_SALE,
            expected_discount_pct=-5,
            affected_categories=["Kişisel Bakım", "Akıllı Saat", "Kulaklık"],
        ),

        # 23 Nisan
        SpecialDay(
            name="23 Nisan İndirimleri",
            start=date(year, 4, 20),
            end=date(year, 4, 25),
            category=EventCategory.NATIONAL_HOLIDAY,
            expected_discount_pct=-5,
            affected_categories=["Tablet", "Bilgisayar", "Oyun Konsolu"],
        ),

        # Anneler Gunu (Mayis 2. Pazar — yaklasik 10-14 Mayis arasi)
        SpecialDay(
            name="Anneler Günü",
            start=date(year, 5, 7),
            end=date(year, 5, 14),
            category=EventCategory.SEASONAL_SALE,
            expected_discount_pct=-5,
            affected_categories=["Kişisel Bakım", "Ev Aleti", "Beyaz Eşya", "Telefon"],
        ),

        # Babalar Gunu (Haziran 3. Pazar — yaklasik 15-21 Haziran)
        SpecialDay(
            name="Babalar Günü",
            start=date(year, 6, 14),
            end=date(year, 6, 21),
            category=EventCategory.SEASONAL_SALE,
            expected_discount_pct=-5,
            affected_categories=["Telefon", "Akıllı Saat", "Kol Saati", "Kulaklık"],
        ),

        # Yaz indirimleri (Haziran ortasi - Temmuz)
        SpecialDay(
            name="Yaz İndirimleri",
            start=date(year, 6, 20),
            end=date(year, 7, 15),
            category=EventCategory.SEASONAL_SALE,
            expected_discount_pct=-12,
            affected_categories=[],  # Hepsi
        ),

        # Okul donemi (Agustos sonu - Eylul basi)
        SpecialDay(
            name="Okula Dönüş Kampanyaları",
            start=date(year, 8, 20),
            end=date(year, 9, 15),
            category=EventCategory.BACK_TO_SCHOOL,
            expected_discount_pct=-10,
            affected_categories=["Bilgisayar", "Laptop", "Tablet", "Telefon", "Kulaklık", "Depolama", "Monitor"],
        ),

        # Apple yeni iPhone lansmani (Eylul ortasi) — eski modeller ucuzlar
        SpecialDay(
            name="Apple Yeni Ürün Lansmanı",
            start=date(year, 9, 10),
            end=date(year, 9, 25),
            category=EventCategory.NEW_PRODUCT,
            expected_discount_pct=-8,
            affected_categories=["Telefon", "Akıllı Saat", "Tablet", "Kulaklık"],
        ),

        # 29 Ekim
        SpecialDay(
            name="29 Ekim İndirimleri",
            start=date(year, 10, 27),
            end=date(year, 10, 31),
            category=EventCategory.NATIONAL_HOLIDAY,
            expected_discount_pct=-5,
            affected_categories=[],
        ),

        # 11.11 (Bekarlar Gunu / Alisveris Festivali)
        SpecialDay(
            name="11.11 Alışveriş Festivali",
            start=date(year, 11, 8),
            end=date(year, 11, 13),
            category=EventCategory.GLOBAL_SALE,
            expected_discount_pct=-15,
            affected_categories=[],  # Hepsi
        ),

        # Black Friday (Kasim son Cuma — yaklasik 22-29 Kasim)
        SpecialDay(
            name="Black Friday / Efsane Cuma",
            start=date(year, 11, 20),
            end=date(year, 11, 30),
            category=EventCategory.GLOBAL_SALE,
            expected_discount_pct=-20,
            affected_categories=[],  # Hepsi — en buyuk indirim donemi
        ),

        # Cyber Monday (Black Friday sonrasi Pazartesi)
        SpecialDay(
            name="Cyber Monday",
            start=date(year, 12, 1),
            end=date(year, 12, 3),
            category=EventCategory.GLOBAL_SALE,
            expected_discount_pct=-15,
            affected_categories=["Bilgisayar", "Laptop", "Telefon", "Tablet", "Monitor", "Depolama"],
        ),

        # 12.12
        SpecialDay(
            name="12.12 İndirim Günü",
            start=date(year, 12, 10),
            end=date(year, 12, 14),
            category=EventCategory.GLOBAL_SALE,
            expected_discount_pct=-10,
            affected_categories=[],
        ),
    ]


# -- Degisken tarihli bayramlar (Hicri takvim) --
# Hicri takvim her yil ~10-11 gun geriye kayar.
# 2025-2028 icin yaklasik tarihler hardcoded.

_RAMAZAN_BAYRAMI = {
    2025: (date(2025, 3, 30), date(2025, 4, 1)),
    2026: (date(2026, 3, 20), date(2026, 3, 22)),
    2027: (date(2027, 3, 9), date(2027, 3, 11)),
    2028: (date(2028, 2, 27), date(2028, 2, 29)),
}

_KURBAN_BAYRAMI = {
    2025: (date(2025, 6, 6), date(2025, 6, 9)),
    2026: (date(2026, 5, 26), date(2026, 5, 29)),
    2027: (date(2027, 5, 16), date(2027, 5, 19)),
    2028: (date(2028, 5, 4), date(2028, 5, 7)),
}


def _religious_events(year: int) -> list[SpecialDay]:
    """Dini bayramlar oncesi indirim donemleri."""
    events = []

    # Ramazan Bayrami oncesi (bayramdan 2 hafta once kampanyalar baslar)
    if year in _RAMAZAN_BAYRAMI:
        start, end = _RAMAZAN_BAYRAMI[year]
        events.append(SpecialDay(
            name="Ramazan Bayramı Kampanyaları",
            start=start - timedelta(days=14),
            end=end,
            category=EventCategory.NATIONAL_HOLIDAY,
            expected_discount_pct=-8,
            affected_categories=["Beyaz Eşya", "Ev Aleti", "Televizyon", "Telefon"],
        ))

    # Kurban Bayrami oncesi
    if year in _KURBAN_BAYRAMI:
        start, end = _KURBAN_BAYRAMI[year]
        events.append(SpecialDay(
            name="Kurban Bayramı Kampanyaları",
            start=start - timedelta(days=14),
            end=end,
            category=EventCategory.NATIONAL_HOLIDAY,
            expected_discount_pct=-8,
            affected_categories=["Beyaz Eşya", "Ev Aleti", "Televizyon"],
        ))

    return events


# -- Public API --

def get_all_events(year: int | None = None) -> list[SpecialDay]:
    """Belirtilen yil icin tum ozel gunleri doner."""
    if year is None:
        year = date.today().year
    events = _fixed_events(year) + _religious_events(year)
    return sorted(events, key=lambda e: e.start)


def get_upcoming_events(
    days_ahead: int = 21,
    category_slug: str | None = None,
) -> list[SpecialDay]:
    """
    Onumuzdeki N gun icindeki ozel gunleri doner.
    category_slug: urunun kategorisi (varsa sadece ilgili etkinlikler filtrelenir)
    """
    today = date.today()
    window_end = today + timedelta(days=days_ahead)

    # Bu yil + sonraki yil (yil sonu gecisi icin)
    events = get_all_events(today.year)
    if today.month >= 11:
        events += get_all_events(today.year + 1)

    upcoming = []
    for ev in events:
        # Etkinlik pencere icinde mi?
        if ev.end < today or ev.start > window_end:
            continue
        # Kategori filtresi
        if category_slug and ev.affected_categories:
            if category_slug not in ev.affected_categories:
                continue
        upcoming.append(ev)

    return upcoming


def compute_event_score(
    days_ahead: int = 21,
    category_slug: str | None = None,
) -> tuple[float, list[dict]]:
    """
    Ozel gun bazli BEKLE skoru hesapla.

    Returns: (score, event_details)
    - score: -1.0 (guclu BEKLE) to 0.0 (etki yok)
      Yaklasan buyuk indirim = negatif skor = BEKLE sinyali
    - event_details: etkinlik bilgileri (UI'da gostermek icin)
    """
    upcoming = get_upcoming_events(days_ahead, category_slug)

    if not upcoming:
        return 0.0, []

    today = date.today()
    total_impact = 0.0
    details = []

    for ev in upcoming:
        # Etkinlige kac gun var?
        days_to_event = max(0, (ev.start - today).days)

        # Yakinlik carpani: yaklastikca etkisi artar
        if days_to_event <= 3:
            proximity = 1.0
        elif days_to_event <= 7:
            proximity = 0.8
        elif days_to_event <= 14:
            proximity = 0.5
        else:
            proximity = 0.3

        # Indirim buyuklugu carpani (normalize: -20% → 1.0, -5% → 0.25)
        magnitude = min(1.0, abs(ev.expected_discount_pct) / 20.0)

        impact = proximity * magnitude
        total_impact += impact

        details.append({
            "name": ev.name,
            "start": ev.start.isoformat(),
            "end": ev.end.isoformat(),
            "days_to_event": days_to_event,
            "expected_discount_pct": ev.expected_discount_pct,
            "impact": round(impact, 3),
            "category": ev.category.value,
        })

    # Normalize: cap at -1.0
    score = -min(1.0, total_impact)

    return round(score, 4), details
