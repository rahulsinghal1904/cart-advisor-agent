import re
import json
import logging
import httpx
import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PriceAPIFetcher:
    """
    Multi-source price fetcher that uses free APIs and web search with fallbacks.
    Implements a tiered approach to ensure high availability and reliable price fetching.
    """
    
    def __init__(self, cache_duration_minutes: int = 60):
        """Initialize the API fetcher with caching capability."""
        self.cache = {}  # Simple in-memory cache
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0"
        ]
        
        # Track API rate limits
        self.api_call_timestamps = {
            "serpapi": [],
            "rapidapi": [],
            "directwebsearch": []
        }
        
        logger.info("Initialized PriceAPIFetcher with multi-source strategy")
    
    async def get_product_details(self, url: str) -> Dict[str, Any]:
        """
        Main method to get product details from any supported website.
        Implements multi-tier strategy with caching and fallbacks.
        
        Args:
            url: Product URL
            
        Returns:
            Dict with product details including price
        """
        # Check cache first
        cache_key = url
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit for {url}")
            return cached_result
        
        # Parse domain to determine which fetcher to use
        domain = self._extract_domain(url)
        
        # First try domain-specific API approach
        result = None
        if "amazon" in domain:
            result = await self._get_amazon_product_data(url)
        elif "walmart" in domain:
            result = await self._get_walmart_product_data(url)
        elif "bestbuy" in domain:
            result = await self._get_bestbuy_product_data(url)
        elif "target" in domain:
            result = await self._get_target_product_data(url)
        elif "ebay" in domain:
            result = await self._get_ebay_product_data(url)
        
        # If domain-specific method failed or not implemented, try generic approach
        if not result or result.get("status") == "error":
            logger.info(f"Domain-specific fetcher failed for {domain}, trying generic web search approach")
            result = await self._get_product_data_from_web_search(url)
        
        # If everything failed, return error
        if not result:
            result = {
                "status": "error",
                "message": "All product data fetching methods failed",
                "url": url,
                "timestamp": datetime.now().isoformat()
            }
        elif result.get("status") == "success":
            # Cache successful results
            self._add_to_cache(cache_key, result)
        
        return result
    
    async def _get_amazon_product_data(self, url: str) -> Dict[str, Any]:
        """
        Get Amazon product data using multiple free API strategies.
        
        Args:
            url: Amazon product URL
            
        Returns:
            Dict with product data
        """
        asin = self._extract_asin_from_url(url)
        if not asin:
            logger.warning(f"Could not extract ASIN from Amazon URL: {url}")
            return {"status": "error", "message": "Invalid Amazon URL format"}
        
        # Try each method in sequence until one succeeds
        methods = [
            self._get_amazon_data_from_rainforest_free(asin),
            self._get_amazon_data_from_rapidapi(asin),
            self._get_amazon_data_from_keepa_api(asin),
            self._get_product_data_from_jsonscraper(url)
        ]
        
        for method in methods:
            try:
                result = await method
                if result and result.get("status") == "success" and result.get("price"):
                    logger.info(f"Successfully retrieved Amazon data for {asin}")
                    return result
            except Exception as e:
                logger.warning(f"Method for Amazon data failed: {str(e)}")
                continue
        
        # If all direct methods failed, fall back to web search
        return await self._get_product_data_from_web_search(url)
    
    async def _get_amazon_data_from_rainforest_free(self, asin: str) -> Dict[str, Any]:
        """Free tier alternative to Rainforest API using their limited free access."""
        # This is a simulated implementation - in practice Rainforest requires a paid API key
        try:
            # Since there's no truly free tier for Rainforest, we'll simulate it
            # In a real implementation, you would use the actual Rainforest free tier if available
            return {
                "status": "error",
                "message": "Rainforest free tier not available"
            }
        except Exception as e:
            logger.error(f"Error with Rainforest free tier: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _get_amazon_data_from_rapidapi(self, asin: str) -> Dict[str, Any]:
        """
        Get Amazon data using RapidAPI's free tier options.
        Note: Most of these have limited monthly requests on free plans.
        """
        # In a real implementation, you would sign up for a free tier RapidAPI key
        # For demonstration purposes, we're using a simulated response
        
        # Check rate limits before making a call
        if not self._can_make_api_call("rapidapi", max_calls_per_hour=10):
            return {"status": "error", "message": "RapidAPI rate limit exceeded"}
        
        try:
            # Simulated API call to RapidAPI's Amazon Data endpoint
            # In a real implementation, you would use httpx to make an actual API call
            
            # Record API call
            self._record_api_call("rapidapi")
            
            # This is a hardcoded successful response for demonstration
            return {
                "status": "error", 
                "message": "RapidAPI free tier limited - simulated endpoint"
            }
        except Exception as e:
            logger.error(f"Error with RapidAPI: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _get_amazon_data_from_keepa_api(self, asin: str) -> Dict[str, Any]:
        """
        Get Amazon data from Keepa API (limited free access).
        """
        # Keepa has some limited free requests after registration
        try:
            # Simulated response since we don't have a real Keepa API key
            return {
                "status": "error",
                "message": "Keepa API free tier not available"
            }
        except Exception as e:
            logger.error(f"Error with Keepa API: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _get_walmart_product_data(self, url: str) -> Dict[str, Any]:
        """
        Get Walmart product data using free APIs and data extraction.
        
        Args:
            url: Walmart product URL
            
        Returns:
            Dict with product data
        """
        # Extract product ID from URL if possible
        item_id = self._extract_item_id_from_walmart_url(url)
        if not item_id:
            logger.warning(f"Could not extract item ID from Walmart URL: {url}")
        
        # Try multiple methods in sequence
        methods = [
            self._get_walmart_data_from_jsonscraper(url),
            self._get_walmart_data_from_serp_api(url, item_id)
        ]
        
        for method in methods:
            try:
                result = await method
                if result and result.get("status") == "success" and result.get("price"):
                    logger.info(f"Successfully retrieved Walmart data for {url}")
                    return result
            except Exception as e:
                logger.warning(f"Method for Walmart data failed: {str(e)}")
                continue
        
        # If all direct methods failed, fall back to web search
        return await self._get_product_data_from_web_search(url)
    
    async def _get_walmart_data_from_jsonscraper(self, url: str) -> Dict[str, Any]:
        """Extract data directly from Walmart page JSON data."""
        try:
            async with httpx.AsyncClient() as client:
                user_agent = random.choice(self.user_agents)
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
                
                response = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
                if response.status_code != 200:
                    return {"status": "error", "message": f"HTTP error: {response.status_code}"}
                
                html_content = response.text
                
                # Extract JSON data embedded in the page
                json_match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*(\{.+?\});', html_content)
                if json_match:
                    try:
                        json_data = json.loads(json_match.group(1))
                        
                        # Navigate through the Walmart JSON structure to find product data
                        if 'product' in json_data and 'products' in json_data['product']:
                            product = json_data['product']['products'][0]
                            
                            # Extract basic product information
                            title = product.get('name', 'Unknown Product')
                            
                            # Extract price information
                            price = None
                            price_text = None
                            if 'priceInfo' in product:
                                price_info = product['priceInfo']
                                if 'currentPrice' in price_info:
                                    price = float(price_info['currentPrice'].get('price', 0))
                                    price_text = f"${price}"
                            
                            # Extract other details
                            image_url = None
                            if 'imageInfo' in product and 'thumbnailUrl' in product['imageInfo']:
                                image_url = product['imageInfo']['thumbnailUrl']
                            
                            # Check if price was found
                            if price is not None:
                                return {
                                    "status": "success",
                                    "source": "walmart",
                                    "url": url,
                                    "title": title,
                                    "price": price,
                                    "price_text": price_text,
                                    "image_url": image_url,
                                    "data_source": "json_scraper"
                                }
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse Walmart JSON data")
                
                # If we're here, we couldn't extract data from JSON
                return {"status": "error", "message": "Could not extract data from Walmart page"}
                
        except Exception as e:
            logger.error(f"Error in Walmart JSON scraper: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _get_walmart_data_from_serp_api(self, url: str, item_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Walmart data using SerpAPI's free tier (or simulated).
        """
        # Check rate limits
        if not self._can_make_api_call("serpapi", max_calls_per_hour=5):
            return {"status": "error", "message": "SerpAPI rate limit exceeded"}
        
        # In practice, you would need a SerpAPI key (they have a free tier with limited requests)
        # For this example, we'll simulate the response
        self._record_api_call("serpapi")
        
        return {
            "status": "error",
            "message": "SerpAPI free tier limited - simulated endpoint"
        }
    
    async def _get_bestbuy_product_data(self, url: str) -> Dict[str, Any]:
        """
        Get Best Buy product data using free APIs and data extraction.
        
        Args:
            url: Best Buy product URL
            
        Returns:
            Dict with product data
        """
        # Extract SKU from URL
        sku = self._extract_sku_from_bestbuy_url(url)
        if not sku:
            logger.warning(f"Could not extract SKU from Best Buy URL: {url}")
        
        # Try multiple methods in sequence
        methods = [
            self._get_bestbuy_data_from_jsonscraper(url),
            self._get_product_data_from_web_search(url)
        ]
        
        for method in methods:
            try:
                result = await method
                if result and result.get("status") == "success" and result.get("price"):
                    logger.info(f"Successfully retrieved Best Buy data for {url}")
                    return result
            except Exception as e:
                logger.warning(f"Method for Best Buy data failed: {str(e)}")
                continue
        
        # If all methods failed, return error
        return {"status": "error", "message": "All Best Buy data fetching methods failed"}
    
    async def _get_bestbuy_data_from_jsonscraper(self, url: str) -> Dict[str, Any]:
        """Extract data directly from Best Buy page JSON data."""
        try:
            async with httpx.AsyncClient() as client:
                user_agent = random.choice(self.user_agents)
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
                
                response = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
                if response.status_code != 200:
                    return {"status": "error", "message": f"HTTP error: {response.status_code}"}
                
                html_content = response.text
                
                # Try to extract product data from schema.org markup
                soup = BeautifulSoup(html_content, 'html.parser')
                schema_scripts = soup.find_all('script', type='application/ld+json')
                
                for script in schema_scripts:
                    try:
                        json_data = json.loads(script.string)
                        
                        # Check if this is product data
                        if '@type' in json_data and json_data['@type'] == 'Product':
                            # Extract basic product information
                            title = json_data.get('name', 'Unknown Product')
                            
                            # Extract price information
                            price = None
                            price_text = None
                            if 'offers' in json_data:
                                offers = json_data['offers']
                                if isinstance(offers, dict):
                                    price_text = offers.get('price')
                                    if price_text:
                                        try:
                                            price = float(price_text)
                                            price_text = f"${price}"
                                        except ValueError:
                                            pass
                                elif isinstance(offers, list) and len(offers) > 0:
                                    price_text = offers[0].get('price')
                                    if price_text:
                                        try:
                                            price = float(price_text)
                                            price_text = f"${price}"
                                        except ValueError:
                                            pass
                            
                            # Extract image URL
                            image_url = json_data.get('image', None)
                            
                            # Check if price was found
                            if price is not None:
                                return {
                                    "status": "success",
                                    "source": "bestbuy",
                                    "url": url,
                                    "title": title,
                                    "price": price,
                                    "price_text": price_text,
                                    "image_url": image_url,
                                    "data_source": "json_scraper"
                                }
                    except json.JSONDecodeError:
                        continue
                
                # If JSON-LD didn't work, try a different approach
                # Look for specific Best Buy price patterns in the HTML
                price_pattern = re.compile(r'"currentPrice":(\d+\.\d+)')
                match = price_pattern.search(html_content)
                
                if match:
                    price = float(match.group(1))
                    
                    # Try to find the title
                    title_elem = soup.find('h1')
                    title = title_elem.text.strip() if title_elem else 'Unknown Product'
                    
                    # Try to find an image
                    image_elem = soup.find('img', {'class': 'primary-image'})
                    image_url = image_elem.get('src') if image_elem else None
                    
                    return {
                        "status": "success",
                        "source": "bestbuy",
                        "url": url,
                        "title": title,
                        "price": price,
                        "price_text": f"${price}",
                        "image_url": image_url,
                        "data_source": "html_pattern"
                    }
                
                # If we're here, we couldn't extract data
                return {"status": "error", "message": "Could not extract data from Best Buy page"}
                
        except Exception as e:
            logger.error(f"Error in Best Buy JSON scraper: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _get_target_product_data(self, url: str) -> Dict[str, Any]:
        """Get Target product data."""
        # Target doesn't have an easily accessible free API
        # Fallback to JSON scraper or web search
        try:
            result = await self._get_product_data_from_jsonscraper(url)
            if result and result.get("status") == "success" and result.get("price"):
                return result
        except Exception as e:
            logger.warning(f"JSON scraper for Target failed: {str(e)}")
        
        # Fallback to web search
        return await self._get_product_data_from_web_search(url)
    
    async def _get_ebay_product_data(self, url: str) -> Dict[str, Any]:
        """Get eBay product data."""
        # eBay requires a registered API key, even for free tier
        # Fallback to JSON scraper or web search
        try:
            result = await self._get_product_data_from_jsonscraper(url)
            if result and result.get("status") == "success" and result.get("price"):
                return result
        except Exception as e:
            logger.warning(f"JSON scraper for eBay failed: {str(e)}")
        
        # Fallback to web search
        return await self._get_product_data_from_web_search(url)
    
    async def _get_product_data_from_jsonscraper(self, url: str) -> Dict[str, Any]:
        """
        Generic method to extract product data from structured JSON in web pages.
        Looks for Schema.org and other common data structures.
        """
        try:
            async with httpx.AsyncClient() as client:
                user_agent = random.choice(self.user_agents)
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
                
                response = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
                if response.status_code != 200:
                    return {"status": "error", "message": f"HTTP error: {response.status_code}"}
                
                html_content = response.text
                
                # Parse the HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Try to extract product data from schema.org markup
                schema_scripts = soup.find_all('script', type='application/ld+json')
                
                for script in schema_scripts:
                    try:
                        json_data = json.loads(script.string)
                        
                        # Handle array of objects
                        if isinstance(json_data, list):
                            for item in json_data:
                                if item.get('@type') == 'Product':
                                    json_data = item
                                    break
                        
                        # Check if this is product data
                        if '@type' in json_data and json_data['@type'] == 'Product':
                            # Extract basic product information
                            title = json_data.get('name', 'Unknown Product')
                            
                            # Extract price information
                            price = None
                            price_text = None
                            if 'offers' in json_data:
                                offers = json_data['offers']
                                if isinstance(offers, dict):
                                    price_text = offers.get('price')
                                    if price_text:
                                        try:
                                            price = float(price_text)
                                            price_text = f"${price}"
                                        except ValueError:
                                            pass
                                elif isinstance(offers, list) and len(offers) > 0:
                                    price_text = offers[0].get('price')
                                    if price_text:
                                        try:
                                            price = float(price_text)
                                            price_text = f"${price}"
                                        except ValueError:
                                            pass
                            
                            # Extract image URL
                            image_url = json_data.get('image', None)
                            if isinstance(image_url, list) and len(image_url) > 0:
                                image_url = image_url[0]
                            
                            # Extract other information that might be useful
                            brand = json_data.get('brand', {}).get('name') if isinstance(json_data.get('brand'), dict) else json_data.get('brand')
                            
                            # Check if price was found
                            if price is not None:
                                # Parse domain for source
                                domain = self._extract_domain(url)
                                source = domain.split('.')[0] if domain else 'unknown'
                                
                                return {
                                    "status": "success",
                                    "source": source,
                                    "url": url,
                                    "title": title,
                                    "price": price,
                                    "price_text": price_text,
                                    "image_url": image_url,
                                    "brand": brand,
                                    "data_source": "json_scraper"
                                }
                    except json.JSONDecodeError:
                        continue
                
                # If schema.org didn't work, try other patterns
                # Generic price pattern that works for many sites
                price_pattern = re.compile(r'"price"[:\s]+(\d+\.?\d*)')
                match = price_pattern.search(html_content)
                
                if match:
                    price = float(match.group(1))
                    
                    # Try to find the title
                    title_elem = soup.find('h1')
                    title = title_elem.text.strip() if title_elem else 'Unknown Product'
                    
                    # Try to find an image
                    image_elem = soup.find('img', {'id': 'landingImage'}) or soup.find('img', {'id': 'main-image'})
                    image_url = image_elem.get('src') if image_elem else None
                    
                    # Parse domain for source
                    domain = self._extract_domain(url)
                    source = domain.split('.')[0] if domain else 'unknown'
                    
                    return {
                        "status": "success",
                        "source": source,
                        "url": url,
                        "title": title,
                        "price": price,
                        "price_text": f"${price}",
                        "image_url": image_url,
                        "data_source": "html_pattern"
                    }
                
                # If we're here, we couldn't extract data
                return {"status": "error", "message": "Could not extract data from page"}
                
        except Exception as e:
            logger.error(f"Error in generic JSON scraper: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _get_product_data_from_web_search(self, url: str) -> Dict[str, Any]:
        """
        Fallback method to get product data using web search.
        Extracts product information when other methods fail.
        
        Args:
            url: Product URL
            
        Returns:
            Dict with product data or error
        """
        # Check rate limits
        if not self._can_make_api_call("directwebsearch", max_calls_per_hour=20):
            return {"status": "error", "message": "Web search rate limit exceeded"}
        
        try:
            # Extract product name from URL for search
            parsed_url = urlparse(url)
            path_segments = parsed_url.path.split('/')
            
            # Try to extract a usable search term from the URL
            search_term = None
            for segment in path_segments:
                if segment and len(segment) > 3 and not segment.isdigit():
                    search_term = segment.replace('-', ' ').replace('_', ' ')
                    break
            
            if not search_term:
                return {"status": "error", "message": "Couldn't extract search term from URL"}
            
            # CRITICAL FIX: Always use proper source identification
            domain = self._extract_domain(url)
            source = "unknown"
            if "amazon" in domain or "amazon" in url.lower():
                source = "amazon"
            elif "walmart" in domain:
                source = "walmart"
            elif "bestbuy" in domain:
                source = "bestbuy"
            elif "target" in domain:
                source = "target"
            elif "ebay" in domain:
                source = "ebay"
            elif "costco" in domain:
                source = "costco"
                
            logger.info(f"Web search source identification: URL={url}, Domain={domain}, Identified Source={source}")
            
            # Record API call
            self._record_api_call("directwebsearch")
            
            # For web search, return product info based on URL without price estimation
            title = search_term.replace(' price', '').replace(source, '').strip().title()
            
            return {
                "status": "success",
                "source": source,  # Use properly identified source
                "url": url,
                "title": title,  # Capitalize words
                "price": None,  # No price data available
                "price_text": "Price unavailable",
                "rating": None,
                "availability": None,
                "data_source": "web_search"
            }
                
        except Exception as e:
            logger.error(f"Error in web search data fetcher: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # CRITICAL FIX: Identify common e-commerce domains more robustly
            if "amazon" in domain:
                return "amazon"
            elif "walmart" in domain:
                return "walmart"
            elif "bestbuy" in domain:
                return "bestbuy"
            elif "target" in domain:
                return "target"
            elif "ebay" in domain:
                return "ebay"
            elif "costco" in domain:
                return "costco"
                
            return domain
        except Exception:
            return "unknown"
    
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
    
    def _extract_item_id_from_walmart_url(self, url: str) -> Optional[str]:
        """Extract item ID from Walmart URL."""
        # Try to find item ID in the path
        match = re.search(r'/ip/(?:.*?)/(\d+)', url)
        if match:
            return match.group(1)
        
        # Try query parameters
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        if 'itemId' in query_params:
            return query_params['itemId'][0]
        
        return None
    
    def _extract_sku_from_bestbuy_url(self, url: str) -> Optional[str]:
        """Extract SKU from Best Buy URL."""
        match = re.search(r'/(?:site|shop)/(?:.*?)/(\d+)(?:\.p)?', url)
        if match:
            return match.group(1)
        
        return None
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if it exists and is not expired."""
        if key in self.cache:
            timestamp, data = self.cache[key]
            if datetime.now() - timestamp < self.cache_duration:
                return data
            else:
                # Remove expired entry
                del self.cache[key]
        return None
    
    def _add_to_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Add data to cache with current timestamp."""
        self.cache[key] = (datetime.now(), data)
    
    def _can_make_api_call(self, api_name: str, max_calls_per_hour: int) -> bool:
        """Check if we can make an API call based on rate limits."""
        now = time.time()
        timestamps = self.api_call_timestamps.get(api_name, [])
        
        # Remove timestamps older than 1 hour
        timestamps = [ts for ts in timestamps if now - ts < 3600]
        self.api_call_timestamps[api_name] = timestamps
        
        # Check if we're under the limit
        return len(timestamps) < max_calls_per_hour
    
    def _record_api_call(self, api_name: str) -> None:
        """Record an API call for rate limiting."""
        now = time.time()
        self.api_call_timestamps.setdefault(api_name, []).append(now)
    
    def _generate_mock_price(self) -> float:
        """Disabled method - no price generation."""
        logger.error("Mock price generation function called but is disabled")
        return None
    
    def cleanup(self):
        """Clean up resources."""
        self.cache.clear()
        logger.info("PriceAPIFetcher resources cleaned up") 