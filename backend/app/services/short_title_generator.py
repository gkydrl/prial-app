"""
Ürün adını push notification için kısaltır.
Claude Haiku kullanır — hızlı ve ucuz.
"""
import anthropic
from app.config import settings


async def generate_short_title(brand: str | None, title: str) -> str:
    """
    Ürün başlığından kısa bir ad üretir (max 40 karakter).
    Bellek (GB/TB), renk, malzeme gibi detayları atar, marka + model adını korur.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt = (
        f"Ürün adını kısalt. Sadece kısaltılmış adı yaz, açıklama veya başka hiçbir şey ekleme.\n\n"
        f"Kurallar:\n"
        f"- Maksimum 40 karakter\n"
        f"- GB, TB, RAM miktarı, renk, malzeme gibi teknik detayları at\n"
        f"- Marka adını ve model adını/numarasını koru\n"
        f"- Sadece Türkçe yaz\n\n"
        f"Marka: {brand or ''}\n"
        f"Ürün adı: {title}"
    )

    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text.strip()
        # Tırnak işareti veya fazladan boşluk temizle
        result = result.strip('"\'').strip()
        return result[:40]
    except Exception as e:
        print(f"[short_title] Üretim hatası: {e}")
        # Fallback: ilk 40 karakter, kelime sınırında kes
        if len(title) <= 40:
            return title
        truncated = title[:40]
        last_space = truncated.rfind(" ")
        return truncated[:last_space] if last_space > 20 else truncated
