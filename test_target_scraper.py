#!/usr/bin/env python
"""
This script tests specifically the Target scraper with the URL that was problematic.
"""
import asyncio
import logging
import sys
import json
import time
from src.e_commerce_agent.providers.simple_scraper import TargetScraper

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

async def main():
    """Test Target scraper directly."""
    # The URL that was problematic
    url = "https://www.target.com/p/kitsch-queen-size-thread-count-34-600-34-satin-standard-pillowcase-ivory/-/A-91792291"
    
    logger.info(f"Testing Target scraper directly with URL: {url}")
    logger.info("=" * 80)
    
    # Create scraper instance
    scraper = TargetScraper()
    
    start_time = time.time()
    logger.info("Starting scraper...")
    
    # Test the scraper
    try:
        # Get product details directly from the scraper
        result = await scraper.extract_product_data(url)
        
        elapsed = time.time() - start_time
        logger.info(f"Scraping completed in {elapsed:.2f} seconds")
        
        # Print the result
        logger.info("Results:")
        logger.info(f"Status: {result.get('status')}")
        logger.info(f"Title: {result.get('title', 'Unknown')}")
        logger.info(f"Price: {result.get('price')}")
        logger.info(f"Price Text: {result.get('price_text', 'No price available')}")
        logger.info(f"Rating: {result.get('rating', 'No rating')}")
        logger.info(f"Availability: {result.get('availability', 'Unknown')}")
        
        # Print full result
        logger.info("Full result:")
        logger.info(json.dumps(result, indent=2))
        
        logger.info("=" * 80)
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test
    asyncio.run(main()) 