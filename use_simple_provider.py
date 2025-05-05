#!/usr/bin/env python
"""
This script tests all scrapers using our simplified provider implementation.
It provides a reliable way to run price searches for all supported retailers.
"""
import asyncio
import logging
import sys
import json
import time
from src.e_commerce_agent.providers.simple_provider import SimplePriceProvider

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

async def test_retailer(provider, url):
    """Test a specific retailer URL."""
    logger.info(f"Testing URL: {url}")
    start_time = time.time()
    
    # Get product details
    result = await provider.get_product_details(url)
    
    elapsed = time.time() - start_time
    logger.info(f"Extraction completed in {elapsed:.2f} seconds")
    
    # Print basic info
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Source: {result.get('source')}")
    logger.info(f"Title: {result.get('title', 'Unknown')}")
    logger.info(f"Price: {result.get('price')}")
    logger.info(f"Price Text: {result.get('price_text', 'No price available')}")
    logger.info(f"Rating: {result.get('rating', 'No rating')}")
    logger.info(f"Availability: {result.get('availability', 'Unknown')}")
    
    # Print full result in JSON format for debugging
    verbose_mode = '--verbose' in sys.argv
    if verbose_mode:
        logger.info(f"Full result: {json.dumps(result, indent=2)}")
    
    return result

async def main():
    """Run tests for all supported retailers."""
    # Parse command-line arguments
    verbose_mode = '--verbose' in sys.argv
    
    # Use URL from command line if provided and not a flag
    urls = []
    for arg in sys.argv[1:]:
        if not arg.startswith('--'):
            urls.append(arg)
    
    # If no URLs were provided, use default test URLs
    if not urls:
        # Default URLs for testing
        urls = [
            # Amazon (uses the original StealthScraper implementation)
            "https://www.amazon.com/OnePlus-Certified-Charging-Wireless-Charger/dp/B09BDLVPHQ/",
            
            # Target (uses our new simplified implementation)
            "https://www.target.com/p/kitsch-queen-size-thread-count-34-600-34-satin-standard-pillowcase-ivory/-/A-91792291",
            
            # Best Buy (uses our new simplified implementation)
            "https://www.bestbuy.com/site/apple-airpods-pro-2nd-generation-with-magsafe-case-usb-c-white/6525204.p"
        ]
    
    # Initialize the simple provider
    provider = SimplePriceProvider()
    logger.info(f"Using SimplePriceProvider with default URLs.")
    logger.info(f"Verbose mode: {'ON' if verbose_mode else 'OFF'}")
    
    # Run tests for all URLs
    results = {}
    for url in urls:
        logger.info("\n" + "="*80)
        result = await test_retailer(provider, url)
        results[result.get('source', 'unknown')] = result
        if len(urls) > 1:
            logger.info("Waiting 5 seconds before next test...")
            await asyncio.sleep(5)  # Longer pause between tests
    
    logger.info("\n" + "="*80)
    logger.info("Testing complete for all retailers.")
    
    # Display a summary of results
    logger.info("\nSUMMARY OF RESULTS:")
    for source, result in results.items():
        status = "✅ SUCCESS" if result.get('status') == 'success' else "❌ FAILED"
        title = result.get('title', 'Unknown')
        price = result.get('price_text', 'No price') if result.get('price_text') else f"${result.get('price')}" if result.get('price') else "No price"
        logger.info(f"{source.upper()}: {status} | {title} | {price}")
    
    logger.info("\nIMPORTANT: This implementation keeps Amazon's original flow entirely intact")
    logger.info("while providing alternative implementations for Target and Best Buy.")

if __name__ == "__main__":
    asyncio.run(main()) 