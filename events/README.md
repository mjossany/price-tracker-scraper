# Test Events

Event files for testing Lambda scrapers locally.

## Available Events

### `test_mercadolivre.json`
Test event for Mercado Livre scraper with a real product URL.

### `test_amazon.json`
Test event for Amazon BR scraper with a real product URL (iPhone 15).

**Note**: Amazon.com.br actively blocks automated requests with CAPTCHA challenges. The scraper will work correctly when:
- Running from AWS Lambda with rotating IPs
- Using more sophisticated bot detection bypass techniques
- Accessing less frequently monitored product pages

For local testing, the scraper correctly handles the CAPTCHA response (treats it as unavailable), but cannot extract price data. The selectors have been verified against real Amazon BR HTML and should work when bot detection is not triggered.

### `scheduled_event.json`
Scheduled event format for production Lambda runs.

## Usage

Run locally with SAM CLI:
```bash
sam local invoke PriceTrackerScraperFunction --event events/test_mercadolivre.json
```

Or with Python directly (if dependencies installed):
```bash
python -c "
import json
from lambda_function import lambda_handler
with open('events/test_amazon.json') as f:
    event = json.load(f)
class Ctx:
    aws_request_id = 'test-123'
result = lambda_handler(event, Ctx())
print(result)
"
```
