from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class SearchResult:
    title: str
    url: str
    store: str
    price: Decimal
    image_url: str | None = None
    brand: str | None = None
    store_product_id: str | None = None
    in_stock: bool = True


class BaseSearcher(ABC):
    @property
    @abstractmethod
    def store_name(self) -> str: ...

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Verilen sorgu için store'da arama yapar, en iyi `limit` sonucu döner."""
        ...
