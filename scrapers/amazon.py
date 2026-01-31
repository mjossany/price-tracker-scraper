"""
Amazon Brazil scraper for amazon.com.br products.
"""
import logging
import time
from typing import List

from scrapers.base import BaseScraper, ScrapingResult

logger = logging.getLogger(__name__)


class AmazonBrScraper(BaseScraper):
    """
    Scraper for Amazon Brazil (amazon.com.br).
    Amazon's HTML changes frequently; re-check selectors periodically.
    """

    def get_price_selectors(self) -> List[str]:
        """
        Get CSS selectors for extracting price from Amazon BR HTML.

        Returns:
            List of CSS selectors to try in order.
        """
        return [
            '.a-price .a-offscreen',
            '.a-price-whole',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '#priceblock_saleprice',
            'span.a-price[data-a-color="price"] .a-offscreen',
            'meta[property="og:price:amount"]',
            'script[type="application/ld+json"]',
        ]

    def scrape_price(self, url: str, product_link_id: str) -> ScrapingResult:
        """
        Scrape price and availability from an Amazon Brazil product page.

        Args:
            url: Amazon BR product URL
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
                    scrape_source='amazon_br',
                    response_time_ms=response_time,
                    error='Failed to fetch HTML'
                )

            is_available = self.is_product_available(html)

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
                    scrape_source='amazon_br',
                    response_time_ms=response_time,
                    error='Product is not available'
                )

            price = self.extract_price_from_html(html, self.get_price_selectors())
            currency = self.extract_currency(html, default='BRL')
            response_time = int((time.time() - start_time) * 1000)

            if price:
                logger.info(f"Scraped Amazon BR: R$ {price:.2f}, available: {is_available}")
            else:
                logger.warning(f"Price not found for {url}")

            return ScrapingResult(
                product_link_id=product_link_id,
                url=url,
                price=price,
                original_price=None,
                currency=currency,
                was_available=is_available,
                scrape_source='amazon_br',
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
                scrape_source='amazon_br',
                response_time_ms=response_time,
                error=str(e)
            )
