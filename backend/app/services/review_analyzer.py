"""
Keyword tabanlı yorum kalite filtresi.
Kargo/teslimat/satıcı gibi alakasız yorumları ayıklar — $0 maliyet (LLM yok).

İki katman:
1) Kesin irrelevant → sadece bu konulardansa filtrele
2) Ürün sinyali → bu keyword varsa, negatif olsa bile tut
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
    # Performans
    "performans", "hız", "işlemci", "ram", "depolama",
    # Tasarım & kalite
    "tasarım", "malzeme", "kalite", "dayanıklılık",
    # Kullanım
    "kullanım", "kurulum", "bağlantı", "wifi", "bluetooth",
]


@dataclass
class FilteredReview:
    """Tek bir yorum için filtre sonucu."""
    text: str
    is_relevant: bool
    reason: str  # "product_signal", "no_irrelevant", "only_irrelevant"


@dataclass
class AnalysisResult:
    """Bir ürünün yorum analiz sonucu."""
    product_title: str
    store: str
    reviews_fetched: int
    filtered_out: int
    relevant: int
    sample_relevant: list[str] = field(default_factory=list)
    sample_filtered: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    """Türkçe lowercase (basit)."""
    return text.lower().replace("İ", "i").replace("I", "ı")


def filter_review(text: str) -> FilteredReview:
    """
    Tek bir yorumu keyword filtreden geçirir.

    Karar mantığı:
    - Ürün sinyali varsa → TUT (kargo bahsetse bile)
    - Sadece irrelevant keyword → FİLTRELE
    - İkisi de yoksa → TUT (varsayılan olarak ürünle ilgili say)
    """
    normalized = _normalize(text)

    has_product_signal = any(kw in normalized for kw in PRODUCT_SIGNAL_KEYWORDS)
    has_irrelevant = any(kw in normalized for kw in IRRELEVANT_KEYWORDS)

    if has_product_signal:
        return FilteredReview(text=text, is_relevant=True, reason="product_signal")

    if has_irrelevant:
        return FilteredReview(text=text, is_relevant=False, reason="only_irrelevant")

    # İkisi de yok → varsayılan olarak ürünle ilgili say
    return FilteredReview(text=text, is_relevant=True, reason="no_irrelevant")


def analyze_reviews(
    reviews: list[str],
    product_title: str,
    store: str,
    sample_limit: int = 3,
) -> AnalysisResult:
    """
    Yorum listesini keyword filtreden geçirip özet döner.
    """
    relevant_texts: list[str] = []
    filtered_texts: list[str] = []

    for text in reviews:
        if not text or len(text.strip()) < 5:
            continue
        result = filter_review(text)
        if result.is_relevant:
            relevant_texts.append(text)
        else:
            filtered_texts.append(text)

    return AnalysisResult(
        product_title=product_title,
        store=store,
        reviews_fetched=len(reviews),
        filtered_out=len(filtered_texts),
        relevant=len(relevant_texts),
        sample_relevant=[t[:300] for t in relevant_texts[:sample_limit]],
        sample_filtered=[t[:300] for t in filtered_texts[:sample_limit]],
    )
