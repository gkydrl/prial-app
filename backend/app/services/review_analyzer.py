"""
Keyword tabanlı yorum kalite filtresi + sentiment analizi.
Kargo/teslimat/satıcı gibi alakasız yorumları ayıklar — $0 maliyet (LLM yok).

Üç katman:
1) Kesin irrelevant → sadece bu konulardansa filtrele
2) Ürün sinyali → bu keyword varsa, negatif olsa bile tut
3) Sentiment → pozitif/negatif/nötr ayrımı
"""
from dataclasses import dataclass, field


# ── Katman 1: Kesin irrelevant keyword'ler ──
# Yorum SADECE bu konulardan bahsediyorsa → filtrele
IRRELEVANT_KEYWORDS: list[str] = [
    # Kargo & teslimat
    "kargo", "teslimat", "kurye", "paketleme", "ambalaj", "kutu",
    "geç geldi", "geç kaldı", "günde geldi", "teslim",
    # Satıcı & mağaza
    "satıcı", "mağaza", "iade", "geri gönder", "iptal",
    # Evrak
    "fatura", "garanti belgesi", "hediye paketi",
]

# ── Katman 2: Ürün sinyal keyword'leri ──
# Bunlar varsa, negatif keyword olsa bile yorum tutulur
PRODUCT_SIGNAL_KEYWORDS: list[str] = [
    # Donanım
    "ekran", "pil", "batarya", "kamera", "ses", "hoparlör", "mikrofon",
    "lens", "sensör", "şarj", "adaptör", "kulaklık",
    # Performans
    "performans", "hız", "işlemci", "ram", "depolama", "hafıza",
    "kasma", "donma", "yavaş", "hızlı",
    # Tasarım & kalite
    "tasarım", "malzeme", "kalite", "dayanıklılık", "plastik", "metal",
    "ağırlık", "boyut", "ergonomi", "renk",
    # Kullanım
    "kullanım", "kurulum", "bağlantı", "wifi", "bluetooth",
    "arayüz", "menü", "güncelleme", "yazılım",
    # Genel ürün
    "fiyat", "para", "değer", "ediyor", "tavsiye", "öneririm",
    "memnun", "pişman", "hayal kırıklığı",
]

# ── Katman 3: Sentiment keyword'leri ──
POSITIVE_KEYWORDS: list[str] = [
    # Doğrudan olumlu
    "mükemmel", "harika", "süper", "muhteşem", "kusursuz", "enfes",
    "memnun", "memnunum", "tavsiye", "öneririm", "beğendim", "sevdim",
    "başarılı", "kaliteli", "sağlam", "güzel", "iyi", "güçlü",
    # Ürün özellikleri olumlu
    "dayanıklı", "uzun ömür", "hızlı", "sessiz", "konforlu",
    "pratik", "kolay", "şık", "net", "parlak", "canlı",
    "değer", "ediyor", "para", "hakk",  # fiyatına değer, parasının hakkını
    # Karşılaştırma olumlu
    "farkı", "üstün", "en iyi",
]

NEGATIVE_KEYWORDS: list[str] = [
    # Doğrudan olumsuz
    "kötü", "berbat", "rezalet", "felaket", "korkunç", "boktan",
    "pişman", "hayal kırıklığı", "memnun değil", "beğenmedim",
    "almayın", "almam", "tavsiye etmem", "önermem",
    # Arıza/sorun
    "bozuldu", "arıza", "sorun", "hata", "çalışmıyor",
    "kırıldı", "çatladı", "patladı", "şişti", "ısınıyor",
    "soyuldu", "döküldü", "koptu", "ayrıldı",
    # Performans olumsuz
    "yavaş", "kasıyor", "donuyor", "takılıyor",
    "zayıf", "yetersiz", "düşük",
    # Kalite olumsuz
    "ucuz", "plastik", "çürük", "ince", "dayanıksız",
]


@dataclass
class FilteredReview:
    """Tek bir yorum için filtre sonucu."""
    text: str
    is_relevant: bool
    reason: str  # "product_signal", "no_irrelevant", "only_irrelevant"
    sentiment: str  # "positive", "negative", "neutral"
    score: int  # Bilgi zenginliği skoru (0-10)


@dataclass
class AnalysisResult:
    """Bir ürünün yorum analiz sonucu."""
    product_title: str
    store: str
    reviews_fetched: int
    filtered_out: int
    relevant: int
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    sample_relevant: list[str] = field(default_factory=list)
    sample_filtered: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)  # En iyi pozitif yorumlar
    lowlights: list[str] = field(default_factory=list)   # En önemli negatif yorumlar


