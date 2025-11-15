"""
Mercado Livre scraper for Brazilian e-commerce products.
Handles price extraction in Brazilian Real (R$) format.
"""
import logging
from typing import List, Optional
import time

from scrapers.base import BaseScraper, ScrapingResult

logger = logging.getLogger(__name__)

class MercadoLivreScraper(BaseScraper):
    """
    Scraper for Mercado Livre (mercadolivre.com.br)
    """

    def get_price_selectors(self) -> List[str]:
        """
        Get CSS selectors for extracting price from Mercado Livre HTML.

        Selectors are ordered by reliability/preference.
        Mercado Livre uses Andes Design System for their UI components.

        Returns:
           List of CSS selectors to try in order.
        """ 
        return [
            # Primary: Andes Design System money component
            'span.andes-money-amount__fraction',

            # Alternative: Old price tag format
            'span.price-tag-fraction',

            # Fallback: Price tag amount
            'span.price-tag-amount',

            # Meta tag fallback (structured data)
            'meta[property="og:price:amount"]',

            # JSON-LD structured data (last resort)
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
            # Fetch HTML content
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

            # Extract price
            price = self.extract_price_from_html(html, self.get_price_selectors())

            # Check availability
            is_available = self.is_product_available(html)

            #Extract currency (should be BRL for Mercado Livre)
            currency = self.extract_currency(html, default='BRL')

            response_time = int((time.time() - start_time) * 1000)

            #Log results
            if price:
                logger.info(
                    f"Successfully scraped Mercado Livre product: "
                    f"R$ {price:.2f} (available: {is_available}) in {response_time}ms"
                )
            else:
                logger.warning(
                    f"Price not found for Mercado Livre product: {url}"
                    f"(available: {is_available})"
                )
            
            return ScrapingResult(
                product_link_id=product_link_id,
                url=url,
                price=price,
                original_price=None,  # Not tracking original prices per requirements
                currency=currency,
                was_available=is_available,
                scrape_source='mercadolivre',
                response_time_ms=response_time,
                error=None if price else 'Price element not found'
            )
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Error scraping Mercado Livre product {url}: {str(e)}")
            
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

        Extends base class method with Mercado Livre-specific phrases.

        Args:
            html: HTML content to check

        Returns:
            True if product appears to be available
        """
        #Check base unavailability phrases first
        if not super().is_product_available(html):
            return False

        # Mercado Livre-specific unavailability indicators
        ml_unavailable_phrases = [
            'pausado temporariamente',
            'publicação pausada',
            'vendedor sem estoque',
            'estoque do vendedor esgotado',
            'anúncio pausado',
            'produto não disponível',
        ]

        html_lower = html.lower()
        return not any(phrase in html_lower for phrase in ml_unavailable_phrases)
