# Price Tracker Scraper – Implementation Plan

## Objective

Fetch prices from **Mercado Livre** and **Amazon**, and store the data in the database. Nothing else.

## Scope

- **Stores**: Mercado Livre, Amazon (amazon.br)
- **Runtime**: One AWS Lambda, triggered by EventBridge (scheduled) or by test events
- **Database**: Neon PostgreSQL. Tables: `product_links` (read), `price_history` (write)

## Implementation Checklist

- [x] Mercado Livre scraper (`scrapers/mercadolivre.py`) + base scraper
- [x] Database client with connection and retry (`utils/db_client.py`)
- [ ] **Amazon scraper** (`scrapers/amazon.py` or `amazon_br.py`) + register in `scrapers/__init__.py` as `amazon_br` (and optionally `amazon`)
- [ ] **DatabaseClient.get_active_product_links()** – query `product_links` (join `products` if needed), filter `store IN ('mercadolivre', 'amazon_br')`, return list of `{id, url, store, ...}`
- [ ] **DatabaseClient.insert_price_history(results)** – insert into `price_history` from `ScrapingResult`; optionally update `product_links` (last_price, last_checked_at, scrape_error_count)
- [ ] **Lambda scheduled flow** – on schedule: get links → for each link `get_scraper(store).scrape_price(url, id)` → `insert_price_history(results)`. Keep existing `test_scraper` event path unchanged.

Optional: short delay between requests to reduce blocking risk.

## Database Reference (key columns only)

**product_links** (read): `id`, `url`, `store`, `product_id`, `last_price`, `last_checked_at`, `scrape_error_count`, `lowest_price_seen`, `highest_price_seen`

**price_history** (insert): `product_link_id`, `price`, `original_price`, `discount_percentage`, `currency`, `was_available`, `scrape_source`, `response_time_ms`. `checked_at` defaults to `now()`.

- Only insert into `price_history` when `price` is not null (schema: `price NOT NULL`).
- When saving results, optionally update `product_links`: `last_checked_at`, `last_price` (if scraped), `scrape_error_count` (increment on error), and optionally `lowest_price_seen` / `highest_price_seen`.

## Repository Layout (relevant parts)

```
lambda_function.py       # Handler: test_scraper path + scheduled flow (get links → scrape → save)
scrapers/
  base.py                # BaseScraper, ScrapingResult
  mercadolivre.py        # Mercado Livre scraper
  amazon.py              # Amazon (BR) scraper – to add
  __init__.py            # get_scraper(store) – add amazon_br
utils/
  db_client.py           # DatabaseClient + get_active_product_links, insert_price_history
  logger.py
```

## Success Criteria

- Lambda can be invoked with a scheduled event, fetch active product links for Mercado Livre and Amazon, scrape each URL, and persist price history (and optional link metadata).
- Test event `action: test_scraper` with `store` and `url` still works for both stores.
