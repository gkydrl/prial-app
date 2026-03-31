"""
Prediction sonucu için insan-dostu Türkçe açıklama üretir.
Claude Haiku kullanır — hızlı ve ucuz.
Fallback: template-based metin.
"""
import anthropic
from app.config import settings


def _template_reasoning(
    recommendation: str,
    current_price: float,
    l1y_lowest: float | None,
    l1y_highest: float | None,
    predicted_direction: str,
) -> str:
    """Claude başarısız olursa template-based metin üret."""
    price_str = f"{current_price:,.0f} TL"

    if recommendation == "AL":
        if l1y_lowest and current_price <= l1y_lowest * 1.05:
            return f"Şu anki fiyat ({price_str}) son 1 yılın en düşüğüne çok yakın. Almak için uygun bir zaman."
        if predicted_direction == "UP":
            return f"Fiyat yükseliş trendinde. Mevcut {price_str} fiyattan almak mantıklı görünüyor."
        return f"Mevcut fiyat ({price_str}) geçmiş verilere göre iyi bir seviyede. Almayı düşünebilirsiniz."

    if recommendation == "GUCLU_BEKLE":
        if l1y_lowest:
            target = f"{l1y_lowest:,.0f} TL"
            return f"Fiyat ({price_str}) tarihi düşüklerin çok üzerinde. Hedef: {target}. Beklemenizi öneriyoruz."
        return f"Mevcut fiyat ({price_str}) yüksek görünüyor. Daha iyi fiyatlar için beklemenizi öneriyoruz."

    # BEKLE
    if predicted_direction == "DOWN":
        return f"Fiyat ({price_str}) düşüş trendinde. Biraz daha beklemek avantajlı olabilir."
    if l1y_lowest:
        target = f"{l1y_lowest:,.0f} TL"
        return f"Mevcut fiyat ({price_str}), hedef fiyat {target} seviyesine gelebilir. Beklemek mantıklı."
    return f"Mevcut fiyat ({price_str}) için beklemenizi öneriyoruz. Daha uygun fiyatlar gelebilir."


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
    Claude Haiku ile 2-3 cümle Türkçe açıklama üret.
    Başarısız olursa template-based fallback kullan.
    """
    if not settings.anthropic_api_key:
        return _template_reasoning(
            recommendation, current_price, l1y_lowest, l1y_highest, predicted_direction
        )

    # Reasoning dict'ten önemli bilgileri çıkar
    factors = []
    for key in ["percentile", "trend", "near_historical_low", "upcoming_event", "seasonal"]:
        if key in reasoning and "note" in reasoning[key]:
            factors.append(reasoning[key]["note"])

    factors_text = "\n".join(f"- {f}" for f in factors) if factors else "Detay yok"

    prompt = (
        f"Sen bir alışveriş asistanısın. Aşağıdaki analiz sonucuna göre kullanıcıya 2-3 cümle Türkçe açıklama yaz.\n\n"
        f"Ürün: {product_title}\n"
        f"Tavsiye: {recommendation}\n"
        f"Güven: %{confidence * 100:.0f}\n"
        f"Mevcut fiyat: {current_price:,.0f} TL\n"
        f"Son 1 yıl en düşük: {f'{l1y_lowest:,.0f} TL' if l1y_lowest else 'Bilinmiyor'}\n"
        f"Son 1 yıl en yüksek: {f'{l1y_highest:,.0f} TL' if l1y_highest else 'Bilinmiyor'}\n"
        f"Fiyat yönü: {predicted_direction}\n"
        f"Analiz faktörleri:\n{factors_text}\n\n"
        f"Kurallar:\n"
        f"- Sadece 2-3 cümle yaz, kısa ve net ol\n"
        f"- Fiyat bilgilerini TL ile yaz\n"
        f"- AL ise neden şimdi alınması gerektiğini, BEKLE/GUCLU_BEKLE ise neden beklenmesi gerektiğini açıkla\n"
        f"- Teknik terimler kullanma, sade Türkçe yaz\n"
        f"- Sadece açıklamayı yaz, başka hiçbir şey ekleme"
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text.strip()
        return result[:500]
    except Exception as e:
        print(f"[reasoning_generator] Claude hatası: {e}")
        return _template_reasoning(
            recommendation, current_price, l1y_lowest, l1y_highest, predicted_direction
        )
