#!/usr/bin/env python
"""
Wrapper script that applies patches to the e-commerce agent
and then runs the main application.

This ensures that Target and Best Buy scrapers work properly while
preserving the original Amazon flow.
"""
import sys
import os
import importlib
import logging
import traceback
from typing import Dict, Any, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path to the main application
MAIN_MODULE = "src.e_commerce_agent.e_commerce_agent"

def apply_patches():
    """Apply patches to fix Target and Best Buy scraping."""
    logger.info("Applying patches to fix Target and Best Buy scrapers")
    
    try:
        # First import the simple provider
        from src.e_commerce_agent.providers.simple_provider import SimplePriceProvider
        
        # Then import the price_scraper module
        import src.e_commerce_agent.providers.price_scraper as price_scraper
        
        # Create a provider instance
        provider = SimplePriceProvider()
        logger.info("Created SimplePriceProvider instance")
        
        # Create patched methods
        async def patched_scrape_target(self, url):
            """Patched Target scraper that uses SimplePriceProvider."""
            logger.info(f"[PATCHED] Scraping Target URL: {url}")
            return await provider.get_product_details(url)
            
        async def patched_scrape_bestbuy(self, url):
            """Patched Best Buy scraper that uses SimplePriceProvider."""
            logger.info(f"[PATCHED] Scraping Best Buy URL: {url}")
            return await provider.get_product_details(url)
        
        # Apply patches to both PriceScraper and StealthScraper classes
        # Find all classes that might have these methods
        for cls_name in dir(price_scraper):
            cls = getattr(price_scraper, cls_name)
            if isinstance(cls, type):  # Check if it's a class
                if hasattr(cls, 'scrape_target'):
                    logger.info(f"Patching scrape_target in {cls_name}")
                    setattr(cls, 'scrape_target', patched_scrape_target)
                    
                if hasattr(cls, 'scrape_bestbuy'):
                    logger.info(f"Patching scrape_bestbuy in {cls_name}")
                    setattr(cls, 'scrape_bestbuy', patched_scrape_bestbuy)
        
        logger.info("Successfully applied patches to Target and Best Buy scrapers")
        return True
    except Exception as e:
        logger.error(f"Failed to apply patches: {str(e)}")
        traceback.print_exc()
        return False

def run_main_application():
    """Run the main e-commerce agent application."""
    logger.info(f"Running main application: {MAIN_MODULE}")
    
    try:
        # Import the main module
        main_module = importlib.import_module(MAIN_MODULE)
        
        # If the module has a main function, run it
        if hasattr(main_module, "main"):
            logger.info("Running main() function")
            main_module.main()
        else:
            logger.warning("No main() function found, running module directly")
            # If no main function, just running the module should be enough
            # as the code at module level will execute
            pass
            
        return True
    except Exception as e:
        logger.error(f"Failed to run main application: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*80)
    print("PATCHED E-COMMERCE AGENT")
    print("="*80)
    print("This wrapper applies fixes to Target and Best Buy scrapers")
    print("while preserving the original Amazon implementation.")
    print("="*80)
    
    # Apply patches
    if apply_patches():
        print("✅ Successfully applied patches to Target and Best Buy scrapers")
        
        # Run the main application
        if run_main_application():
            print("✅ Main application completed successfully")
        else:
            print("❌ Main application failed")
            sys.exit(1)
    else:
        print("❌ Failed to apply patches")
        sys.exit(1) 