def _normalize(text: str) -> str:
    """Türkçe lowercase (basit)."""
    return text.lower().replace("İ", "i").replace("I", "ı")


def _count_matches(text: str, keywords: list[str]) -> int:
    """Metin içindeki keyword eşleşme sayısını döner."""
    return sum(1 for kw in keywords if kw in text)


def filter_review(text: str) -> FilteredReview:
    """
    Tek bir yorumu keyword filtreden geçirir + sentiment belirler.

    Karar mantığı:
    - Ürün sinyali varsa → TUT (kargo bahsetse bile)
    - Sadece irrelevant keyword → FİLTRELE
    - İkisi de yoksa → TUT (varsayılan olarak ürünle ilgili say)

    Sentiment:
    - Pozitif keyword > negatif → positive
    - Negatif keyword > pozitif → negative
    - Eşit veya ikisi de yok → neutral
    """
    normalized = _normalize(text)

    has_product_signal = any(kw in normalized for kw in PRODUCT_SIGNAL_KEYWORDS)
    has_irrelevant = any(kw in normalized for kw in IRRELEVANT_KEYWORDS)

    # Relevance
    if has_product_signal:
        is_relevant = True
        reason = "product_signal"
    elif has_irrelevant:
        is_relevant = False
        reason = "only_irrelevant"
    else:
        is_relevant = True
        reason = "no_irrelevant"

    # Sentiment
    pos_count = _count_matches(normalized, POSITIVE_KEYWORDS)
    neg_count = _count_matches(normalized, NEGATIVE_KEYWORDS)

    if pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    # Bilgi zenginliği skoru (daha çok product signal = daha bilgilendirici)
    signal_count = _count_matches(normalized, PRODUCT_SIGNAL_KEYWORDS)
    text_length_bonus = min(len(text) // 50, 3)  # Uzun yorumlar genelde daha bilgilendirici
    score = signal_count + text_length_bonus + (1 if sentiment != "neutral" else 0)

    return FilteredReview(
        text=text, is_relevant=is_relevant, reason=reason,
        sentiment=sentiment, score=score,
    )


def analyze_reviews(
    reviews: list[str],
    product_title: str,
    store: str,
    highlight_limit: int = 5,
    lowlight_limit: int = 3,
    sample_limit: int = 3,
) -> AnalysisResult:
    """
    Yorum listesini keyword filtreden geçirip sentiment analizi ile özet döner.
    Highlight: en bilgilendirici pozitif yorumlar (score'a göre sıralı)
    Lowlight: en bilgilendirici negatif yorumlar (score'a göre sıralı)
    """
    filtered_results: list[FilteredReview] = []
    filtered_texts: list[str] = []

    for text in reviews:
        if not text or len(text.strip()) < 10:
            continue
        result = filter_review(text)
        if result.is_relevant:
            filtered_results.append(result)
        else:
            filtered_texts.append(text)

    # Sentiment sayıları
    positive_count = sum(1 for r in filtered_results if r.sentiment == "positive")
    negative_count = sum(1 for r in filtered_results if r.sentiment == "negative")
    neutral_count = sum(1 for r in filtered_results if r.sentiment == "neutral")

    # Score'a göre sırala (en bilgilendirici önce)
    filtered_results.sort(key=lambda r: r.score, reverse=True)

    # Highlights: En iyi pozitif yorumlar
    highlights = [
        r.text[:300] for r in filtered_results
        if r.sentiment == "positive"
    ][:highlight_limit]

    # Lowlights: En önemli negatif yorumlar
    lowlights = [
        r.text[:300] for r in filtered_results
        if r.sentiment == "negative"
    ][:lowlight_limit]

    # Genel sample (geriye uyumluluk)
    sample_relevant = [r.text[:300] for r in filtered_results[:sample_limit]]

    return AnalysisResult(
        product_title=product_title,
        store=store,
        reviews_fetched=len(reviews),
        filtered_out=len(filtered_texts),
        relevant=len(filtered_results),
        positive_count=positive_count,
        negative_count=negative_count,
        neutral_count=neutral_count,
        sample_relevant=sample_relevant,
        sample_filtered=[t[:300] for t in filtered_texts[:sample_limit]],
        highlights=highlights,
        lowlights=lowlights,
    )
