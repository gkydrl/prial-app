"""
Prediction sonucu için insan-dostu Türkçe açıklama üretir.
Claude Haiku kullanır — hızlı ve ucuz.
Fallback: template-based metin.

Çıktı formatı: {"summary": "...", "pros": ["...", ...], "cons": ["...", ...]}
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
) -> dict:
    """Claude başarısız olursa template-based metin üret."""
    price_str = f"{current_price:,.0f} TL"
    pros = []
    cons = []

    if recommendation == "AL":
        if l1y_lowest and current_price <= l1y_lowest * 1.05:
            pros.append(f"Fiyat ({price_str}) son 1 yılın en düşüğüne çok yakın")
        if predicted_direction == "UP":
            pros.append("Fiyat yükseliş trendinde, erken almak avantajlı")
        else:
            pros.append(f"Mevcut fiyat ({price_str}) geçmiş verilere göre iyi seviyede")
        pros.append("Stokta mevcut ve hemen teslim")
        cons.append("Her zaman daha düşük fiyat ihtimali var")
        cons.append("İndirim dönemlerinde daha ucuza düşebilir")
        summary = f"Mevcut fiyat ({price_str}) almak için uygun görünüyor."
    elif recommendation == "GUCLU_BEKLE":
        if l1y_lowest:
            target = f"{l1y_lowest:,.0f} TL"
            cons.append(f"Fiyat tarihi düşük ({target}) seviyesinin çok üzerinde")
        cons.append("Yakın zamanda fiyat düşüşü bekleniyor")
        cons.append(f"Mevcut fiyat ({price_str}) yüksek görünüyor")
        pros.append("Bekleyerek önemli tasarruf yapılabilir")
        pros.append("Fiyat geçmişi düşüş potansiyeli gösteriyor")
        summary = f"Fiyat ({price_str}) yüksek. Beklemenizi öneriyoruz."
    else:  # BEKLE
        if predicted_direction == "DOWN":
            cons.append("Fiyat düşüş trendinde, biraz daha beklemek avantajlı")
        if l1y_lowest:
            target = f"{l1y_lowest:,.0f} TL"
            cons.append(f"Hedef fiyat: {target}")
        cons.append("Daha uygun fiyatlar gelebilir")
        pros.append("Acil ihtiyaç varsa mevcut fiyat makul")
        pros.append("Stok riski düşük")
        summary = f"Mevcut fiyat ({price_str}) için beklemenizi öneriyoruz."

    # 3'er tane olacak şekilde tamamla
    while len(pros) < 3:
        pros.append("Birden fazla mağazada mevcut")
    while len(cons) < 3:
        cons.append("Fiyat dalgalanmaları yaşanabilir")

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
    Claude Haiku ile yapılandırılmış açıklama üret.
    JSON string döner: {"summary": "...", "pros": [...], "cons": [...]}
    Başarısız olursa template-based fallback kullan.
    """
    if not settings.anthropic_api_key:
        return json.dumps(
            _template_reasoning(recommendation, current_price, l1y_lowest, l1y_highest, predicted_direction),
            ensure_ascii=False,
        )

    # Reasoning dict'ten önemli bilgileri çıkar
    factors = []
    for key in ["percentile", "trend", "near_historical_low", "upcoming_event", "seasonal", "volatility", "drop_frequency"]:
        if key in reasoning and "note" in reasoning[key]:
            factors.append(reasoning[key]["note"])

    factors_text = "\n".join(f"- {f}" for f in factors) if factors else "Detay yok"

    prompt = (
        f"Sen bir alışveriş asistanısın. Aşağıdaki analiz sonucuna göre JSON formatında yanıt ver.\n\n"
        f"Ürün: {product_title}\n"
        f"Tavsiye: {recommendation}\n"
        f"Güven: %{confidence * 100:.0f}\n"
        f"Mevcut fiyat: {current_price:,.0f} TL\n"
        f"Son 1 yıl en düşük: {f'{l1y_lowest:,.0f} TL' if l1y_lowest else 'Bilinmiyor'}\n"
        f"Son 1 yıl en yüksek: {f'{l1y_highest:,.0f} TL' if l1y_highest else 'Bilinmiyor'}\n"
        f"Fiyat yönü: {predicted_direction}\n"
        f"Analiz faktörleri:\n{factors_text}\n\n"
        f"Kurallar:\n"
        f'- JSON formatında yanıt ver: {{"summary": "...", "pros": ["...", "...", "..."], "cons": ["...", "...", "..."]}}\n'
        f"- summary: 1 cümle genel değerlendirme\n"
        f"- pros: Tam 3 madde — bu ürünü ŞİMDİ almak için olumlu nedenler\n"
        f"- cons: Tam 3 madde — bu ürünü almak için olumsuz nedenler veya bekleme sebepleri\n"
        f"- Her madde kısa olsun (max 15 kelime)\n"
        f"- Fiyat bilgilerini TL ile yaz\n"
        f"- Teknik terimler kullanma, sade Türkçe yaz\n"
        f"- SADECE JSON döndür, başka hiçbir şey yazma"
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text.strip()

        # JSON parse doğrulaması
        parsed = json.loads(result)
        # Yapıyı doğrula ve düzelt
        output = {
            "summary": str(parsed.get("summary", "")),
            "pros": [str(p) for p in parsed.get("pros", [])][:3],
            "cons": [str(c) for c in parsed.get("cons", [])][:3],
        }
        # 3'er tane olacak şekilde tamamla
        while len(output["pros"]) < 3:
            output["pros"].append("Stokta mevcut")
        while len(output["cons"]) < 3:
            output["cons"].append("Fiyat dalgalanması olası")

        return json.dumps(output, ensure_ascii=False)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[reasoning_generator] JSON parse hatası: {e}, raw: {result[:200] if 'result' in dir() else 'N/A'}")
        return json.dumps(
            _template_reasoning(recommendation, current_price, l1y_lowest, l1y_highest, predicted_direction),
            ensure_ascii=False,
        )
    except Exception as e:
        print(f"[reasoning_generator] Claude hatası: {e}")
        return json.dumps(
            _template_reasoning(recommendation, current_price, l1y_lowest, l1y_highest, predicted_direction),
            ensure_ascii=False,
        )
