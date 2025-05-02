#!/usr/bin/env python
"""
Test script for the simplified price provider.
This demonstrates using the simplified provider as a direct replacement
for the problematic PriceScraper implementation.
"""
import asyncio
import logging
import sys
from src.e_commerce_agent.providers.simple_provider import SimplePriceProvider

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

async def test_simple_provider():
    """Test simplified price provider with multiple retailers."""
    provider = SimplePriceProvider()
    
    # Test with various retailers
    test_urls = [
        # Amazon (should use the specialized StealthScraper)
        "https://www.amazon.com/Apple-iPhone-13-128GB-Blue/dp/B09G9HD6PD/",
        
        # Target (uses SimpleScraper)
        "https://www.target.com/p/kitsch-queen-size-thread-count-34-600-34-satin-standard-pillowcase-ivory/-/A-91792291",
        
        # Best Buy (uses SimpleScraper)
        "https://www.bestbuy.com/site/sony-whch720n-wireless-noise-canceling-headphones-pink/6620465.p"
    ]
    
    # Test each URL
    for url in test_urls:
        logger.info(f"\nTesting provider with URL: {url}")
        
        # Get product details
        result = await provider.get_product_details(url)
        
        # Print results
        logger.info(f"Status: {result.get('status')}")
        logger.info(f"Source: {result.get('source')}")
        logger.info(f"Title: {result.get('title')}")
        logger.info(f"Price: {result.get('price')}")
        
        if result.get('status') == 'error':
            logger.error(f"Error message: {result.get('message')}")

if __name__ == "__main__":
    asyncio.run(test_simple_provider()) 