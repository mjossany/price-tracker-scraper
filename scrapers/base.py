"""
Base scraper class providing common functionality for all site-specific scrapers.
"""
import re
import time
import logging
import gzip
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Set up logger
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
        self.ua = UserAgent()
    
    def _create_session(self) -> requests.Session:
        """
        Create and configure an HTTP session with appropriate headers.

        Returns:
            Configured requests.Session object
        """
        session = requests.Session()
        session.headers.update({
            'User-Agent': self._get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
        return session
    
    def _get_user_agent(self) -> str:
        """
        Get a random user agent string to rotate and avoid detection.

        Returns:
            User agent string
        """
        try:
            return self.ua.random
        except Exception:
            # Fallback to a default user agent if fake_useragent fails
            return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'

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
                # Rotate user agent on each attempt
                self.session.headers['User-Agent'] = self._get_user_agent()

                start_time = time.time()
                response = self.session.get(url, timeout=self.timeout)
                response_time = int((time.time() - start_time) * 1000)

                response.raise_for_status()

                logger.info(f"Successfully fetched {url} in {response_time}ms (attempt {attempt + 1})")

                content = response.content
                if content.startswith(b'\x1f\x8b'):
                    try:
                        logger.debug(f"Detected raw GZIP content for {url}, decompressing manually")
                        content = gzip.decompress(content)
                        encoding = response.encoding or response.apparent_encoding or 'utf-8' 
                        return content.decode(encoding, errors='replace')
                    except Exception as e:
                        logger.warning(f"Manual GZIP decompression failed: {e}")
                return response.text
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries})")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429: # Rate limited
                    wait_time = 2 ** attempt # Exponential backoff
                    logger.warning(f"Rate limited on {url}, waiting {wait_time}s")
                    time.sleep(wait_time)
                elif e.response.status_code in [404, 410]: # Product nof found or gone
                    logger.error(f"Product not found at {url}: {e.response.status_code}")
                    return None
                else:
                    logger.error(f"HTTP error fetching {url}: {e}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {url}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                time.sleep(1 * (attempt + 1)) # Progressive delay
            
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

    def extract_price_from_html(
        self,
        html: str,
        selectors: List[str]
    ) -> Optional[float]:
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
                    price_text = element.get_text().strip()
                    price = self.parse_price_text(price_text)
                    if price:
                        logger.debug(f"Extracted price ${price} using selector: {selector}")
                        return price
            except Exception as e:
                logger.debug(f"Failed to extract price with selector '{selector}': {e}")
                continue
        
        logger.warning("Could not extract price using any selector")
        return None
    
    def parse_price_text(self, price_text: str) -> Optional[float]:
        """
        Parse price from text, handling various formats including Brazilian Real.

        Examples:
            "$1,234.56" -> 1234.56 (US format)
            "€1.234,56" -> 1234.56 (European format)
            "R$ 1.234,56" -> 1234.56 (Brazilian format)
            "R$ 1 234,56" -> 1234.56 (Brazilian with space separator)
            "1234.56 USD" -> 1234.56
            "$1,234.56 - $2,000.00" -> 1234.56 (takes first price)
        
        Args:
            price_text: Raw price text from HTML

        Returns:
            Parsed price as float, or None if parsing failed
        """
        if not price_text:
            return None
        
        # Remove common text patterns (English and Portuguese)
        price_text = re.sub(
            r'(was|now|from|starting at|de|por|a partir de|por apenas)[\s:]*', 
            '', 
            price_text, 
            flags=re.IGNORECASE
        )

        # Extract first price-like pattern (handles ranges like "$10 - $20" or "R$ 10 - R$ 20")
        price_patterns = [
            r'R\$?\s*(\d+(?:[\s\.,]\d{3})*(?:[,\.]\d{2}))',  # Brazilian Real with R$
            r'\$\s*(\d+(?:[,\.]\d{3})*(?:[,\.]\d{2}))',      # Dollar sign
            r'€\s*(\d+(?:[,\.]\d{3})*(?:[,\.]\d{2}))',       # Euro sign
            r'(\d+(?:[\s\.,]\d{3})*(?:[,\.]\d{2}))',         # Any number format
        ]

        for pattern in price_patterns:
            match = re.search(pattern, price_text)
            if match:
                price_str = match.group(1)
                
                # Remove spaces (Brazilian format: R$ 1 234,56)
                price_str = price_str.replace(' ', '')
                    
                # Handle different decimal separators
                # Brazilian/European format: 1.234,56 -> 1234.56
                if ',' in price_str and '.' in price_str:
                    if price_str.rindex(',') > price_str.rindex('.'):
                        # Brazilian format: 1.234,56 or 1234,56
                        price_str = price_str.replace('.', '').replace(',', '.')
                    else:
                        # US format: 1,234.56
                        price_str = price_str.replace(',', '')
                # Only comma present
                elif ',' in price_str:
                    # Check if comma is decimal separator (only 2 digits after)
                    if re.match(r'\d+,\d{2}$', price_str):
                        # Brazilian/European: 1234,56
                        price_str = price_str.replace(',', '.')
                    else:
                        # Thousands separator: 1,234
                        price_str = price_str.replace(',', '')
                # Only dot present - could be thousands or decimal
                elif '.' in price_str:
                    # If only 2 digits after dot, it's decimal
                    if re.match(r'\d+\.\d{2}$', price_str):
                        pass  # Already in correct format
                    else:
                        # Thousands separator
                        price_str = price_str.replace('.', '')
                
                try:
                    price = float(price_str)
                    # Sanity check: reasonable price range (R$ 0.01 to R$ 10 million)
                    if 0.01 <= price <= 10000000:
                        return round(price, 2)
                except ValueError:
                    continue
        
        logger.debug(f"Could not parse price from text: {price_text}")
        return None
    
    def extract_currency(self, html: str, default: str = 'BRL') -> str:
        """
        Extract currency from HTML content.

        Args:
            html: HTML content to parse
            default: Default currency if not found (BRL for Brazilian sites)

        Returns:
            Currency code (e.g., 'BRL', 'USD', 'EUR', 'GBP')
        """
        # Check first 5KB for performance
        html_sample = html[:5000]
        
        # Check for explicit currency codes first
        currency_codes = ['BRL', 'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD']
        for code in currency_codes:
            if code in html_sample:
                return code
        
        # Check currency symbols (order matters - check R$ before $)
        currency_symbols = {
            'R$': 'BRL',
            'C$': 'CAD',
            'A$': 'AUD',
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            '¥': 'JPY',
        }

        for symbol, code in currency_symbols.items():
            if symbol in html_sample:
                return code
        
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
            # English phrases
            'out of stock',
            'currently unavailable',
            'not available',
            'sold out',
            'no longer available',
            'discontinued',
            # Portuguese phrases (Brazilian)
            'indisponível',
            'esgotado',
            'fora de estoque',
            'produto indisponível',
            'sem estoque',
            'temporariamente indisponível',
            'não disponível',
            'produto esgotado',
            'estoque esgotado',
            'fora de linha',
            'descontinuado',
        ]

        html_lower = html.lower()
        return not any(phrase in html_lower for phrase in unavailable_phrases)

    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()