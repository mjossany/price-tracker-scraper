"""
Unit tests for the BaseScraper class.
"""
import pytest
from scrapers.base import BaseScraper, ScrapingResult


class DummyScraper(BaseScraper):
    """Concrete implementation of BaseScraper for testing purposes."""
    
    def scrape_price(self, url: str, product_link_id: str) -> ScrapingResult:
        return ScrapingResult(
            product_link_id=product_link_id,
            url=url,
            price=None,
            original_price=None,
            currency='BRL',
            was_available=True,
            scrape_source='test',
            response_time_ms=0
        )
    
    def get_price_selectors(self):
        return ['.price']


class TestParseBRLPrice:
    """Tests for Brazilian Real (BRL) price parsing."""
    
    @pytest.fixture
    def scraper(self):
        return DummyScraper()
    
    def test_parse_brl_with_dot_thousands_and_comma_decimal(self, scraper):
        """Test: R$ 1.234,56 -> 1234.56"""
        result = scraper.parse_price_text("R$ 1.234,56")
        assert result == 1234.56
    
    def test_parse_brl_with_space_thousands_and_comma_decimal(self, scraper):
        """Test: R$ 1 234,56 -> 1234.56"""
        result = scraper.parse_price_text("R$ 1 234,56")
        assert result == 1234.56
    
    def test_parse_brl_without_thousands_separator(self, scraper):
        """Test: R$ 1234,56 -> 1234.56"""
        result = scraper.parse_price_text("R$ 1234,56")
        assert result == 1234.56
    
    def test_parse_brl_simple_price(self, scraper):
        """Test: R$ 99,90 -> 99.90"""
        result = scraper.parse_price_text("R$ 99,90")
        assert result == 99.90
    
    def test_parse_brl_price_range_returns_first(self, scraper):
        """Test: R$ 10 - R$ 20 -> 10.00 (returns first price)"""
        result = scraper.parse_price_text("R$ 10,00 - R$ 20,00")
        assert result == 10.00
    
    def test_parse_brl_with_portuguese_prefix(self, scraper):
        """Test: por R$ 1.234,56 -> 1234.56"""
        result = scraper.parse_price_text("por R$ 1.234,56")
        assert result == 1234.56
    
    def test_parse_brl_with_a_partir_de(self, scraper):
        """Test: a partir de R$ 99,99 -> 99.99"""
        result = scraper.parse_price_text("a partir de R$ 99,99")
        assert result == 99.99
    
    def test_parse_brl_large_number(self, scraper):
        """Test: R$ 10.000,00 -> 10000.00"""
        result = scraper.parse_price_text("R$ 10.000,00")
        assert result == 10000.00
    
    def test_parse_brl_very_large_number(self, scraper):
        """Test: R$ 1.234.567,89 -> 1234567.89"""
        result = scraper.parse_price_text("R$ 1.234.567,89")
        assert result == 1234567.89


class TestParseUSDPrice:
    """Tests for US Dollar (USD) price parsing."""
    
    @pytest.fixture
    def scraper(self):
        return DummyScraper()
    
    def test_parse_usd_with_comma_thousands_and_dot_decimal(self, scraper):
        """Test: $1,234.56 -> 1234.56"""
        result = scraper.parse_price_text("$1,234.56")
        assert result == 1234.56
    
    def test_parse_usd_without_thousands_separator(self, scraper):
        """Test: $1234.56 -> 1234.56"""
        result = scraper.parse_price_text("$1234.56")
        assert result == 1234.56
    
    def test_parse_usd_simple_price(self, scraper):
        """Test: $99.90 -> 99.90"""
        result = scraper.parse_price_text("$99.90")
        assert result == 99.90
    
    def test_parse_usd_with_us_prefix(self, scraper):
        """Test: US$ 1,234.56 -> 1234.56"""
        result = scraper.parse_price_text("US$ 1,234.56")
        assert result == 1234.56
    
    def test_parse_usd_with_usd_prefix(self, scraper):
        """Test: USD 1,234.56 -> handled as USD"""
        # This tests explicit currency parameter
        result = scraper.parse_price_text("$1,234.56", currency='USD')
        assert result == 1234.56
    
    def test_parse_usd_large_number(self, scraper):
        """Test: $10,000.00 -> 10000.00"""
        result = scraper.parse_price_text("$10,000.00")
        assert result == 10000.00
    
    def test_parse_usd_very_large_number(self, scraper):
        """Test: $1,234,567.89 -> 1234567.89"""
        result = scraper.parse_price_text("$1,234,567.89")
        assert result == 1234567.89
    
    def test_parse_usd_with_english_prefix(self, scraper):
        """Test: price $99.99 -> 99.99"""
        result = scraper.parse_price_text("price $99.99")
        assert result == 99.99


