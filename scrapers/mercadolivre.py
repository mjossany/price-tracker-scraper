"""
Mercado Livre scraper for Brazilian e-commerce products.
"""
import logging
import time
from typing import List

from scrapers.base import BaseScraper, ScrapingResult

logger = logging.getLogger(__name__)


class MercadoLivreScraper(BaseScraper):
    """
    Scraper for Mercado Livre (mercadolivre.com.br)
    """

    def get_price_selectors(self) -> List[str]:
        """
        Get CSS selectors for extracting price from Mercado Livre HTML.

        Returns:
           List of CSS selectors to try in order.
        """
        return [
            'span.andes-money-amount__fraction',
            'span.price-tag-fraction',
            'span.price-tag-amount',
            'meta[property="og:price:amount"]',
            'script[type="application/ld+json"]',
        ]

    def scrape_price(self, url: str, product_link_id: str) -> ScrapingResult:
        """
        Scrape price and availability from a Mercado Livre product page.

        Args:
            url: Mercado Livre product URL
            product_link_id: Database ID of the product link

        Returns:
            ScrapingResult with price data and metadata
        """
        start_time = time.time()

        try:
            html = self.fetch_html(url)

            if not html:
                response_time = int((time.time() - start_time) * 1000)
                return ScrapingResult(
                    product_link_id=product_link_id,
                    url=url,
                    price=None,
                    original_price=None,
                    currency='BRL',
                    was_available=False,
                    scrape_source='mercadolivre',
                    response_time_ms=response_time,
                    error='Failed to fetch HTML'
                )

            # Check availability first
            is_available = self.is_product_available(html)
            
            # If product is unavailable, return early without extracting price
            if not is_available:
                currency = self.extract_currency(html, default='BRL')
                response_time = int((time.time() - start_time) * 1000)
                logger.info(f"Product unavailable at {url}")
                return ScrapingResult(
                    product_link_id=product_link_id,
                    url=url,
                    price=None,
                    original_price=None,
                    currency=currency,
                    was_available=False,
                    scrape_source='mercadolivre',
                    response_time_ms=response_time,
                    error='Product is not available'
                )

            # Product is available, proceed with price extraction
            price = self.extract_price_from_html(html, self.get_price_selectors())
            currency = self.extract_currency(html, default='BRL')
            response_time = int((time.time() - start_time) * 1000)

            if price:
                logger.info(f"Scraped Mercado Livre: R$ {price:.2f}, available: {is_available}")
            else:
                logger.warning(f"Price not found for {url}")

            return ScrapingResult(
                product_link_id=product_link_id,
                url=url,
                price=price,
                original_price=None,
                currency=currency,
                was_available=is_available,
                scrape_source='mercadolivre',
                response_time_ms=response_time,
                error=None if price else 'Price element not found'
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Error scraping {url}: {e}")

            return ScrapingResult(
                product_link_id=product_link_id,
                url=url,
                price=None,
                original_price=None,
                currency='BRL',
                was_available=False,
                scrape_source='mercadolivre',
                response_time_ms=response_time,
                error=str(e)
            )

    def is_product_available(self, html: str) -> bool:
        """
        Check if product is available on Mercado Livre.

        Args:
            html: HTML content to check

        Returns:
            True if product appears to be available
        """
        if not super().is_product_available(html):
            return False

        # Mercado Livre-specific unavailability indicators
        ml_unavailable = [
            'pausado temporariamente',
            'publicação pausada',
            'vendedor sem estoque',
            'estoque do vendedor esgotado',
            'anúncio pausado',
            'produto não disponível',
        ]

        html_lower = html.lower()
        return not any(phrase in html_lower for phrase in ml_unavailable)

    def _get_price_text(self, element) -> str:
        """
        Extract price text, handling Mercado Livre's split fraction/cents structure.
        """
        text = element.get_text().strip()
        classes = element.get('class', [])

        cents_selector = None
        if 'andes-money-amount__fraction' in classes:
            cents_selector = '.andes-money-amount__cents'
        elif 'price-tag-fraction' in classes:
            cents_selector = '.price-tag-cents'

        if cents_selector:
            parent = element.parent
            if parent:
                cents_element = parent.select_one(cents_selector)
                if cents_element:
                    cents_text = cents_element.get_text().strip()
                    return f"{text},{cents_text}"

        return text
