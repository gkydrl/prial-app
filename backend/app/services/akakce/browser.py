"""
Playwright browser yonetimi — Akakce scraping icin singleton async context manager.
Stealth ayarlari, resource blocking, rate limiting.
"""
from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.config import settings

# Singleton state
_browser: Browser | None = None
_context: BrowserContext | None = None
_lock = asyncio.Lock()

# Rate limiting: max 1 concurrent page operation
_semaphore = asyncio.Semaphore(1)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]


async def _ensure_browser() -> BrowserContext:
    """Singleton browser + context baslat. Zaten varsa mevcut context'i don."""
    global _browser, _context

    async with _lock:
        if _browser is None or not _browser.is_connected():
            pw = await async_playwright().start()
            _browser = await pw.chromium.launch(
                headless=settings.playwright_headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            _context = await _browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                viewport={"width": 1366, "height": 768},
                extra_http_headers={
                    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )
            # Block unnecessary resources
            await _context.route(
                "**/*.{png,jpg,jpeg,gif,svg,webp,woff,woff2,ttf,eot,css}",
                lambda route: route.abort(),
            )

        return _context


async def close_browser() -> None:
    """Browser'i kapat (shutdown'da kullanilir)."""
    global _browser, _context
    async with _lock:
        if _context:
            await _context.close()
            _context = None
        if _browser:
            await _browser.close()
            _browser = None


@asynccontextmanager
async def get_page() -> AsyncGenerator[Page, None]:
    """
    Rate-limited page context manager.
    Kullanim:
        async with get_page() as page:
            await page.goto(url)
    """
    async with _semaphore:
        ctx = await _ensure_browser()
        page = await ctx.new_page()
        try:
            yield page
        finally:
            await page.close()


async def random_delay(min_sec: float = 3.0, max_sec: float = 6.0) -> None:
    """Rate limiting icin rastgele bekleme."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def detect_cloudflare(page: Page) -> bool:
    """Cloudflare challenge sayfasinda olup olmadigini kontrol et."""
    title = await page.title()
    cf_titles = ["just a moment", "attention required", "cloudflare"]
    return any(t in title.lower() for t in cf_titles)


async def wait_for_cloudflare(page: Page, timeout: int = 30000) -> bool:
    """
    Cloudflare challenge varsa bekle.
    Returns True if page loaded successfully after challenge.
    """
    if not await detect_cloudflare(page):
        return True

    print("[akakce/browser] Cloudflare challenge algilandi, bekleniyor...", flush=True)
    try:
        await page.wait_for_function(
            """() => !document.title.toLowerCase().includes('just a moment')""",
            timeout=timeout,
        )
        await asyncio.sleep(2)  # Extra wait after challenge
        return True
    except Exception:
        print("[akakce/browser] Cloudflare challenge asilAmadi", flush=True)
        return False
