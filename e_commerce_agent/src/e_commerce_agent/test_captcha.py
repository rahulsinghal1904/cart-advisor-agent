#!/usr/bin/env python3
"""
Test script for the stealth scraping functionality.
This script attempts to access e-commerce URLs and tests our anti-detection system.
"""

import asyncio
import logging
import os
import sys
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("stealth_test")

# Add parent directory to path to import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(parent_dir)

# Now import using relative imports
from src.e_commerce_agent.providers.price_scraper import PriceScraper

async def test_stealth_scraping():
    """Test the stealth scraping capabilities with focus on price extraction."""
    
    # Create the price scraper
    scraper = PriceScraper()
    
    # Example URLs that often trigger anti-bot measures - include a variety of product types
    test_urls = [
        "https://www.amazon.com/dp/B07ZPKN6YR",  # AirPods Pro
        "https://www.amazon.com/Apple-MacBook-13-inch-256GB-Storage/dp/B08N5M7S6K/",  # MacBook Air
        "https://www.amazon.com/dp/B06XCM9LJ4",  # Instant Pot
        "https://www.amazon.com/dp/B09JQL3MXB",  # PlayStation 5 Console
        "https://www.amazon.com/dp/B09ZQ429Y3"   # Samsung TV
    ]
    
    # Track success/failure stats
    total = len(test_urls)
    success = 0
    partial = 0
    price_success = 0
    
    # Try each URL
    for i, url in enumerate(test_urls, 1):
        print(f"\n[{i}/{total}] Testing URL: {url}")
        
        try:
            # Attempt to scrape the page
            result = await scraper.get_product_details(url)
            
            if result.get("status") == "success":
                success += 1
                price = result.get("price")
                price_text = result.get("price_text")
                
                if price is not None:
                    price_success += 1
                    print(f"✓ SUCCESS! Product: {result.get('title')[:50]}...")
                    print(f"✓ PRICE: {price_text} (numeric value: ${price:.2f})")
                    print(f"✓ Other details: Rating: {result.get('rating')}, ASIN: {result.get('asin')}")
                else:
                    print(f"✓ SUCCESS with missing price! Product: {result.get('title')[:50]}...")
                    print(f"✗ Price extraction failed. Price text: {price_text}")
                    print(f"✓ Other details: Rating: {result.get('rating')}, ASIN: {result.get('asin')}")
                
                # Save the successful result for analysis
                with open(f"test_result_{i}.json", "w") as f:
                    json.dump(result, f, indent=2)
                    print(f"✓ Saved details to test_result_{i}.json")
                
            elif result.get("status") == "partial":
                partial += 1
                print(f"⚠ PARTIAL SUCCESS! {result.get('message')}")
                print(f"⚠ Information retrieved: {json.dumps(result, indent=2)}")
            else:
                print(f"✗ FAILED! Error: {result.get('message')}")
                
        except Exception as e:
            print(f"✗ ERROR: {str(e)}")
    
    # Print summary
    print("\n" + "="*50)
    print(f"SUMMARY OF {total} TESTS:")
    print(f"✓ Full Success: {success}/{total} ({success/total*100:.1f}%)")
    print(f"⚠ Partial Success: {partial}/{total} ({partial/total*100:.1f}%)")
    print(f"✗ Complete Failure: {total-success-partial}/{total} ({(total-success-partial)/total*100:.1f}%)")
    print(f"✓ Price Extraction Success: {price_success}/{success} successful scrapes ({price_success/max(success,1)*100:.1f}%)")
    print("="*50)
    
    return success > 0 and price_success > 0

# Check if Rainforest API is configured
def check_api_setup():
    """Check if Rainforest API is set up properly."""
    rainforest_api_key = os.getenv("RAINFOREST_API_KEY")
    if rainforest_api_key:
        print("✅ Rainforest API key is configured. API data retrieval is available.")
    else:
        print("⚠️ Rainforest API key is not set. Falling back to stealth browser techniques.")
        print("👉 Get a free API key at: https://www.rainforestapi.com/")
        print("👉 Add to .env file as: RAINFOREST_API_KEY=your_api_key_here")

if __name__ == "__main__":
    load_dotenv()
    print("\n" + "="*50)
    print("🔍 TESTING E-COMMERCE DATA RETRIEVAL")
    print("   FOCUSING ON PRICE EXTRACTION")
    print("="*50 + "\n")
    
    check_api_setup()
    success = asyncio.run(test_stealth_scraping())
    
    if success:
        print("\n✅ Test completed successfully! Price extraction is working.")
    else:
        print("\n❌ Test completed with issues. Price extraction needs improvement.") 