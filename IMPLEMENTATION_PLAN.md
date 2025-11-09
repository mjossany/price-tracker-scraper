# Price Tracker Scraper Lambda Development Plan

## 📋 Project Overview

The **price-tracker-scraper** is a Python 3.12 AWS Lambda function responsible for:
- Fetching active product links from the database
- Scraping prices from various e-commerce sites (Amazon, eBay, Walmart, etc.)
- Storing price history in the database
- Running twice daily via AWS EventBridge Scheduler

## 🏗️ Architecture Context

Based on the existing architecture, the scraper lambda will:
- **Input**: Triggered by EventBridge (cron: `0 9 * * ? *` and `0 21 * * ? *`)
- **Database**: Connect to Neon PostgreSQL (same as API)
- **Output**: Store price history in `price_history` table
- **Scaling**: Handle 100-500 products per run
- **Timeout**: 10 minutes maximum

## 📁 Repository Structure

```
price-tracker-scraper/
├── README.md
├── IMPLEMENTATION_PLAN.md          # This file
├── lambda_function.py              # Main Lambda handler
├── scrapers/
│   ├── __init__.py
│   ├── base.py                     # Base scraper class
│   ├── amazon.py                   # Amazon-specific scraper
│   ├── ebay.py                     # eBay-specific scraper
│   ├── walmart.py                  # Walmart-specific scraper
│   └── bestbuy.py                  # Best Buy-specific scraper
├── utils/
│   ├── __init__.py
│   ├── db_client.py                # Database connection helper
│   ├── logger.py                   # Structured logging
│   └── validators.py               # Data validation utilities
├── infrastructure/
│   ├── template.yaml               # SAM template
│   ├── samconfig.toml              # SAM configuration
│   └── deploy.sh                   # Deployment script
├── tests/
│   ├── __init__.py
│   ├── test_scrapers.py
│   ├── test_lambda_handler.py
│   └── fixtures/                   # Test data
├── requirements.txt
├── .github/workflows/
│   └── deploy.yml                  # CI/CD pipeline
└── .env.example                    # Environment variables template
```

## 🛠️ Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

#### 1.1 Project Setup
- [x] Initialize Python project structure
- [x] Set up virtual environment and dependencies
- [x] Create AWS SAM template for deployment
- [x] Create SAM Configuration File for deployment
- [x] Configure GitHub Actions for CI/CD

#### 1.2 Logging & Monitoring
- [x] Set up structured logging with CloudWatch
- [x] Add performance metrics tracking

#### 1.3 Database Integration
- [ ] Create database connection utility (`utils/db_client.py`)
- [ ] Implement connection pooling for Lambda
- [ ] Add retry logic for database operations
- [ ] Test database connectivity

### Phase 2: Scraper Framework (Week 2)

#### 2.1 Base Scraper Class
```python
# scrapers/base.py
class BaseScraper:
    def __init__(self, session):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; PriceTracker/1.0)',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def scrape_price(self, url: str) -> ScrapingResult:
        """Abstract method to be implemented by each scraper"""
        pass
    
    def extract_price(self, html: str, selectors: List[str]) -> Optional[float]:
        """Common price extraction logic"""
        pass
```

#### 2.2 Site-Specific Scrapers
- [ ] **Amazon Scraper** (`scrapers/amazon.py`)
  - Handle different product page layouts
  - Extract price, original price, availability
  - Handle Prime vs non-Prime pricing
  - Deal with "Currently unavailable" states

- [ ] **eBay Scraper** (`scrapers/ebay.py`)
  - Handle auction vs Buy It Now
  - Extract shipping costs
  - Handle "Best Offer" scenarios

- [ ] **Walmart Scraper** (`scrapers/walmart.py`)
  - Handle in-store vs online pricing
  - Extract pickup/delivery options

- [ ] **Best Buy Scraper** (`scrapers/bestbuy.py`)
  - Handle member pricing
  - Extract store pickup availability

#### 2.3 Scraper Factory
```python
# scrapers/__init__.py
def get_scraper(store: str) -> BaseScraper:
    scrapers = {
        'amazon': AmazonScraper,
        'ebay': EbayScraper,
        'walmart': WalmartScraper,
        'bestbuy': BestBuyScraper,
    }
    return scrapers.get(store.lower(), GenericScraper)()
```

### Phase 3: Lambda Handler (Week 3)

#### 3.1 Main Handler Function
```python
# lambda_function.py
def lambda_handler(event, context):
    """
    Main Lambda handler for price scraping
    
    Flow:
    1. Fetch active product links from database
    2. Group by store for efficient scraping
    3. Scrape prices in parallel (with rate limiting)
    4. Store results in database
    5. Update product link metadata
    """
    start_time = time.time()
    
    try:
        # Initialize database connection
        db_client = DatabaseClient()
        
        # Fetch active product links
        product_links = db_client.get_active_product_links()
        
        # Group by store for efficient scraping
        links_by_store = group_by_store(product_links)
        
        # Scrape prices
        results = []
        for store, links in links_by_store.items():
            scraper = get_scraper(store)
            store_results = scrape_store_links(scraper, links)
            results.extend(store_results)
        
        # Store results in database
        db_client.store_price_history(results)
        
        # Update product link metadata
        db_client.update_link_metadata(results)
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Scraping completed successfully',
                'products_processed': len(results),
                'execution_time': time.time() - start_time
            }
        }
        
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }
```