class TestCurrencyDetection:
    """Tests for automatic currency detection."""
    
    @pytest.fixture
    def scraper(self):
        return DummyScraper()
    
    def test_detect_brl_from_r_dollar(self, scraper):
        """Test detection of BRL from R$ symbol."""
        result = scraper._detect_currency_from_text("R$ 100,00")
        assert result == 'BRL'
    
    def test_detect_usd_from_dollar(self, scraper):
        """Test detection of USD from $ symbol."""
        result = scraper._detect_currency_from_text("$100.00")
        assert result == 'USD'
    
    def test_detect_usd_from_us_dollar(self, scraper):
        """Test detection of USD from US$ symbol."""
        result = scraper._detect_currency_from_text("US$ 100.00")
        assert result == 'USD'
    
    def test_detect_returns_none_for_no_currency(self, scraper):
        """Test that None is returned when no currency symbol found."""
        result = scraper._detect_currency_from_text("100.00")
        assert result is None


class TestExtractCurrency:
    """Tests for extracting currency from HTML content."""
    
    @pytest.fixture
    def scraper(self):
        return DummyScraper()
    
    def test_extract_brl_from_html(self, scraper):
        """Test extraction of BRL from HTML with R$ symbols."""
        html = '<div class="price">R$ 199,99</div><div>R$ 299,99</div>'
        result = scraper.extract_currency(html)
        assert result == 'BRL'
    
    def test_extract_usd_from_html(self, scraper):
        """Test extraction of USD from HTML with $ symbols."""
        html = '<div class="price">$199.99</div><div>$299.99</div>'
        result = scraper.extract_currency(html)
        assert result == 'USD'
    
    def test_extract_default_when_no_currency(self, scraper):
        """Test that default currency is returned when none found."""
        html = '<div class="price">199.99</div>'
        result = scraper.extract_currency(html, default='BRL')
        assert result == 'BRL'
    
    def test_extract_most_frequent_currency(self, scraper):
        """Test that the most frequent currency wins."""
        html = '<div>R$ 100,00</div><div>$50.00</div><div>R$ 200,00</div>'
        result = scraper.extract_currency(html)
        assert result == 'BRL'


class TestScrapingResult:
    """Tests for ScrapingResult dataclass."""
    
    def test_discount_calculation(self):
        """Test automatic discount percentage calculation."""
        result = ScrapingResult(
            product_link_id='123',
            url='https://example.com',
            price=80.00,
            original_price=100.00,
            currency='BRL',
            was_available=True,
            scrape_source='test',
            response_time_ms=100
        )
        assert result.discount_percentage == 20.0
    
    def test_no_discount_when_prices_equal(self):
        """Test no discount when price equals original price."""
        result = ScrapingResult(
            product_link_id='123',
            url='https://example.com',
            price=100.00,
            original_price=100.00,
            currency='BRL',
            was_available=True,
            scrape_source='test',
            response_time_ms=100
        )
        assert result.discount_percentage is None
    
    def test_no_discount_when_original_price_missing(self):
        """Test no discount when original price is None."""
        result = ScrapingResult(
            product_link_id='123',
            url='https://example.com',
            price=80.00,
            original_price=None,
            currency='BRL',
            was_available=True,
            scrape_source='test',
            response_time_ms=100
        )
        assert result.discount_percentage is None


class TestProductAvailability:
    """Tests for product availability checking."""
    
    @pytest.fixture
    def scraper(self):
        return DummyScraper()
    
    def test_product_available(self, scraper):
        """Test that product is available when no unavailable phrases found."""
        html = '<div>Produto disponível</div><button>Comprar</button>'
        assert scraper.is_product_available(html) is True
    
    def test_product_unavailable_portuguese(self, scraper):
        """Test detection of unavailable product in Portuguese."""
        html = '<div>Produto indisponível</div>'
        assert scraper.is_product_available(html) is False
    
    def test_product_out_of_stock_portuguese(self, scraper):
        """Test detection of out of stock in Portuguese."""
        html = '<div>Produto esgotado</div>'
        assert scraper.is_product_available(html) is False
    
    def test_product_out_of_stock_english(self, scraper):
        """Test detection of out of stock in English."""
        html = '<div>Out of stock</div>'
        assert scraper.is_product_available(html) is False
    
    def test_product_sold_out_english(self, scraper):
        """Test detection of sold out in English."""
        html = '<div>Sold out</div>'
        assert scraper.is_product_available(html) is False
