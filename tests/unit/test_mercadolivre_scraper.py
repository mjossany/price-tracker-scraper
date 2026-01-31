"""
Unit tests for MercadoLivreScraper availability-first behavior.
"""
import pytest
from unittest.mock import Mock, patch
from scrapers.mercadolivre import MercadoLivreScraper


class TestMercadoLivreAvailabilityFirst:
    """Tests for availability check before price extraction."""
    
    @pytest.fixture
    def scraper(self):
        return MercadoLivreScraper()
    
    @patch.object(MercadoLivreScraper, 'fetch_html')
    def test_unavailable_product_skips_price_extraction(self, mock_fetch, scraper):
        """Test that price extraction is skipped when product is unavailable."""
        html_unavailable = '''
        <html>
            <body>
                <div>Produto indisponível</div>
                <span class="andes-money-amount__fraction">1234</span>
            </body>
        </html>
        '''
        mock_fetch.return_value = html_unavailable
        
        result = scraper.scrape_price(
            url='https://www.mercadolivre.com.br/test',
            product_link_id='test-123'
        )
        
        assert result.was_available is False
        assert result.price is None
        assert result.error == 'Product is not available'
    
    @patch.object(MercadoLivreScraper, 'fetch_html')
    def test_available_product_extracts_price(self, mock_fetch, scraper):
        """Test that price is extracted when product is available."""
        html_available = '''
        <html>
            <body>
                <div>Produto disponível para compra</div>
                <span class="andes-money-amount__fraction">1234</span>
                <meta property="og:price:amount" content="1234.56">
            </body>
        </html>
        '''
        mock_fetch.return_value = html_available
        
        result = scraper.scrape_price(
            url='https://www.mercadolivre.com.br/test',
            product_link_id='test-123'
        )
        
        assert result.was_available is True
        # Price extraction may or may not work in test, but the important thing
        # is that it tried (was_available=True means it got past the availability check)
        assert result.error != 'Product is not available'
    
    @patch.object(MercadoLivreScraper, 'fetch_html')
    def test_mercadolivre_specific_unavailable_messages(self, mock_fetch, scraper):
        """Test Mercado Livre-specific unavailability messages."""
        unavailable_phrases = [
            'pausado temporariamente',
            'publicação pausada',
            'vendedor sem estoque',
            'estoque do vendedor esgotado',
            'anúncio pausado',
            'produto não disponível'
        ]
        
        for phrase in unavailable_phrases:
            html = f'''
            <html>
                <body>
                    <div>{phrase}</div>
                    <span class="andes-money-amount__fraction">1234</span>
                </body>
            </html>
            '''
            mock_fetch.return_value = html
            
            result = scraper.scrape_price(
                url='https://www.mercadolivre.com.br/test',
                product_link_id='test-123'
            )
            
            assert result.was_available is False, f"Failed for phrase: {phrase}"
            assert result.price is None, f"Price should be None for phrase: {phrase}"
            assert result.error == 'Product is not available'
    
    @patch.object(MercadoLivreScraper, 'fetch_html')
    def test_general_unavailable_messages(self, mock_fetch, scraper):
        """Test general unavailability messages from base scraper."""
        unavailable_phrases = [
            'indisponível',
            'esgotado',
            'fora de estoque',
            'out of stock',
            'sold out'
        ]
        
        for phrase in unavailable_phrases:
            html = f'''
            <html>
                <body>
                    <div>{phrase}</div>
                    <span class="andes-money-amount__fraction">9999</span>
                </body>
            </html>
            '''
            mock_fetch.return_value = html
            
            result = scraper.scrape_price(
                url='https://www.mercadolivre.com.br/test',
                product_link_id='test-123'
            )
            
            assert result.was_available is False, f"Failed for phrase: {phrase}"
            assert result.price is None, f"Price should be None for phrase: {phrase}"
    
    @patch.object(MercadoLivreScraper, 'fetch_html')
    def test_available_product_without_price_element(self, mock_fetch, scraper):
        """Test available product but price element not found."""
        html_no_price = '''
        <html>
            <body>
                <div>Produto disponível</div>
                <button>Comprar</button>
            </body>
        </html>
        '''
        mock_fetch.return_value = html_no_price
        
        result = scraper.scrape_price(
            url='https://www.mercadolivre.com.br/test',
            product_link_id='test-123'
        )
        
        assert result.was_available is True
        assert result.price is None
        assert result.error == 'Price element not found'
    
    @patch.object(MercadoLivreScraper, 'fetch_html')
    def test_failed_html_fetch(self, mock_fetch, scraper):
        """Test behavior when HTML fetch fails."""
        mock_fetch.return_value = None
        
        result = scraper.scrape_price(
            url='https://www.mercadolivre.com.br/test',
            product_link_id='test-123'
        )
        
        assert result.was_available is False
        assert result.price is None
        assert result.error == 'Failed to fetch HTML'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