#### 3.2 Parallel Processing
- [ ] Implement concurrent scraping with `asyncio`
- [ ] Add rate limiting to avoid being blocked
- [ ] Handle timeouts gracefully
- [ ] Implement retry logic for failed requests

#### 3.3 Error Handling
- [ ] Categorize errors (network, parsing, database)
- [ ] Implement exponential backoff
- [ ] Track consecutive failures per product link
- [ ] Disable problematic links after multiple failures

### Phase 4: Data Processing (Week 4)

#### 4.1 Price Extraction Logic
```python
# utils/price_extractor.py
class PriceExtractor:
    @staticmethod
    def extract_price(html: str, selectors: List[str]) -> Optional[float]:
        """Extract price from HTML using multiple selectors"""
        for selector in selectors:
            try:
                soup = BeautifulSoup(html, 'html.parser')
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text().strip()
                    price = PriceExtractor.parse_price(price_text)
                    if price:
                        return price
            except Exception:
                continue
        return None
    
    @staticmethod
    def parse_price(price_text: str) -> Optional[float]:
        """Parse price from text (handle $, commas, etc.)"""
        # Remove currency symbols and clean text
        cleaned = re.sub(r'[^\d.,]', '', price_text)
        # Handle different decimal separators
        if ',' in cleaned and '.' in cleaned:
            # European format: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned:
            # US format: 1,234.56
            cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned)
        except ValueError:
            return None
```

#### 4.2 Data Validation
- [ ] Validate price ranges (reasonable bounds)
- [ ] Check for price anomalies
- [ ] Validate currency consistency
- [ ] Handle missing or malformed data

#### 4.3 Database Operations
```python
# utils/db_client.py
class DatabaseClient:
    def get_active_product_links(self) -> List[ProductLink]:
        """Fetch active product links for scraping"""
        query = """
        SELECT pl.id, pl.url, pl.store, pl.product_identifier, 
               pl.last_price, pl.scrape_error_count
        FROM product_links pl
        JOIN products p ON pl.product_id = p.id
        WHERE pl.is_active = true 
        AND p.is_active = true
        AND (pl.last_checked_at IS NULL OR pl.last_checked_at < NOW() - INTERVAL '6 hours')
        ORDER BY pl.last_checked_at ASC NULLS FIRST
        """
        # Implementation here
    
    def store_price_history(self, results: List[ScrapingResult]):
        """Store scraping results in price_history table"""
        # Implementation here
    
    def update_link_metadata(self, results: List[ScrapingResult]):
        """Update product_links with latest price and metadata"""
        # Implementation here
```

### Phase 5: Testing & Deployment (Week 5)

#### 5.1 Unit Tests
- [ ] Test individual scrapers with mock HTML
- [ ] Test price extraction logic
- [ ] Test database operations
- [ ] Test error handling scenarios

#### 5.2 Integration Tests
- [ ] Test full Lambda function with test data
- [ ] Test database connectivity
- [ ] Test with real (but limited) scraping
- [ ] Performance testing

#### 5.3 Deployment
- [ ] Deploy to AWS using SAM
- [ ] Configure EventBridge scheduler
- [ ] Set up CloudWatch monitoring
- [ ] Test end-to-end functionality

#### 5.4 Advanced Monitoring & Error Handling
- [ ] **Implement error categorization**
  - Network errors (timeouts, connection refused)
  - Parsing errors (HTML structure changes, missing selectors)
  - Database errors (connection failures, constraint violations)
  - Rate limiting errors (429 responses, IP blocking)
  - Business logic errors (product not found, price unavailable)

- [ ] **Create monitoring dashboards**
  - Success/failure rates by store
  - Performance metrics (execution time, memory usage)
  - Error trends and patterns
  - Cost monitoring and optimization
  - Real-time alerts for critical failures

- [ ] **Set up alerting system**
  - CloudWatch alarms for high error rates
  - SNS notifications for critical failures
  - Slack/email alerts for monitoring team
  - Automated recovery procedures

## 🔧 Technical Specifications

### Dependencies (`requirements.txt`)
```
beautifulsoup4==4.12.2
requests==2.31.0
psycopg2-binary==2.9.7
boto3==1.28.57
python-dateutil==2.8.2
lxml==4.9.3
fake-useragent==1.4.0
```

### AWS SAM Template (`infrastructure/template.yaml`)
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Parameters:
  DatabaseUrl:
    Type: String
    Description: Database connection string
    NoEcho: true

Resources:
  PriceTrackerScraperFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./
      Handler: lambda_function.lambda_handler
      Runtime: python3.12
      Timeout: 600  # 10 minutes
      MemorySize: 512
      Environment:
        Variables:
          DATABASE_URL: !Ref DatabaseUrl
      Events:
        MorningScrape:
          Type: Schedule
          Properties:
            Schedule: cron(0 9 * * ? *)
        EveningScrape:
          Type: Schedule
          Properties:
            Schedule: cron(0 21 * * ? *)
