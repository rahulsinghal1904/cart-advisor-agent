"""
Simple price provider implementation that uses the simplified scraper.
This is a direct solution to replace the problematic PriceScraper implementation.
"""
import logging
import re
import json
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .simple_scraper import SimpleScraper
import secrets

logger = logging.getLogger(__name__)

class MinimalStealthScraper:
    """
    Minimal implementation of StealthScraper for Amazon products.
    This avoids dependency on the broken price_scraper.py file.
    """
    
    def __init__(self):
        """Initialize the minimal stealth scraper."""
        # User agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ]
        
        logger.info("Initialized MinimalStealthScraper")
    
    async def get_amazon_product_data(self, url: str) -> Dict[str, Any]:
        """
        Get Amazon product data using a simplified approach.
        
        Args:
            url: Amazon product URL
            
        Returns:
            Dict containing product data
        """
        logger.info(f"Fetching Amazon product data for: {url}")
        
        # Extract ASIN from URL
        asin = self._extract_asin_from_url(url)
        if not asin:
            logger.warning(f"Could not extract ASIN from URL: {url}")
            asin = "unknown"
        
        # Try HTTP request approach first
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                headers = {
                    "User-Agent": secrets.choice(self.user_agents),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5"
                }
                
                logger.info(f"Making HTTP request to: {url}")
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    # Extract basic product details from the HTML
                    title = self._extract_title_from_response(response.text)
                    # Extract price (simplified approach)
                    price_data = self._extract_price_from_response(response.text)
                    
                    logger.info(f"Extracted title: {title}")
                    logger.info(f"Extracted price: {price_data}")
                    
                    return {
                        "status": "success",
                        "source": "amazon",
                        "url": url,
                        "title": title or "Unknown Amazon Product",
                        "price": price_data.get("price"),
                        "price_text": price_data.get("price_text", "Price not available"),
                        "rating": "No ratings",
                        "availability": "Unknown",
                        "extracted_method": "minimal_stealth",
                        "asin": asin
                    }
                else:
                    logger.error(f"HTTP request failed with status: {response.status_code}")
        except Exception as e:
            logger.error(f"Error during HTTP request: {str(e)}")
        
        # Fallback to basic info
        title = self._extract_title_from_url(url)
        return {
            "status": "success",
            "source": "amazon",
            "url": url,
            "title": title or "Unknown Amazon Product",
            "price": None,
            "price_text": "Price not available",
            "rating": "No ratings",
            "availability": "Unknown",
            "extracted_method": "minimal_fallback",
            "asin": asin
        }
    
    def _extract_asin_from_url(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL."""
        patterns = [
            r'/dp/([A-Z0-9]{10})/?',
            r'/gp/product/([A-Z0-9]{10})/?',
            r'/ASIN/([A-Z0-9]{10})/?',
            r'/product/([A-Z0-9]{10})/?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a reasonable product title from the URL."""
        try:
            # Extract from path
            path = urlparse(url).path
            
            # Remove file extensions and trailing slashes
            path = re.sub(r'\.\w+$', '', path).rstrip('/')
            
            # Split by slashes and get the last meaningful segment
            segments = [s for s in path.split('/') if s and len(s) > 1]
            
            if segments:
                # Try to find a segment that looks like a product title
                # Usually it's the last segment before query parameters
                # But not the ASIN segment
                for segment in segments:
                    if len(segment) > 5 and not re.match(r'^[A-Z0-9]{10}$', segment):
                        # Replace hyphens and underscores with spaces
                        title = re.sub(r'[-_]', ' ', segment)
                        
                        # Capitalize words
                        title = ' '.join(word.capitalize() for word in title.split())
                        
                        return title
            
            # Ultimate fallback
            return "Unknown Amazon Product"
        except Exception as e:
            logger.error(f"Error extracting title from URL: {str(e)}")
            return "Unknown Amazon Product"
    
    def _extract_title_from_response(self, html_content: str) -> Optional[str]:
        """Extract title from HTML content."""
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content)
        if title_match:
            title = title_match.group(1).strip()
            # Remove "Amazon.com:" prefix if present
            title = re.sub(r'^Amazon\.com:\s*', '', title)
            return title
        
        # Try product title specific patterns
        product_title_match = re.search(r'id="productTitle"[^>]*>([^<]+)</span>', html_content)
        if product_title_match:
            return product_title_match.group(1).strip()
        
        return None
    
    def _extract_price_from_response(self, html_content: str) -> Dict[str, Any]:
        """Extract price from HTML content."""
        result = {"price": None, "price_text": None}
        
        # Try to extract from JSON-LD data
        json_ld_match = re.search(r'<script type="application/ld\+json">(.+?)</script>', html_content, re.DOTALL)
        if json_ld_match:
            try:
                json_data = json.loads(json_ld_match.group(1))
                if isinstance(json_data, dict):
                    if "offers" in json_data:
                        offers = json_data["offers"]
                        if isinstance(offers, dict) and "price" in offers:
                            price = float(offers["price"])
                            result["price"] = price
                            result["price_text"] = f"${price}"
                            return result
            except Exception as e:
                logger.warning(f"Error parsing JSON-LD: {str(e)}")
        
        # Try direct price patterns
        price_patterns = [
            r'<span class="a-offscreen">(\$[\d,\.]+)</span>',
            r'id="priceblock_ourprice"[^>]*>(\$[\d,\.]+)</span>',
            r'id="priceblock_dealprice"[^>]*>(\$[\d,\.]+)</span>',
            r'"price":\s*"(\$[\d,\.]+)"',
            r'class="a-color-price"[^>]*>(\$[\d,\.]+)</span>'
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, html_content)
            if price_match:
                price_text = price_match.group(1)
                # Extract numeric price
                price_value_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                if price_value_match:
                    price_str = price_value_match.group(1).replace(',', '')
                    try:
                        price = float(price_str)
                        result["price"] = price
                        result["price_text"] = price_text
                        return result
                    except ValueError:
                        pass
        
        return result


