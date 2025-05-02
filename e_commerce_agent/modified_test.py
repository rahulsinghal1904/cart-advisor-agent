#!/usr/bin/env python
import asyncio
import sys
import logging
from importlib import reload

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

async def test_scrapers():
    """Test Target and Best Buy scrapers with emergency patch applied."""
    # Apply emergency patch
    print("Applying emergency patch...")
    import emergency_fix
    emergency_fix.apply_patch()
    
    # Import the patched module
    from src.e_commerce_agent.providers.price_scraper import PriceScraper
    
    # Create the scraper instance
    scraper = PriceScraper()
    
    # Print available methods for debugging
    logger.info("Available methods after patching:")
    logger.info(str([m for m in dir(scraper) if not m.startswith('_')]))
    
    # Test Target scraper
    logger.info("Testing Target scraper...")
    target_url = "https://www.target.com/p/kitsch-queen-size-thread-count-34-600-34-satin-standard-pillowcase-ivory/-/A-91792291"
    target_result = await scraper.get_product_details(target_url)
    
    # Print Target result
    logger.info("Target Result:")
    logger.info(f"Status: {target_result.get('status')}")
    logger.info(f"Title: {target_result.get('title')}")
    logger.info(f"Price: {target_result.get('price')}")
    logger.info(f"Price Text: {target_result.get('price_text')}")
    logger.info(f"Source: {target_result.get('source')}")
    
    # Test Best Buy scraper
    logger.info("\nTesting Best Buy scraper...")
    bestbuy_url = "https://www.bestbuy.com/site/sony-whch720n-wireless-noise-canceling-headphones-pink/6620465.p"
    bestbuy_result = await scraper.get_product_details(bestbuy_url)
    
    # Print Best Buy result
    logger.info("Best Buy Result:")
    logger.info(f"Status: {bestbuy_result.get('status')}")
    logger.info(f"Title: {bestbuy_result.get('title')}")
    logger.info(f"Price: {bestbuy_result.get('price')}")
    logger.info(f"Price Text: {bestbuy_result.get('price_text')}")
    logger.info(f"Source: {bestbuy_result.get('source')}")

if __name__ == "__main__":
    asyncio.run(test_scrapers()) 