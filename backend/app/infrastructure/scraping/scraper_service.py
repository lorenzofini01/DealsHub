"""
Infrastructure - Scraper Service (ottimizzato con parallelismo)
"""
from typing import Optional
import httpx
from bs4 import BeautifulSoup
import re
from decimal import Decimal
from urllib.parse import urlparse
from ...domain import IScraperService
import logging

logger = logging.getLogger(__name__)


class HTTPXScraperService(IScraperService):
    """
    Scraper service usando HTTPX async.
    Include retry logic e timeout ottimizzati.
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
    }

    COOKIES = {
        "i18n-prefs": "EUR",
        "lc-acbit": "it_IT",
    }

    VALID_SHOPS = ["amazon", "amzn", "ebay"]
    BAD_PATHS = ["/deals", "/music/", "/prime", "/gp/video", "/cart", "/sign-in"]

    async def scrape_product(self, url: str) -> dict:
        """
        Scrape metadata da URL.
        Returns dict con title, price, original_price, image_url, is_available
        """
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url, headers=self.HEADERS, cookies=self.COOKIES)
                final_url = str(response.url)

                # Valida shop
                if not self._is_valid_shop(final_url):
                    logger.warning(f"Invalid shop: {final_url}")
                    return {"is_available": False}

                if response.status_code >= 400:
                    return {"is_available": False}

                html = response.text
                soup = BeautifulSoup(html, "html.parser")

                # Check disponibilità
                is_available = self._check_availability(soup, html, final_url)
                if not is_available:
                    return {"is_available": False}

                # Extract metadata
                result = {
                    "is_available": True,
                    "title": self._extract_title(soup),
                    "image_url": self._extract_image(soup, html),
                    "price": self._extract_price(soup, html),
                    "original_price": self._extract_original_price(soup),
                }

                logger.info(f"Scraped: {result['title'][:50] if result['title'] else 'N/A'}")
                return result

        except Exception as e:
            logger.error(f"Scraping error for {url}: {e}")
            return {"is_available": True}  # Assume disponibile se errore (retry later)

    def _is_valid_shop(self, url: str) -> bool:
        """Verifica se l'URL è di uno shop valido"""
        domain = urlparse(url).netloc.lower()
        if not any(shop in domain for shop in self.VALID_SHOPS):
            return False

        if any(bad in url for bad in self.BAD_PATHS):
            return False

        return True

    def _check_availability(self, soup: BeautifulSoup, html: str, url: str) -> bool:
        """Verifica se prodotto disponibile"""
        if "amazon" in url:
            if soup.select_one("#outOfStock"):
                return False
            if "attualmente non disponibile" in html.lower():
                return False
        return True

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Estrae titolo prodotto"""
        # Selettori Amazon
        for sel in ["#productTitle", "#title", ".product-title-word-break"]:
            elem = soup.select_one(sel)
            if elem:
                title = elem.get_text(strip=True)
                return self._clean_title(title)

        # OpenGraph fallback
        og = soup.select_one('meta[property="og:title"]')
        if og and og.get("content"):
            return self._clean_title(og.get("content"))

        # Title tag fallback
        if soup.title:
            return self._clean_title(soup.title.string)

        return None

    def _clean_title(self, title: str) -> Optional[str]:
        """Pulisce titolo da junk"""
        if not title:
            return None

        title = title.strip()
        # Rimuovi suffissi comuni
        for suffix in [" : Amazon.it", "Amazon.it: ", "Amazon.it", " | eBay"]:
            title = title.replace(suffix, "")

        if len(title) < 5 or "Captcha" in title:
            return None

        return title[:500]  # Limit length

    def _extract_image(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Estrae URL immagine prodotto"""
        # Selettori diretti
        img = soup.select_one("#landingImage, #imgBlkFront, #main-image")
        if img:
            return img.get("src") or img.get("data-old-hires")

        # OpenGraph
        og = soup.select_one('meta[property="og:image"]')
        if og and og.get("content"):
            return og.get("content")

        # Regex su JSON inline (per fashion/alimentari)
        patterns = [
            r'"hiRes":"(https://[^"]+?\.jpg)"',
            r'"large":"(https://[^"]+?\.jpg)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1).replace(r"\/", "/")

        return None

    def _extract_price(self, soup: BeautifulSoup, html: str) -> Optional[Decimal]:
        """Estrae prezzo corrente"""
        # Selettori Amazon
        selectors = [
            "#corePrice_desktop .a-price-whole",
            ".apexPriceToPay .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
        ]

        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                price = self._parse_price(elem.get_text(strip=True))
                if price:
                    return price

        # Regex fallback
        match = re.search(r'"priceToPay":{"amount":(\d+\.?\d*)', html)
        if match:
            return Decimal(match.group(1))

        return None

    def _extract_original_price(self, soup: BeautifulSoup) -> Optional[Decimal]:
        """Estrae prezzo originale (barrato)"""
        selectors = [
            ".a-text-price .a-offscreen",
            "span[data-a-strike='true'] .a-offscreen",
            ".basisPrice .a-offscreen",
        ]

        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                price = self._parse_price(elem.get_text(strip=True))
                if price:
                    return price

        return None

    def _parse_price(self, text: str) -> Optional[Decimal]:
        """Parse stringa prezzo -> Decimal"""
        if not text:
            return None

        try:
            clean = text.replace("€", "").replace("EUR", "").strip()

            # Handle formats: 1.234,56 or 1,234.56
            if "," in clean and "." in clean:
                if clean.rindex(",") > clean.rindex("."):
                    clean = clean.replace(".", "").replace(",", ".")
                else:
                    clean = clean.replace(",", "")
            elif "," in clean:
                clean = clean.replace(",", ".")

            return Decimal(clean)
        except Exception as e:
            logger.warning(f"Failed to parse price '{text}': {e}")
            return None
