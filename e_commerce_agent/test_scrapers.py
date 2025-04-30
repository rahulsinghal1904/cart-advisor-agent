import asyncio
import json
import sys
import os

# Add the parent directory to sys.path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from e_commerce_agent.src.e_commerce_agent.providers.price_scraper import PriceScraper

async def test_scrapers():
    """Test the scraper implementations for different retailers."""
    print("Testing price scrapers for multiple retailers")
    print("-" * 50)
    
    # Initialize the scraper
    scraper = PriceScraper()
    
    # Test URLs
    test_urls = [
        "https://www.amazon.com/Apple-MacBook-16-inch-10%E2%80%91core-16%E2%80%91core/dp/B09JQKBQSB/",
        "https://www.walmart.com/ip/Apple-AirPods-Pro-2nd-Generation-with-MagSafe-Case-USB-C/5287628428", 
        "https://www.bestbuy.com/site/sony-playstation-5-slim-console-white/6565303.p?skuId=6565303"
    ]
    
    # Test each URL
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        try:
            result = await scraper.get_product_details(url)
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"Source: {result.get('source', 'unknown')}")
            print(f"Title: {result.get('title', 'Not found')}")
            print(f"Price: {result.get('price_text', 'Not found')}")
            print(f"Rating: {result.get('rating', 'Not found')}")
            
            # Print the first few features if available
            if 'features' in result and result['features']:
                print("Features:")
                for i, feature in enumerate(result['features'][:3]):
                    print(f"  - {feature[:50]}{'...' if len(feature) > 50 else ''}")
            
            # Save detailed results to file for debugging
            domain = url.split('/')[2].replace('www.', '')
            with open(f"scraper_test_{domain}.json", "w") as f:
                json.dump(result, f, indent=2)
                print(f"Detailed results saved to scraper_test_{domain}.json")
            
        except Exception as e:
            print(f"Error testing {url}: {e}")
    
    # Cleanup
    if hasattr(scraper, 'stealth_scraper'):
        scraper.stealth_scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(test_scrapers()) 