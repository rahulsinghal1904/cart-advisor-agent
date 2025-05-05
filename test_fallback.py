#!/usr/bin/env python
"""
Simple test script for the Target and Best Buy fallback mechanisms.
"""
import asyncio
import logging
import sys
import json
from urllib.parse import urlparse
import re

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

def create_basic_target_result(url):
    """Create a minimal working result for Target URLs."""
    # Extract product name from URL
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Extract ID
    item_id = None
    id_match = re.search(r'A-(\d+)', path)
    if id_match:
        item_id = id_match.group(1)
        
    # Try to extract product name
    product_name = "Target Product"
    name_parts = path.split('/')
    for part in name_parts:
        if part and part != '-' and not part.startswith('A-') and len(part) > 5:
            product_name = part.replace('-', ' ').title()
            break
    
    # Add item ID to title if available
    if item_id:
        product_name = f"{product_name} (ID: {item_id})"
        
    logger.info(f"Created basic Target result with title: {product_name}")
    
    return {
        "status": "success",
        "source": "target",
        "url": url,
        "title": product_name,
        "price": None,
        "price_text": "Price information unavailable",
        "rating": "No ratings available",
        "availability": "Unknown",
        "item_id": item_id
    }

async def main():
    """Test the fallback mechanism directly."""
    target_url = "https://www.target.com/p/kitsch-queen-size-thread-count-34-600-34-satin-standard-pillowcase-ivory/-/A-91792291"
    
    logger.info(f"Testing fallback for Target URL: {target_url}")
    
    # Use the fallback
    result = create_basic_target_result(target_url)
    
    # Print the result
    logger.info(f"Fallback result for Target:")
    logger.info(f"Title: {result.get('title')}")
    logger.info(f"Price: {result.get('price')}")
    logger.info(f"Price Text: {result.get('price_text')}")
    logger.info(f"Result: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main()) 