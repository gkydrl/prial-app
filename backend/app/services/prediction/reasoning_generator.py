"""
Prediction sonucu için insan-dostu Türkçe açıklama üretir.
Template-based: hızlı, ücretsiz, ürüne özel fiyat verileriyle zenginleştirilmiş.

Çıktı formatı: JSON string → {"summary": "...", "pros": ["...", ...], "cons": ["...", ...]}
"""
import json


def _build_reasoning(
    recommendation: str,
    current_price: float,
    l1y_lowest: float | None,
    l1y_highest: float | None,
    predicted_direction: str,
    confidence: float,
    reasoning: dict,
) -> dict:
    """Analiz verilerine dayalı yapılandırılmış reasoning üret."""
    price_str = f"{current_price:,.0f} TL"
    pros: list[str] = []
    cons: list[str] = []

    # --- Fiyat pozisyonu ---
    if l1y_lowest and l1y_highest:
        range_pct = ((current_price - l1y_lowest) / (l1y_highest - l1y_lowest) * 100) if l1y_highest != l1y_lowest else 50
        if range_pct <= 15:
            pros.append(f"Fiyat ({price_str}) son 1 yılın en düşüğüne çok yakın")
        elif range_pct <= 40:
            pros.append(f"Fiyat ({price_str}) son 1 yıl ortalamasının altında")
        elif range_pct >= 80:
            cons.append(f"Fiyat ({price_str}) son 1 yılın en yükseğine yakın")
        else:
            cons.append(f"Fiyat ({price_str}) orta seviyede, daha düşebilir")

    # --- Trend ---
    trend_info = reasoning.get("trend", {})
    trend_30d = trend_info.get("trend_30d")
    trend_7d = trend_info.get("trend_7d")
    if trend_30d is not None:
        if trend_30d < -5:
            pros.append(f"Son 30 günde %{abs(trend_30d):.0f} düşüş yaşandı")
        elif trend_30d > 5:
            cons.append(f"Son 30 günde %{trend_30d:.0f} artış yaşandı")
    if trend_7d is not None:
        if trend_7d < -3:
            pros.append("Son 1 haftada fiyat düşüşü devam ediyor")
        elif trend_7d > 3:
            cons.append("Son 1 haftada fiyat yükselişte")

    # --- Predicted direction ---
    if predicted_direction == "DOWN":
        cons.append("AI modeli yakın zamanda daha fazla düşüş bekliyor")
    elif predicted_direction == "UP":
        pros.append("Fiyatın yükselmesi bekleniyor, şimdi almak mantıklı")
    else:
        pros.append("Fiyat stabil seyrediyor")

    # --- Near historical low ---
    near_low = reasoning.get("near_historical_low", {})
    if near_low.get("score", 0) >= 0.8:
        pros.append("Tarihi en düşük fiyata çok yakın — nadir fırsat")
    elif near_low.get("score", 0) == 0:
        cons.append("Tarihi düşük fiyattan uzak")

    # --- Upcoming event ---
    event_info = reasoning.get("upcoming_event", {})
    events = event_info.get("events", [])
    if events:
        cons.append(f"Yaklaşan {events[0]} indirimi fiyatı düşürebilir")
    else:
        if event_info.get("score", 0.5) >= 0.5:
            pros.append("3 hafta içinde büyük indirim dönemi beklenmiyor")

    # --- Volatility ---
    vol_info = reasoning.get("volatility", {})
    vol_score = vol_info.get("score", 0.5)
    if vol_score >= 0.7:
        pros.append("Fiyat dalgalanması düşük, stabil seyir")
    elif vol_score <= 0.3:
        cons.append("Fiyat sık dalgalanıyor, düşüş fırsatı olabilir")

    # --- Drop frequency ---
    drop_info = reasoning.get("drop_frequency", {})
    drop_val = drop_info.get("value")
    if drop_val is not None:
        if drop_val >= 8:
            cons.append(f"Yılda {drop_val} kez ciddi fiyat düşüşü yaşanıyor")
        elif drop_val <= 2:
            pros.append("Fiyat nadiren düşüyor, mevcut fiyat iyi bir fırsat")

    # --- l1y_lowest hedef ---
    if l1y_lowest and current_price > l1y_lowest * 1.15:
        target = f"{l1y_lowest:,.0f} TL"
        cons.append(f"Hedef fiyat: {target} (son 1 yıl en düşük)")

    # --- Summary ---
    conf_pct = int(confidence * 100)
    if recommendation == "AL":
        summary = f"AI analizi %{conf_pct} güvenle almayı öneriyor. Mevcut fiyat ({price_str}) uygun seviyede."
    elif recommendation == "GUCLU_BEKLE":
        summary = f"AI analizi %{conf_pct} güvenle beklemeyi öneriyor. Fiyat ({price_str}) yüksek görünüyor."
    else:
        summary = f"AI analizi %{conf_pct} güvenle beklemeyi öneriyor. Daha iyi fiyatlar gelebilir."

    # Ensure exactly 3 pros and 3 cons — deduplicate first
    pros = list(dict.fromkeys(pros))  # remove duplicates preserving order
    cons = list(dict.fromkeys(cons))

    # Fill to 3 with generic but relevant items
    generic_pros = [
        "Birden fazla mağazada karşılaştırma imkanı",
        "Stokta mevcut, hemen teslim edilebilir",
        "Fiyat takibi ile uygun zamanı yakalayabilirsiniz",
    ]
    generic_cons = [
        "İndirim dönemlerinde daha ucuza bulunabilir",
        "Fiyat dalgalanmaları olası",
        "Alternatif ürünler daha uygun fiyatlı olabilir",
    ]
    for gp in generic_pros:
        if len(pros) >= 3:
            break
        if gp not in pros:
            pros.append(gp)
    for gc in generic_cons:
        if len(cons) >= 3:
            break
        if gc not in cons:
            cons.append(gc)

    return {"summary": summary, "pros": pros[:3], "cons": cons[:3]}


async def generate_reasoning_text(
    product_title: str,
    recommendation: str,
    confidence: float,
    current_price: float,
    reasoning: dict,
    l1y_lowest: float | None,
    l1y_highest: float | None,
    predicted_direction: str,
) -> str:
    """
    Ürüne özel yapılandırılmış reasoning JSON string döner.
    Template-based: hızlı, ücretsiz, ürün verilerine dayalı.
    """
    result = _build_reasoning(
        recommendation=recommendation,
        current_price=current_price,
        l1y_lowest=l1y_lowest,
        l1y_highest=l1y_highest,
        predicted_direction=predicted_direction,
        confidence=confidence,
        reasoning=reasoning,
    )
    return json.dumps(result, ensure_ascii=False)
