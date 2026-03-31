"""
Prediction sonucu için insan-dostu Türkçe açıklama üretir.
Claude Haiku kullanır — doğal, ürüne özel açıklamalar.
Fallback: template-based metin (Claude fail olursa).

Çıktı formatı: JSON string → {"summary": "...", "pros": ["...", ...], "cons": ["...", ...]}
Maliyet: ~$0.42/gün (500 ürün), ~$12.60/ay
"""
import json
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
) -> dict:
    """Claude başarısız olursa veri-bazlı template metin üret."""
    price_str = f"{current_price:,.0f} TL"
    pros: list[str] = []
    cons: list[str] = []

    # Fiyat pozisyonu
    if l1y_lowest and l1y_highest and l1y_highest != l1y_lowest:
        range_pct = (current_price - l1y_lowest) / (l1y_highest - l1y_lowest) * 100
        if range_pct <= 15:
            pros.append(f"Fiyat ({price_str}) son 1 yılın en düşüğüne çok yakın")
        elif range_pct <= 40:
            pros.append(f"Fiyat ({price_str}) son 1 yıl ortalamasının altında")
        elif range_pct >= 80:
            cons.append(f"Fiyat ({price_str}) son 1 yılın en yükseğine yakın")

    # Trend
    trend_info = reasoning.get("trend", {})
    trend_30d = trend_info.get("trend_30d")
    if trend_30d is not None:
        if trend_30d < -5:
            pros.append(f"Son 30 günde %{abs(trend_30d):.0f} düşüş yaşandı")
        elif trend_30d > 5:
            cons.append(f"Son 30 günde %{trend_30d:.0f} artış yaşandı")

    # Direction
    if predicted_direction == "DOWN":
        cons.append("Yakın zamanda daha fazla düşüş bekleniyor")
    elif predicted_direction == "UP":
        pros.append("Fiyatın yükselmesi bekleniyor, şimdi almak mantıklı")

    # Events
    events = reasoning.get("upcoming_event", {}).get("events", [])
    if events:
        cons.append(f"Yaklaşan {events[0]} indirimi fiyatı düşürebilir")
    else:
        pros.append("Yakın dönemde büyük indirim beklenmiyor")

    # Near low
    if reasoning.get("near_historical_low", {}).get("score", 0) >= 0.8:
        pros.append("Tarihi en düşük fiyata çok yakın")

    # Filler
    fillers_pro = ["Birden fazla mağazada karşılaştırma imkanı", "Stokta mevcut ve hemen teslim"]
    fillers_con = ["İndirim dönemlerinde daha ucuza bulunabilir", "Fiyat dalgalanmaları olası"]
    for f in fillers_pro:
        if len(pros) >= 3: break
        pros.append(f)
    for f in fillers_con:
        if len(cons) >= 3: break
        cons.append(f)

    conf_pct = int(confidence * 100)
    if recommendation == "AL":
        summary = f"Mevcut fiyat ({price_str}) uygun seviyede. Almak için iyi bir zaman."
    elif recommendation == "GUCLU_BEKLE":
        summary = f"Fiyat ({price_str}) yüksek. Beklemenizi öneriyoruz."
    else:
        summary = f"Daha iyi fiyatlar gelebilir. Beklemek avantajlı olabilir."

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
    Claude Haiku ile yapılandırılmış 3 pro + 3 con üret.
    JSON string döner. Fail olursa template fallback.
    """
    if not settings.anthropic_api_key:
        return json.dumps(
            _template_reasoning(recommendation, current_price, l1y_lowest, l1y_highest, predicted_direction, confidence, reasoning),
            ensure_ascii=False,
        )

    # Reasoning dict'ten faktörleri çıkar
    factors = []
    for key in ["percentile", "trend", "near_historical_low", "upcoming_event", "seasonal", "volatility", "drop_frequency"]:
        if key in reasoning and "note" in reasoning[key]:
            factors.append(reasoning[key]["note"])

    factors_text = "\n".join(f"- {f}" for f in factors) if factors else "Detay yok"

    prompt = (
        f"Sen Prial alışveriş asistanısın. Aşağıdaki ürün analizi için JSON formatında 3 olumlu ve 3 olumsuz madde yaz.\n\n"
        f"Ürün: {product_title}\n"
        f"Tavsiye: {recommendation}\n"
        f"Güven: %{confidence * 100:.0f}\n"
        f"Mevcut fiyat: {current_price:,.0f} TL\n"
        f"Son 1 yıl en düşük: {f'{l1y_lowest:,.0f} TL' if l1y_lowest else 'Bilinmiyor'}\n"
        f"Son 1 yıl en yüksek: {f'{l1y_highest:,.0f} TL' if l1y_highest else 'Bilinmiyor'}\n"
        f"Fiyat yönü: {predicted_direction}\n"
        f"Analiz faktörleri:\n{factors_text}\n\n"
        f"Kurallar:\n"
        f'- JSON döndür: {{"summary": "1 cümle", "pros": ["...", "...", "..."], "cons": ["...", "...", "..."]}}\n'
        f"- pros: 3 madde — bu ürünü şimdi almak için nedenler (fiyat avantajı, trend, stok vb.)\n"
        f"- cons: 3 madde — beklemek/almamak için nedenler (yüksek fiyat, indirim beklentisi vb.)\n"
        f"- summary: 1 kısa cümle genel değerlendirme\n"
        f"- Her madde max 12 kelime, sade Türkçe\n"
        f"- Fiyat yazarken TL kullan\n"
        f"- SADECE JSON döndür"
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text.strip()
        parsed = json.loads(result)

        output = {
            "summary": str(parsed.get("summary", "")),
            "pros": [str(p) for p in parsed.get("pros", [])][:3],
            "cons": [str(c) for c in parsed.get("cons", [])][:3],
        }
        while len(output["pros"]) < 3:
            output["pros"].append("Stokta mevcut")
        while len(output["cons"]) < 3:
            output["cons"].append("Fiyat dalgalanması olası")

        return json.dumps(output, ensure_ascii=False)
    except Exception as e:
        print(f"[reasoning_generator] Claude hatası ({product_title[:30]}): {e}", flush=True)
        return json.dumps(
            _template_reasoning(recommendation, current_price, l1y_lowest, l1y_highest, predicted_direction, confidence, reasoning),
            ensure_ascii=False,
        )
