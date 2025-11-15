"""
Scraper factory for creating site-specific scrapers.
"""

from scrapers.base import BaseScraper
from scrapers.mercadolivre import MercadoLivreScraper

def get_scraper(store: str) -> BaseScraper:
    """
    Factory function to get the appropriate scraper for a given store.
    
    Args:
        store: Store identifier (e.g., 'mercadolivre', 'amazon_br')
    
    Returns:
        Instance of the appropriate scraper class
    
    Raises:
        ValueError: If store is not supported
    """
    scrapers = {
        'mercadolivre': MercadoLivreScraper,
        'mercado_livre': MercadoLivreScraper, # Alternative naming
    }

    scraper_class = scrapers.get(store.lower())

    if not scraper_class:
        raise ValueError(
            f"Unsupported store: {store}. "
            f"Supported stores: {', '.join(scrapers.keys())}"
        )
    
    return scraper_class()

__all__ = ['BaseScraper', 'MercadoLivreScraper', 'get_scraper']