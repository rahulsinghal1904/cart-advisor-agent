#!/usr/bin/env python
"""
This script tests all scrapers using our simplified provider implementation.
It provides a reliable way to run price searches for all supported retailers.
"""
import asyncio
import logging
import sys
import json
from src.e_commerce_agent.providers.simple_provider import SimplePriceProvider

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

async def test_retailer(provider, url):
    """Test a specific retailer URL."""
    logger.info(f"Testing URL: {url}")
    
    # Get product details
    result = await provider.get_product_details(url)
    
    # Print basic info
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Source: {result.get('source')}")
    logger.info(f"Title: {result.get('title', 'Unknown')}")
    logger.info(f"Price: {result.get('price')}")
    logger.info(f"Price Text: {result.get('price_text', 'No price available')}")
    
    # Print full result in JSON format for debugging
    logger.debug(f"Full result: {json.dumps(result, indent=2)}")
    
    return result

async def main():
    """Run tests for all supported retailers."""
    if len(sys.argv) > 1:
        # Use URL from command line if provided
        urls = [sys.argv[1]]
    else:
        # Otherwise use sample URLs for each retailer
        urls = [
            # Amazon (works well with MinimalStealthScraper)
            "https://www.amazon.com/Apple-iPhone-13-128GB-Blue/dp/B09G9HD6PD/",
            
            # Target (uses SimpleScraper)
            "https://www.target.com/p/kitsch-queen-size-thread-count-34-600-34-satin-standard-pillowcase-ivory/-/A-91792291",
            
            # Best Buy (uses SimpleScraper)
            "https://www.bestbuy.com/site/sony-whch720n-wireless-noise-canceling-headphones-pink/6620465.p"
        ]
    
    # Initialize the simple provider
    provider = SimplePriceProvider()
    logger.info("Using SimplePriceProvider for all retailers.")
    
    # Run tests for all URLs
    results = {}
    for url in urls:
        logger.info("\n" + "="*60)
        result = await test_retailer(provider, url)
        results[result.get('source', 'unknown')] = result
    
    logger.info("\n" + "="*60)
    logger.info("Testing complete for all retailers.")
    
    # Display a summary of results
    logger.info("\nSUMMARY OF RESULTS:")
    for source, result in results.items():
        status = "✅ SUCCESS" if result.get('status') == 'success' else "❌ FAILED"
        price = result.get('price_text', 'No price') if result.get('price_text') else f"${result.get('price')}" if result.get('price') else "No price"
        logger.info(f"{source.upper()}: {status} | {result.get('title', 'Unknown')} | {price}")

if __name__ == "__main__":
    asyncio.run(main()) 