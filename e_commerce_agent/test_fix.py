import asyncio
import logging
import sys
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

async def test_amazon_product():
    """Test fetching Amazon product information and alternatives."""
    provider = PriceProvider()
    
    # New Balance shoe URL (the example that failed before)
    url = "https://www.amazon.com/New-Balance-Casual-Comfort-Trainer/dp/B07B421VFD"
    
    try:
        # Get product details
        logger.info(f"Fetching product details for: {url}")
        product_details = await provider.get_product_details(url)
        
        # Log the details
        logger.info("Product Details:")
        logger.info(f"Title: {product_details.get('title')}")
        logger.info(f"Price: {product_details.get('price')}")
        logger.info(f"Price Text: {product_details.get('price_text')}")
        logger.info(f"Source: {product_details.get('source')}")
        logger.info(f"Rating: {product_details.get('rating')}")
        logger.info(f"Availability: {product_details.get('availability')}")
        
        # Get alternatives
        logger.info("Searching for alternatives...")
        alternatives = await provider.find_alternatives(product_details)
        
        # Log alternatives
        logger.info(f"Found {len(alternatives)} alternatives:")
        for i, alt in enumerate(alternatives):
            logger.info(f"Alternative {i+1}:")
            logger.info(f"  Title: {alt.get('title')}")
            logger.info(f"  Price: {alt.get('price')}")
            logger.info(f"  Source: {alt.get('source')}")
            logger.info(f"  Is Better Deal: {alt.get('is_better_deal')}")
            logger.info(f"  Reason: {alt.get('reason')}")
        
        # Analyze deal
        logger.info("Analyzing deal...")
        deal_analysis = await provider.analyze_deal(product_details, alternatives)
        
        # Log analysis
        logger.info("Deal Analysis:")
        logger.info(f"Is Good Deal: {deal_analysis.get('is_good_deal')}")
        logger.info(f"Verdict: {deal_analysis.get('verdict')}")
        logger.info(f"Confidence: {deal_analysis.get('confidence')}")
        logger.info("Reasons:")
        for reason in deal_analysis.get('reasons', []):
            logger.info(f"  {reason}")
            
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up resources
        provider.cleanup()

if __name__ == "__main__":
    asyncio.run(test_amazon_product()) 