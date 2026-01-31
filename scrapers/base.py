"""
Base scraper class providing common functionality for all site-specific scrapers.
"""
import re
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """
    Data class representing the result of a scraping operation.
    """
    product_link_id: str
    url: str
    price: Optional[float]
    original_price: Optional[float]
    currency: str
    was_available: bool
    scrape_source: str
    response_time_ms: int
    error: Optional[str] = None
    discount_percentage: Optional[float] = None

    def __post_init__(self):
        """Calculate discount percentage if both prices are available"""
        if self.price and self.original_price and self.original_price > self.price:
            self.discount_percentage = round(
                ((self.original_price - self.price) / self.original_price) * 100, 2
            )


class BaseScraper(ABC):
    """
    Abstract base class for all e-commerce site scrapers.
    Provides common functionality for HTTP requests, HTML parsing, and price extraction.
    """

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize the base scraper.

        Args:
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create and configure an HTTP session with appropriate headers.

        Returns:
            Configured requests.Session object
        """
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        return session

    def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a URL with retry logic.

        Args:
            url: The URL to fetch

        Returns:
            HTML content as string, or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                response = self.session.get(url, timeout=self.timeout)
                response_time = int((time.time() - start_time) * 1000)

                response.raise_for_status()
                logger.info(f"Fetched {url} in {response_time}ms (attempt {attempt + 1})")
                return response.text

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries})")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    logger.warning(f"Rate limited on {url}, waiting 2s")
                    time.sleep(2)
                elif e.response.status_code in [404, 410]:  # Not found
                    logger.error(f"Product not found at {url}: {e.response.status_code}")
                    return None
                else:
                    logger.error(f"HTTP error fetching {url}: {e}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {url}: {e}")

            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                time.sleep(1)

        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    @abstractmethod
    def scrape_price(self, url: str, product_link_id: str) -> ScrapingResult:
        """
        Abstract method to scrape price from a specific e-commerce site.
        Must be implemented by each site-specific scraper.

        Args:
            url: Product URL to scrape
            product_link_id: Database ID of the product link

        Returns:
            ScrapingResult object with price data and metadata
        """
        pass

    @abstractmethod
    def get_price_selectors(self) -> List[str]:
        """
        Get CSS selectors for extracting price from HTML.
        Must be implemented by each site-specific scraper.

        Returns:
            List of CSS selectors to try in order
        """
        pass

    def extract_price_from_html(self, html: str, selectors: List[str]) -> Optional[float]:
        """
        Extract price from HTML using multiple CSS selectors.

        Args:
            html: HTML content to parse
            selectors: List of CSS selectors to try

        Returns:
            Extracted price as float, or None if not found
        """
        soup = BeautifulSoup(html, 'lxml')

        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    price_text = self._get_price_text(element)
                    price = self.parse_price_text(price_text)
                    if price:
                        logger.debug(f"Extracted price {price} using selector: {selector}")
                        return price
            except Exception as e:
                logger.debug(f"Failed to extract price with selector '{selector}': {e}")
                continue

        logger.warning("Could not extract price using any selector")
        return None

    def _get_price_text(self, element) -> str:
        """
        Extract text from a price element.
        Can be overridden by subclasses to handle complex price structures.
        """
        return element.get_text().strip()

    def parse_price_text(self, price_text: str, currency: str = 'BRL') -> Optional[float]:
        """
        Parse price from text, handling Brazilian Real (R$) and US Dollar ($) formats.

        Examples:
            BRL: "R$ 1.234,56" -> 1234.56 (dot thousands, comma decimal)
            USD: "$1,234.56" -> 1234.56 (comma thousands, dot decimal)

        Args:
            price_text: Raw price text from HTML
            currency: Currency code ('BRL' or 'USD') to determine parsing format

        Returns:
            Parsed price as float, or None if parsing failed
        """
        if not price_text:
            return None

        # Remove common text patterns
        price_text = re.sub(
            r'(de|por|a partir de|por apenas|from|starting at|now|was|price)[\s:]*',
            '',
            price_text,
            flags=re.IGNORECASE
        )

        # Detect currency from text
        detected_currency = self._detect_currency_from_text(price_text)
        if detected_currency:
            currency = detected_currency

        if currency == 'USD':
            return self._parse_usd_price(price_text)
        else:
            return self._parse_brl_price(price_text)

    def _detect_currency_from_text(self, price_text: str) -> Optional[str]:
        """
        Detect currency from price text based on currency symbols.

        Args:
            price_text: Raw price text

        Returns:
            'BRL', 'USD', or None if cannot determine
        """
        if re.search(r'R\$', price_text):
            return 'BRL'
        if re.search(r'US\$|USD|\$(?!R)', price_text):
            if not re.search(r'R\$', price_text):
                return 'USD'
        return None

    def _parse_brl_price(self, price_text: str) -> Optional[float]:
        """
        Parse Brazilian Real price format.
        Format: R$ 1.234,56 (dot for thousands, comma for decimals)

        Args:
            price_text: Raw price text

        Returns:
            Parsed price as float, or None if parsing failed
        """
        price_pattern = r'R\$?\s*(\d+(?:[\s\.]\d{3})*(?:,\d{2})?)'
        match = re.search(price_pattern, price_text)
        
        if match:
            price_str = match.group(1)
            price_str = price_str.replace(' ', '')

            # Handle Brazilian format: 1.234,56 -> 1234.56
            if ',' in price_str and '.' in price_str:
                price_str = price_str.replace('.', '').replace(',', '.')
            elif ',' in price_str:
                if re.match(r'\d+,\d{2}$', price_str):
                    price_str = price_str.replace(',', '.')
                else:
                    price_str = price_str.replace(',', '')
            elif '.' in price_str:
                if not re.match(r'\d+\.\d{2}$', price_str):
                    price_str = price_str.replace('.', '')

            try:
                price = float(price_str)
                if 0.01 <= price <= 10000000:
                    return round(price, 2)
            except ValueError:
                pass

        return None

    def _parse_usd_price(self, price_text: str) -> Optional[float]:
        """
        Parse US Dollar price format.
        Format: $1,234.56 (comma for thousands, dot for decimals)

        Args:
            price_text: Raw price text

        Returns:
            Parsed price as float, or None if parsing failed
        """
        price_pattern = r'(?:US)?\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
        match = re.search(price_pattern, price_text)
        
        if match:
            price_str = match.group(1).replace(',', '')
            
            try:
                price = float(price_str)
                if 0.01 <= price <= 10000000:
                    return round(price, 2)
            except ValueError:
                pass

        return None

    def extract_currency(self, html: str, default: str = 'BRL') -> str:
        """
        Extract currency from HTML content.

        Args:
            html: HTML content to parse
            default: Default currency if none detected

        Returns:
            Currency code ('BRL' or 'USD')
        """
        brl_count = len(re.findall(r'R\$', html))
        usd_count = len(re.findall(r'(?:US\$|USD\s*\d|\$\d)', html))

        if brl_count > usd_count:
            return 'BRL'
        elif usd_count > brl_count:
            return 'USD'

        return default

    def is_product_available(self, html: str) -> bool:
        """
        Check if product is available for purchase.
        Can be overridden by site-specific scrapers.

        Args:
            html: HTML content to check

        Returns:
            True if product appears to be available
        """
        unavailable_phrases = [
            # English
            'out of stock', 'currently unavailable', 'not available',
            'sold out', 'no longer available', 'discontinued',
            # Portuguese
            'indisponível', 'esgotado', 'fora de estoque',
            'produto indisponível', 'sem estoque',
            'temporariamente indisponível', 'não disponível',
            'produto esgotado', 'estoque esgotado',
            'fora de linha', 'descontinuado',
        ]

        html_lower = html.lower()
        return not any(phrase in html_lower for phrase in unavailable_phrases)

    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()