class SimplePriceProvider:
    """
    Simplified price provider that determines which scraper to use based on retailer.
    Uses MinimalStealthScraper for Amazon and SimpleScraper for Target and Best Buy.
    """
    
    def __init__(self):
        """Initialize the simple price provider."""
        # Amazon specialized scraper
        self.stealth_scraper = MinimalStealthScraper()
        
        # Simple scraper for other retailers
        self.simple_scraper = SimpleScraper()
        
        logger.info("Initialized SimplePriceProvider with specialized scrapers")
    
    async def get_product_details(self, url: str) -> Dict[str, Any]:
        """
        Fetch product details from the given URL using the appropriate scraper.
        
        Args:
            url: Product URL (Amazon, Target, Best Buy, etc.)
            
        Returns:
            Dict containing product details
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Determine the source retailer
        source = "unknown"
        if "amazon" in domain or "amazon" in url.lower() or "a.co" in domain:
            source = "amazon"
        elif "target" in domain or "target.com" in url.lower():
            source = "target"
        elif "bestbuy" in domain or "best-buy" in url.lower() or "bestbuy" in url.lower():
            source = "bestbuy"
        
        logger.info(f"Determined source as {source} for URL: {url}")
        
        try:
            # Use the appropriate scraper based on source
            if source == "amazon":
                # Amazon uses MinimalStealthScraper
                result = await self.stealth_scraper.get_amazon_product_data(url)
                
                # Ensure source is properly set
                if result and result.get("status") == "success":
                    result["source"] = "amazon"
                
                return result
            elif source == "target":
                # Target uses the simplified scraper
                return await self.simple_scraper.scrape_target(url)
            elif source == "bestbuy":
                # Best Buy uses the simplified scraper
                return await self.simple_scraper.scrape_bestbuy(url)
            else:
                # For unknown sources, return an error
                return {
                    "status": "error",
                    "message": f"Unsupported retailer: {domain}",
                    "source": source,
                    "url": url
                }
        except Exception as e:
            logger.error(f"Error fetching product details: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get product details: {str(e)}",
                "source": source,
                "url": url
            } 
