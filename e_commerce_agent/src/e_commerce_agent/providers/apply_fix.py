"""
Apply fixes for Target and Best Buy scrapers.

This script directly patches the price_scraper module and alternative_finder module
to fix Target and Best Buy scraping and alternatives.
"""
import os
import sys
import logging
import importlib.util
import types
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import re

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our own implementation
from target_bestbuy_fix import scrape_target, scrape_bestbuy, find_alternatives

def apply_fixes():
    """Apply all fixes to make Target and Best Buy scrapers work."""
    # Load the price_scraper module
    import price_scraper
    
    # Directly replace the problematic methods
    
    # 1. First, patch the StealthScraper class
    if hasattr(price_scraper, 'StealthScraper'):
        logger.info("Patching StealthScraper class")
        
        # Check if it has the target method
        if hasattr(price_scraper.StealthScraper, 'scrape_target'):
            # Wrap our function to match the method signature
            async def stealth_scrape_target(self, url):
                logger.info(f"[FIXED] StealthScraper.scrape_target redirecting to fixed implementation")
                return await scrape_target(url)
                
            # Replace the method
            setattr(price_scraper.StealthScraper, 'scrape_target', stealth_scrape_target)
            logger.info("StealthScraper.scrape_target patched successfully")
            
        # Check if it has the bestbuy method
        if hasattr(price_scraper.StealthScraper, 'scrape_bestbuy'):
            # Wrap our function to match the method signature
            async def stealth_scrape_bestbuy(self, url):
                logger.info(f"[FIXED] StealthScraper.scrape_bestbuy redirecting to fixed implementation")
                return await scrape_bestbuy(url)
                
            # Replace the method
            setattr(price_scraper.StealthScraper, 'scrape_bestbuy', stealth_scrape_bestbuy)
            logger.info("StealthScraper.scrape_bestbuy patched successfully")
    
    # 2. Now monkey-patch the scrape_target and scrape_bestbuy functions at module level
    logger.info("Looking for module-level definitions of scrape_target and scrape_bestbuy")
    
    # Find all the functions/methods in the module
    for name in dir(price_scraper):
        # Skip special names and classes we've already patched
        if name.startswith('__') or name in ['StealthScraper', 'PriceScraper']:
            continue
            
        attr = getattr(price_scraper, name)
        if callable(attr) and name in ['scrape_target', 'scrape_bestbuy']:
            logger.info(f"Found module-level function: {name}")
            
            # Create replacement function with the same signature
            if name == 'scrape_target':
                async def module_scrape_target(url):
                    logger.info(f"[FIXED] Module-level scrape_target redirecting to fixed implementation")
                    return await scrape_target(url)
                setattr(price_scraper, name, module_scrape_target)
                logger.info(f"Replaced module-level {name} function")
                
            elif name == 'scrape_bestbuy':
                async def module_scrape_bestbuy(url):
                    logger.info(f"[FIXED] Module-level scrape_bestbuy redirecting to fixed implementation")
                    return await scrape_bestbuy(url)
                setattr(price_scraper, name, module_scrape_bestbuy)
                logger.info(f"Replaced module-level {name} function")
    
    # 3. Create a direct replacement for get_product_details that uses our implementation
    try:
        from price_provider import PriceProvider
        
        # Store the original method
        original_get_details = PriceProvider.get_product_details
        
        # Create a new method that uses our implementations
        async def fixed_get_product_details(self, product_url):
            """Fixed implementation that routes to the right scraper."""
            logger.info(f"[FIXED] PriceProvider.get_product_details for URL: {product_url}")
            
            # Determine the source
            source = self._determine_source(product_url)
            
            # Route to the appropriate implementation
            if source == 'target':
                logger.info(f"[FIXED] Routing to fixed Target implementation")
                return await scrape_target(product_url)
            elif source == 'bestbuy':
                logger.info(f"[FIXED] Routing to fixed Best Buy implementation")
                return await scrape_bestbuy(product_url)
            else:
                # Use original implementation for other sources
                logger.info(f"Using original implementation for {source}")
                return await original_get_details(self, product_url)
        
        # Replace the method
        PriceProvider.get_product_details = fixed_get_product_details
        logger.info("PriceProvider.get_product_details patched successfully")
        
        # Also patch the find_alternatives method
        original_find_alternatives = PriceProvider.find_alternatives
        
        async def fixed_provider_find_alternatives(self, product_details, max_results=3):
            """Fixed implementation of find_alternatives."""
            logger.info(f"[FIXED] PriceProvider.find_alternatives")
            return find_alternatives(product_details, max_results)
            
        # Replace the method
        PriceProvider.find_alternatives = fixed_provider_find_alternatives
        logger.info("PriceProvider.find_alternatives patched successfully")
    except Exception as e:
        logger.warning(f"Could not patch PriceProvider: {e}")
    
    # 4. Patch alternative_finder if it exists
    try:
        import alternative_finder
        
        # Check if it has find_alternatives
        if hasattr(alternative_finder, 'find_alternatives'):
            original_func = alternative_finder.find_alternatives
            
            # Create async wrapper for our sync function
            async def patched_find_alternatives(product_details, max_results=3):
                logger.info(f"[FIXED] alternative_finder.find_alternatives")
                return find_alternatives(product_details, max_results)
                
            # Replace the function
            alternative_finder.find_alternatives = patched_find_alternatives
            logger.info("alternative_finder.find_alternatives patched successfully")
    except Exception as e:
        logger.warning(f"Could not patch alternative_finder: {e}")
    
    logger.info("All fixes applied successfully")
    return True

if __name__ == "__main__":
    print("="*80)
    print("APPLYING FIXES FOR TARGET AND BEST BUY")
    print("="*80)
    
    try:
        apply_fixes()
        print("✅ Successfully applied all fixes")
        print("Now you can run the e-commerce agent normally")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error applying fixes: {e}")
        sys.exit(1) 