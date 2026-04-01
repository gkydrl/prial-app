"""
Prediction sonucu için insan-dostu Türkçe açıklama üretir.
Claude Haiku kullanır — doğal, ürüne özel paragraf.
Fallback: template-based metin (Claude fail olursa).

V2: Düz paragraf formatı (JSON değil). wait_days + expected_price bilgisi eklendi.
Maliyet: ~$7-17/ay (sadece fiyat değişen ürünler)
"""
import anthropic
from app.config import settings


def _template_reasoning(
    recommendation: str,
    current_price: float,
    l1y_lowest: float | None,
    l1y_highest: float | None,
    predicted_direction: str,
    confidence: float,
    reasoning: dict,
    wait_days: int | None = None,
    expected_price: float | None = None,
    event_details: list[dict] | None = None,
    shipping_info: list[dict] | None = None,
) -> str:
    """Claude başarısız olursa veri-bazlı template paragraf üret."""
    price_str = f"{current_price:,.0f} TL"
    parts: list[str] = []

    if recommendation == "AL":
        parts.append(f"Şu anki {price_str} fiyat uygun seviyede.")

        # Fiyat pozisyonu
        if l1y_lowest and l1y_highest and l1y_highest != l1y_lowest:
            range_pct = (current_price - l1y_lowest) / (l1y_highest - l1y_lowest) * 100
            if range_pct <= 15:
                parts.append(f"Son 1 yılın en düşüğüne çok yakın.")
            elif range_pct <= 40:
                parts.append(f"Son 1 yıl ortalamasının altında.")

        if predicted_direction == "UP":
            parts.append("Fiyatın yükselmesi bekleniyor, şimdi almak mantıklı.")

        # Mağaza karşılaştırması
        if shipping_info and len(shipping_info) >= 2:
            stores = [f"{s['store']}'da {s.get('text') or str(s.get('days', '?')) + ' iş günü kargo'}" for s in shipping_info[:2]]
            parts.append(f"{stores[0]}, {stores[1]} avantajı var.")
        elif shipping_info:
            s = shipping_info[0]
            parts.append(f"{s['store']}'da {s.get('text') or 'hızlı kargo'} avantajı var.")

    elif recommendation == "GUCLU_BEKLE":
        parts.append(f"Şu anki {price_str} fiyat yüksek seviyede.")

        if wait_days and expected_price:
            parts.append(f"Yaklaşık {wait_days} gün içinde {expected_price:,.0f} TL civarına düşmesini bekliyorum.")

        if event_details:
            event = event_details[0]
            parts.append(f"Yaklaşan {event.get('name', 'indirim dönemi')} fiyatı düşürebilir.")

        parts.append("Beklemenizi öneriyorum.")

    else:  # BEKLE
        if event_details:
            event = event_details[0]
            days_to = event.get("days_to_start", "?")
            discount = event.get("expected_discount_pct", 0)
            parts.append(f"{event.get('name', 'İndirim dönemi')}'e {days_to} gün kaldı.")
            if discount:
                parts.append(f"Bu kategoride geçen yıl ortalama %{discount:.0f} indirim olmuştu.")

        if wait_days and expected_price:
            parts.append(f"Şu anki {price_str} fiyattan yaklaşık {expected_price:,.0f} TL'ye düşmesini bekliyorum.")
            parts.append(f"{wait_days} gün beklemenizi öneriyorum.")
        else:
            trend_info = reasoning.get("trend", {})
            trend_30d = trend_info.get("trend_30d")
            if trend_30d is not None and trend_30d < -5:
                parts.append(f"Son 30 günde %{abs(trend_30d):.0f} düşüş yaşandı, düşüş devam edebilir.")
            parts.append("Daha iyi fiyatlar gelebilir, beklemenizi öneriyorum.")

    return " ".join(parts)


