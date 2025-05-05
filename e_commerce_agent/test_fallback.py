#!/usr/bin/env python3

import asyncio
import logging
from src.e_commerce_agent.providers.price_provider import PriceProvider
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_price_fallback_mechanism():
    """Test the fallback mechanism when Amazon price fetching fails."""
    price_provider = PriceProvider()
    
    # Example URLs to test
    amazon_url = "https://www.amazon.com/Apple-MacBook-Laptop-16GB-512GB/dp/B0CHX3QBCH/"
    
    try:
        logger.info(f"Testing product details fetching with simulated price failure for: {amazon_url}")
        
        # Get product details
        product_details = await price_provider.get_product_details(amazon_url)
        
        # Simulate price data missing
        logger.info("Simulating price data missing...")
        if product_details.get("status") == "success":
            # Remove price data but keep other components
            product_details["price"] = None
            product_details["price_text"] = "Price unavailable"
            logger.info("Price data has been removed to simulate fetching failure")
        
        logger.info("Product details with missing price:")
        pprint(product_details)
        
        # Find alternatives
        logger.info("Finding alternatives...")
        alternatives = await price_provider.find_alternatives(product_details)
        logger.info(f"Found {len(alternatives)} alternatives")
        logger.info("Alternative details:")
        pprint(alternatives)
        
        # Analyze deal using non-price data
        logger.info("Analyzing deal with missing price data...")
        deal_analysis = await price_provider.analyze_deal(product_details, alternatives)
        logger.info("Deal analysis result:")
        pprint(deal_analysis)
        
        # Check if the verdict uses non-price factors
        verdict = deal_analysis.get("verdict", "")
        reasons = deal_analysis.get("reasons", [])
        
        if "price" in verdict.lower():
            logger.warning("Verdict still mentions price despite price data missing!")
        else:
            logger.info("Verdict correctly doesn't mention price when price data is missing")
        
        # Check if holistic score was calculated without price
        holistic_score = deal_analysis.get("holistic_score", 0)
        logger.info(f"Holistic score without price: {holistic_score}")
        
        # Check if non-price factors were mentioned in reasons
        non_price_factors = ["rating", "review", "availability", "reputation"]
        non_price_mentions = sum(1 for reason in reasons for factor in non_price_factors if factor in reason.lower())
        logger.info(f"Number of non-price factor mentions in reasons: {non_price_mentions}")
        
        logger.info("Test completed successfully")
        return deal_analysis
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        return None
    finally:
        # Clean up resources
        price_provider.cleanup()

if __name__ == "__main__":
    asyncio.run(test_price_fallback_mechanism())