```

### Environment Variables
```bash
# .env.example
DATABASE_URL=postgresql://user:password@host:port/database
LOG_LEVEL=INFO
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3
```

## 📊 Performance Targets

- **Cold Start**: < 2 seconds
- **Scraping Speed**: 1-3 seconds per product
- **Success Rate**: > 95% for active products
- **Memory Usage**: < 400MB
- **Timeout**: 10 minutes (handles 100-500 products)

## 🚨 Error Handling Strategy

### Error Categories
1. **Network Errors**: Retry with exponential backoff
2. **Parsing Errors**: Log and skip, update error count
3. **Database Errors**: Retry with connection pooling
4. **Rate Limiting**: Implement delays between requests

### Monitoring
- CloudWatch metrics for success/failure rates
- Alerts for consecutive failures
- Performance dashboards
- Cost monitoring

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy Scraper Lambda

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/

  deploy:
    if: github.ref == 'refs/heads/main'
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to AWS
        run: |
          sam build
          sam deploy --no-confirm-changeset
```

## 📈 Future Enhancements

### Phase 2 Features
- [ ] **Proxy Support**: Rotate IPs to avoid blocking
- [ ] **Advanced Scraping**: Playwright for JavaScript-heavy sites
- [ ] **Machine Learning**: Price prediction and anomaly detection
- [ ] **Notifications**: Alert users when prices drop
- [ ] **API Integration**: Use official APIs where available

### Scaling Considerations
- **SQS Integration**: For high-volume scraping
- **Parallel Lambdas**: Multiple workers for different stores
- **Caching**: Redis for frequently accessed data
- **Monitoring**: Advanced analytics and alerting

## 🗄️ Database Schema Reference

The scraper will interact with these tables from the existing schema:

### Complete Schema

#### `users` table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email_verified BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

#### `products` table
```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    target_price NUMERIC(12,2),
    currency VARCHAR(3) DEFAULT 'USD',
    notification_enabled BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

#### `product_links` table
```sql
CREATE TABLE product_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    url TEXT UNIQUE NOT NULL,
    store VARCHAR(100) NOT NULL,
    product_identifier VARCHAR(255),
    last_price NUMERIC(12,2),
    lowest_price_seen NUMERIC(12,2),
    highest_price_seen NUMERIC(12,2),
    last_checked_at TIMESTAMP,
    scrape_error_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```
- **Read**: Fetch active links for scraping
- **Update**: Update `last_price`, `last_checked_at`, `scrape_error_count`, `lowest_price_seen`, `highest_price_seen`, `updated_at`

#### `price_history` table
```sql
CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_link_id UUID NOT NULL REFERENCES product_links(id) ON DELETE CASCADE,
    price NUMERIC(12,2) NOT NULL,
    original_price NUMERIC(12,2),
    discount_percentage NUMERIC(5,2),
    currency VARCHAR(3) DEFAULT 'USD',
    was_available BOOLEAN DEFAULT true,
    scrape_source VARCHAR(50),
    response_time_ms INTEGER,
    checked_at TIMESTAMP DEFAULT now()
);
```
- **Insert**: Store new price data with metadata including performance metrics and discount information

### Key Fields for Scraping
```sql
-- Product links to scrape
SELECT pl.id, pl.url, pl.store, pl.product_identifier, 
       pl.last_price, pl.lowest_price_seen, pl.highest_price_seen,
       pl.scrape_error_count, p.target_price, p.currency
FROM product_links pl
JOIN products p ON pl.product_id = p.id
WHERE pl.is_active = true 
AND p.is_active = true
AND (pl.last_checked_at IS NULL OR pl.last_checked_at < NOW() - INTERVAL '6 hours')
ORDER BY pl.last_checked_at ASC NULLS FIRST;
```

### Key Schema Notes
- All tables use **UUID** primary keys instead of SERIAL integers
- All foreign keys have `ON DELETE CASCADE` for data integrity
- Price fields use `NUMERIC(12,2)` for precision (10 digits before decimal, 2 after)
- Timestamps use `now()` instead of `CURRENT_TIMESTAMP`
- The `price_history` table tracks performance (`response_time_ms`) and discount data
- The `product_links` table maintains price ranges (`lowest_price_seen`, `highest_price_seen`)

## 🎯 Success Criteria

### MVP (Minimum Viable Product)
- [ ] Successfully scrape prices from Amazon, eBay, Walmart, Best Buy
- [ ] Store price history in database
- [ ] Run twice daily via EventBridge
- [ ] Handle 100+ products per run
- [ ] 95%+ success rate for active products

### Production Ready
- [ ] Comprehensive error handling and logging
- [ ] Performance monitoring and alerting
- [ ] Automated deployment pipeline
- [ ] Cost optimization (< $5/month)
- [ ] Documentation and runbooks

---

**Last Updated**: October 2024  
**Version**: 1.0  
**Status**: Planning Phase