async def generate_reasoning_text(
    product_title: str,
    recommendation: str,
    confidence: float,
    current_price: float,
    reasoning: dict,
    l1y_lowest: float | None,
    l1y_highest: float | None,
    predicted_direction: str,
    review_summary: dict | None = None,
    shipping_info: list[dict] | None = None,
    daily_lowest_price: float | None = None,
    daily_lowest_store: str | None = None,
    wait_days: int | None = None,
    expected_price: float | None = None,
    event_details: list[dict] | None = None,
) -> str:
    """
    Claude Haiku ile doğal Türkçe paragraf üret.
    Düz metin döner (JSON değil). Fail olursa template fallback.
    """
    if not settings.anthropic_api_key:
        return _template_reasoning(
            recommendation, current_price, l1y_lowest, l1y_highest,
            predicted_direction, confidence, reasoning,
            wait_days, expected_price, event_details, shipping_info,
        )

    # Reasoning dict'ten faktörleri çıkar
    factors = []
    for key in ["percentile", "trend", "near_historical_low", "upcoming_event", "seasonal", "volatility", "drop_frequency"]:
        if key in reasoning and "note" in reasoning[key]:
            factors.append(reasoning[key]["note"])

    factors_text = "\n".join(f"- {f}" for f in factors) if factors else "Detay yok"

    # Build review section
    review_section = ""
    if review_summary:
        review_lines = []
        for store_key in ("trendyol", "hepsiburada"):
            store_data = review_summary.get(store_key)
            if store_data and isinstance(store_data, dict):
                rating = store_data.get("rating")
                count = store_data.get("count", 0)
                if rating:
                    review_lines.append(f"- {store_key.capitalize()}: {rating}/5 ({count} yorum)")
        if review_lines:
            review_section = "\n\nKullanıcı Yorumları:\n" + "\n".join(review_lines)

    # Build shipping section
    shipping_section = ""
    if shipping_info:
        ship_lines = []
        for info in shipping_info:
            store = info.get("store", "?")
            text = info.get("text") or f"{info.get('days', '?')} iş günü"
            ship_lines.append(f"- {store}: {text}")
        if ship_lines:
            shipping_section = "\n\nKargo Süreleri:\n" + "\n".join(ship_lines)

    # Build daily lowest section
    daily_section = ""
    if daily_lowest_price and daily_lowest_store:
        daily_section = f"\nBugünkü en düşük fiyat: {daily_lowest_price:,.0f} TL ({daily_lowest_store})"

    # Build wait info section
    wait_section = ""
    if wait_days is not None and expected_price is not None:
        wait_section = f"\nBekleme süresi: {wait_days} gün\nBeklenen fiyat: {expected_price:,.0f} TL"
    elif wait_days is None:
        wait_section = "\nBekleme süresi: Yok (hemen al)"

    # Event section
    event_section = ""
    if event_details:
        ev = event_details[0]
        event_section = f"\nYaklaşan etkinlik: {ev.get('name', '?')} ({ev.get('days_to_start', '?')} gün sonra, tahmini %{ev.get('expected_discount_pct', '?')} indirim)"

    prompt = (
        f"Sen Prial alışveriş asistanısın. Aşağıdaki ürün analizi için doğal bir Türkçe paragraf yaz.\n\n"
        f"Ürün: {product_title}\n"
        f"Tavsiye: {recommendation}\n"
        f"Güven: %{confidence * 100:.0f}\n"
        f"Mevcut fiyat: {current_price:,.0f} TL\n"
        f"Son 1 yıl en düşük: {f'{l1y_lowest:,.0f} TL' if l1y_lowest else 'Bilinmiyor'}\n"
        f"Son 1 yıl en yüksek: {f'{l1y_highest:,.0f} TL' if l1y_highest else 'Bilinmiyor'}\n"
        f"Fiyat yönü: {predicted_direction}"
        f"{wait_section}"
        f"{event_section}\n"
        f"Analiz faktörleri:\n{factors_text}"
        f"{review_section}"
        f"{shipping_section}"
        f"{daily_section}\n\n"
        f"Kurallar:\n"
        f"- Düz paragraf yaz, JSON veya madde işareti kullanma\n"
        f"- Max 3-4 cümle, sade ve samimi Türkçe\n"
        f"- Somut rakamlar kullan (fiyat, yüzde, gün sayısı)\n"
        f"- BEKLE ise: ne kadar beklemeli (gün), neden beklemeli, beklenen fiyat belirt\n"
        f"- AL ise: neden şimdi almalı belirt, 2+ mağaza varsa kargo ve taksit farkını belirt\n"
        f"- SADECE düz metin döndür, başka bir şey ekleme"
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        print(f"[reasoning_generator] Claude çağrısı: {product_title[:40]}...", flush=True)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text.strip()

        # Strip markdown code fences if present
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
            if result.endswith("```"):
                result = result[:-3].strip()

        # Strip quotes if wrapped
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]

        return result
    except Exception as e:
        import traceback
        print(f"[reasoning_generator] Claude hatası ({product_title[:30]}): {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        return _template_reasoning(
            recommendation, current_price, l1y_lowest, l1y_highest,
            predicted_direction, confidence, reasoning,
            wait_days, expected_price, event_details, shipping_info,
        )
