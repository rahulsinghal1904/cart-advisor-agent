# Multi-Source Price Fetching System

This directory contains the price fetching components for the e-commerce agent, with a focus on high availability and reliability.

## Architecture Overview

The price fetching system uses a multi-tier approach with cascading fallbacks to ensure reliable price data:

1. **PriceProvider** (`price_provider.py`) - The main entry point that orchestrates multiple data sources
2. **PriceAPIFetcher** (`price_api_fetcher.py`) - Fetches pricing via free APIs and structured data extraction
3. **PriceScraper** and **StealthScraper** - Fallback mechanisms that use browser automation

## Key Features

- **Multi-Source Strategy**: Tries multiple data sources in sequence until one succeeds
- **Caching**: Reduces API calls and improves response time
- **Rate Limiting**: Prevents exceeding free API limits
- **Adaptive Source Ranking**: Learns which sources are most reliable for each retailer
- **Robust Error Handling**: Graceful degradation when sources fail

## Data Flow

```
User Request → PriceProvider → PriceAPIFetcher → Free APIs/JSON Extraction
                     ↓                ↓
                     ↓          Web Search Fallback
                     ↓
            Standard Scraper Fallback
                     ↓
            Stealth Scraper Fallback
```

## Supported E-commerce Sites

- Amazon
- Walmart
- Best Buy
- Target (basic support)
- eBay (basic support)

## Free APIs and Data Sources

The system uses several free or publicly accessible data sources:

1. **Schema.org JSON-LD**: Extracts structured product data embedded in pages
2. **Website JSON Data**: Extracts product data from JSON objects in the page source
3. **Structured HTML**: Parses HTML using patterns specific to each retailer
4. **Web Search**: Uses search results as a last resort for price estimation

## Extending the System

To add support for a new retailer:

1. Add a domain-specific method in `PriceAPIFetcher` like `_get_newstore_product_data`
2. Add URL pattern extraction for the retailer
3. Update the domain detection in `_extract_domain` method
4. Add retailer-specific JSON extraction patterns if needed

## Benefits Over Previous Approach

- **Higher Availability**: Multiple fallback mechanisms ensure a response
- **Improved Performance**: API-first approach is faster than browser automation
- **Lower Resource Usage**: Less reliance on browser-based scraping
- **Better Scaling**: More efficient resource utilization under load
- **Adaptive Learning**: System improves over time by tracking success rates 