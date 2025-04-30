import asyncio
import logging
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_scrapers():
    """Test the Walmart and Best Buy scrapers from PriceScraper using direct imports"""
    logger.info("Testing Walmart and Best Buy scrapers")
    
    try:
        # Import here to avoid potential import errors
        from src.e_commerce_agent.providers.price_scraper import PriceScraper
        
        # Initialize the scraper
        scraper = PriceScraper()
        
        # Test URLs
        walmart_url = "https://www.walmart.com/ip/Apple-AirPods-with-Charging-Case-2nd-Generation/604342441"
        bestbuy_url = "https://www.bestbuy.com/site/apple-airpods-with-charging-case-2nd-generation-white/6084400.p"
        
        # Test Walmart scraper
        logger.info(f"Testing Walmart scraper with URL: {walmart_url}")
        walmart_result = await scraper.scrape_walmart(walmart_url)
        
        print("\nWALMART RESULT:")
        print(f"Status: {walmart_result.get('status', 'unknown')}")
        print(f"Title: {walmart_result.get('title', 'Not found')}")
        print(f"Price: {walmart_result.get('price_text', 'Not found')}")
        
        # Test Best Buy scraper
        logger.info(f"Testing Best Buy scraper with URL: {bestbuy_url}")
        bestbuy_result = await scraper.scrape_bestbuy(bestbuy_url)
        
        print("\nBEST BUY RESULT:")
        print(f"Status: {bestbuy_result.get('status', 'unknown')}")
        print(f"Title: {bestbuy_result.get('title', 'Not found')}")
        print(f"Price: {bestbuy_result.get('price_text', 'Not found')}")
        
    except ImportError as e:
        logger.error(f"Import error: {str(e)}")
        print(f"\nERROR: Could not import the required modules: {str(e)}")
        print("Please ensure all dependencies are installed.")
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        print(f"\nERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_scrapers()) 