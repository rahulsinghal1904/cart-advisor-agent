#!/usr/bin/env python
"""
Test script for the simplified scraper implementation.
"""
import asyncio
import logging
import sys
from src.e_commerce_agent.providers.simple_scraper import SimpleScraper

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

async def test_simple_scraper():
    """Test simplified Target and Best Buy scrapers."""
    scraper = SimpleScraper()
    
    # Test Target scraper
    logger.info("Testing simplified Target scraper...")
    target_url = "https://www.target.com/p/kitsch-queen-size-thread-count-34-600-34-satin-standard-pillowcase-ivory/-/A-91792291"
    target_result = await scraper.scrape_target(target_url)
    
    # Print Target result
    logger.info("Target Result:")
    logger.info(f"Status: {target_result.get('status')}")
    logger.info(f"Title: {target_result.get('title')}")
    logger.info(f"Price Text: {target_result.get('price_text')}")
    logger.info(f"Source: {target_result.get('source')}")
    
    # Test Best Buy scraper
    logger.info("\nTesting simplified Best Buy scraper...")
    bestbuy_url = "https://www.bestbuy.com/site/sony-whch720n-wireless-noise-canceling-headphones-pink/6620465.p"
    bestbuy_result = await scraper.scrape_bestbuy(bestbuy_url)
    
    # Print Best Buy result
    logger.info("Best Buy Result:")
    logger.info(f"Status: {bestbuy_result.get('status')}")
    logger.info(f"Title: {bestbuy_result.get('title')}")
    logger.info(f"Price Text: {bestbuy_result.get('price_text')}")
    logger.info(f"Source: {bestbuy_result.get('source')}")

if __name__ == "__main__":
    asyncio.run(test_simple_scraper()) 