from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ScrapedProduct:
    title: str
    url: str
    store: str
    current_price: Decimal
    original_price: Decimal | None = None
    currency: str = "TRY"
    image_url: str | None = None
    brand: str | None = None
    description: str | None = None
    store_product_id: str | None = None
    in_stock: bool = True
    category: str | None = None

    @property
    def discount_percent(self) -> int | None:
        if self.original_price and self.original_price > self.current_price:
            return round((1 - self.current_price / self.original_price) * 100)
        return None


class BaseScraper(ABC):
    """Tüm mağaza scraper'larının temel sınıfı."""

    @property
    @abstractmethod
    def store_name(self) -> str:
        ...

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Bu scraper verilen URL'yi işleyebilir mi?"""
        ...

    @abstractmethod
    async def scrape(self, url: str) -> ScrapedProduct:
        """URL'den ürün bilgisini çeker."""
        ...
