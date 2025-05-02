#!/usr/bin/env python
import asyncio
import logging
import sys
import json
from src.e_commerce_agent.providers.price_provider import PriceProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def test_alternatives_search():
    """Test alternatives search functionality for various products."""
    # Create price provider
    provider = PriceProvider()
    
    # Test URLs for different retailers
    test_urls = [
        "https://www.amazon.com/Apple-iPhone-13-128GB-Blue/dp/B09G9HD6PD/",
        "https://www.target.com/p/apple-airpods-with-charging-case-2nd-generation/-/A-54191097",
        "https://www.bestbuy.com/site/logitech-g502-hero-wired-optical-gaming-mouse-with-rgb-lighting-black/6265133.p?skuId=6265133"
    ]
    
    for url in test_urls:
        try:
            logger.info(f"\n\n=========================================")
            logger.info(f"TESTING URL: {url}")
            logger.info(f"=========================================")
            
            # First get product details
            logger.info(f"Fetching product details...")
            product_details = await provider.get_product_details(url)
            
            if product_details.get("status") != "success":
                logger.error(f"Failed to fetch product details: {product_details.get('message', 'Unknown error')}")
                continue
            
            # Log basic product info
            logger.info(f"Product details success:")
            logger.info(f"  - Title: {product_details.get('title', 'Unknown')}")
            logger.info(f"  - Price: {product_details.get('price_text', 'Unknown')}")
            logger.info(f"  - Source: {product_details.get('source', 'Unknown')}")
            
            # Now search for alternatives
            logger.info(f"Searching for alternatives...")
            alternatives = await provider.find_alternatives(product_details)
            
            # Log alternatives
            if alternatives:
                logger.info(f"Found {len(alternatives)} alternatives:")
                for i, alt in enumerate(alternatives):
                    logger.info(f"\nAlternative {i+1}:")
                    logger.info(f"  - Source: {alt.get('source', 'Unknown')}")
                    logger.info(f"  - Title: {alt.get('title', 'Unknown')}")
                    logger.info(f"  - Price: {alt.get('price_text') if alt.get('price_text') else alt.get('price', 'Unknown')}")
                    logger.info(f"  - Better deal: {alt.get('is_better_deal', False)}")
                    logger.info(f"  - Reason: {alt.get('reason', 'Unknown')}")
            else:
                logger.warning(f"No alternatives found for {product_details.get('title', 'Unknown')}")
            
            logger.info(f"=========================================\n\n")
            
        except Exception as e:
            logger.error(f"Error testing {url}: {str(e)}")
    
    # Clean up
    provider.cleanup()

if __name__ == "__main__":
    asyncio.run(test_alternatives_search()) 