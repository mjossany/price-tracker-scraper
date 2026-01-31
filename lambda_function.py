"""
AWS Lambda handler for price scraping.
"""
import json
import logging
from typing import Dict, Any

from utils.logger import get_logger
from scrapers import get_scraper

logger = get_logger("price-tracker-scraper")


def lambda_handler(event, context):
    """
    Lambda handler for price scraping.

    Event format for testing:
    {
        "action": "test_scraper",
        "store": "mercadolivre",
        "url": "https://www.mercadolivre.com.br/...",
        "product_link_id": "test-123"
    }
    """
    logger.info(f"Price tracker scraper started - Request ID: {context.aws_request_id}")
    logger.debug(f"Event: {json.dumps(event)}")

    try:
        # Check if this is a test scraper event
        if event.get('action') == 'test_scraper':
            return handle_test_scraper(event)

        # Default response for scheduled events
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Price tracker scraper executed successfully',
                'request_id': context.aws_request_id
            })
        }
    except Exception as e:
        logger.error(f"Error in lambda handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_test_scraper(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle test scraper event.

    Args:
        event: Lambda event with scraper test parameters

    Returns:
        Response with scraping results
    """
    store = event.get('store', 'mercadolivre')
    url = event.get('url')
    product_link_id = event.get('product_link_id', 'test-123')

    if not url:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required parameter: url'})
        }

    logger.info(f"Testing {store} scraper with URL: {url}")

    try:
        scraper = get_scraper(store)
        result = scraper.scrape_price(url=url, product_link_id=product_link_id)
        scraper.close()

        # Convert result to dict for JSON serialization
        result_dict = {
            'product_link_id': result.product_link_id,
            'url': result.url,
            'price': result.price,
            'original_price': result.original_price,
            'currency': result.currency,
            'was_available': result.was_available,
            'scrape_source': result.scrape_source,
            'response_time_ms': result.response_time_ms,
            'error': result.error,
            'discount_percentage': result.discount_percentage,
        }

        logger.info(f"Scraping completed: {result_dict}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Scraping completed successfully',
                'result': result_dict
            })
        }
    except ValueError as e:
        logger.error(f"Invalid store: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
