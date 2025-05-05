import logging
import asyncio
from typing import Dict, List, Any, Optional
from .price_api_fetcher import PriceAPIFetcher
from .price_scraper import PriceScraper, StealthScraper
from .alternative_finder import AlternativeFinder
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PriceProvider:
    """
    Unified price provider that integrates multiple strategies for fetching product prices.
    Implements cascading fallbacks to ensure high availability and service reliability.
    """
    
    def __init__(self):
        """Initialize the price provider with multiple data sources."""
        # Primary API-based fetcher (prioritize this for better performance and reliability)
        self.api_fetcher = PriceAPIFetcher(cache_duration_minutes=60)
        
        # Fallback to existing scrapers when APIs fail
        self.scraper = PriceScraper()
        self.stealth_scraper = StealthScraper()
        
        # Initialize the new alternative finder
        self.alternative_finder = AlternativeFinder(self.scraper)
        
        # Track success/failure rates for adaptive sourcing
        self.source_stats = {
            "api": {"success": 0, "failure": 0},
            "scraper": {"success": 0, "failure": 0},
            "stealth": {"success": 0, "failure": 0}
        }
        
        logger.info("Initialized PriceProvider with multi-tier strategy and fallbacks")
    
    async def get_product_details(self, url: str) -> Dict[str, Any]:
        """
        Get product details using a multi-source approach that combines data.
        
        Strategy:
        1. Try all available data sources 
        2. Combine their data to create the most complete product information
        3. Fill in missing pieces from each source
        
        Args:
            url: Product URL
            
        Returns:
            Dict with product details including price
        """
        domain = self._extract_domain(url)
        logger.info(f"Fetching product details for {url} from {domain}")
        
        # For Amazon, prioritize stealth scraper (it works best)
        if domain == "amazon":
            sources = [
                ("stealth", self._get_product_from_stealth_scraper),
                ("scraper", self._get_product_from_scraper),
                ("api", self._get_product_from_api),
            ]
        else:
            # For other sites, try standard scraper first
            sources = [
                ("scraper", self._get_product_from_scraper),
                ("api", self._get_product_from_api),
                ("stealth", self._get_product_from_stealth_scraper)
            ]
        
        # Try ALL sources and collect results
        results = []
        error_messages = []
        
        for source_name, source_func in sources:
            try:
                logger.info(f"Trying {source_name} for {url}")
                result = await source_func(url)
                
                if result and result.get("status") == "success":
                    # Record success
                    self._record_success(source_name)
                    result["provider"] = source_name
                    results.append(result)
                    logger.info(f"Got successful result from {source_name}")
                else:
                    # Record failure
                    self._record_failure(source_name)
                    if result and result.get("message"):
                        error_messages.append(f"{source_name}: {result.get('message')}")
                    else:
                        error_messages.append(f"{source_name}: Unknown error")
            except Exception as e:
                # Record failure
                self._record_failure(source_name)
                error_messages.append(f"{source_name}: {str(e)}")
                logger.error(f"Error with {source_name} for {url}: {str(e)}")
        
        # If we have at least one successful result, merge them
        if results:
            # Create a merged result starting with the first result
            merged_result = results[0].copy()
            
            # CRITICAL FIX: Ensure source is properly set for Amazon
            if domain == "amazon" and merged_result.get("source", "").lower() in ["www", "unknown"]:
                logger.info(f"Fixing source from '{merged_result.get('source')}' to 'amazon'")
                merged_result["source"] = "amazon"
            
            # Track which fields we've combined
            combined_fields = ["provider"]
            merged_result["provider"] = "combined"
            
            # Add data sources used
            merged_result["data_sources_used"] = [r.get("provider", "unknown") for r in results]
            
            # Merge data from all results, prioritizing non-null values
            for result in results[1:]:
                for key, value in result.items():
                    # Skip status, provider, and already combined fields
                    if key in ["status", "provider"] or key in combined_fields:
                        continue
                    
                    # For price data, take the first non-null value (results are already ordered by priority)
                    if key == "price" and value is not None and merged_result.get("price") is None:
                        merged_result["price"] = value
                        merged_result["price_text"] = result.get("price_text", f"${value}")
                        combined_fields.extend(["price", "price_text"])
                        logger.info(f"Added price {value} from {result.get('provider')}")
                    
                    # For rating data, take the first available ratings
                    elif key == "rating" and value is not None and (
                        merged_result.get("rating") is None or 
                        merged_result.get("rating", "").lower() in ["no ratings", "none"]
                    ):
                        merged_result["rating"] = value
                        combined_fields.append("rating")
                        logger.info(f"Added rating {value} from {result.get('provider')}")
                    
                    # For availability data, take the first available data
                    elif key == "availability" and value is not None and (
                        merged_result.get("availability") is None or
                        merged_result.get("availability", "").lower() in ["unknown", "none"]
                    ):
                        merged_result["availability"] = value
                        combined_fields.append("availability")
                        logger.info(f"Added availability {value} from {result.get('provider')}")
                    
                    # For other missing data, fill it in
                    elif merged_result.get(key) is None and value is not None:
                        merged_result[key] = value
                        combined_fields.append(key)
                        logger.info(f"Added {key} from {result.get('provider')}")
            
            # If we still don't have a title, extract it from URL
            if not merged_result.get("title"):
                merged_result["title"] = self._extract_title_from_url(url)
                
            # Last chance to extract price from price_text if we still don't have it
            if merged_result.get("price") is None and merged_result.get("price_text"):
                try:
                    price_text = merged_result.get("price_text")
                    price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                    if price_match:
                        price_str = price_match.group(1).replace(',', '')
                        price = float(price_str)
                        # Add it to the result with sanity check
                        if 1 <= price <= 10000:  # Basic sanity check
                            merged_result["price"] = price
                            logger.info(f"Extracted price ${price} from price_text")
                except Exception as e:
                    logger.error(f"Failed to extract price from price_text: {e}")
            
            # CRITICAL FIX: If we still don't have a price, try a direct browser scrape as last resort
            if merged_result.get("price") is None:
                try:
                    logger.info("Price still missing - trying direct browser scrape as last resort")
                    direct_price = await self._try_direct_browser_scrape(url)
                    if direct_price and direct_price > 0:
                        merged_result["price"] = direct_price
                        merged_result["price_text"] = f"${direct_price:.2f}"
                        logger.info(f"Successfully extracted price ${direct_price} using direct browser scrape")
                except Exception as e:
                    logger.error(f"Error in direct browser scrape: {str(e)}")
            
            return merged_result
        
        # If we're here, all methods failed
        error_details = " | ".join(error_messages)
        logger.warning(f"All methods failed for {url}: {error_details}")
        
        # Return a helpful error response
        return {
            "status": "error",
            "message": "Failed to fetch product details using all available methods",
            "url": url,
            "error_details": error_details,
            "provider": "none"
        }
    
    async def _get_product_from_api(self, url: str) -> Dict[str, Any]:
        """Fetch product details using the API approach."""
        return await self.api_fetcher.get_product_details(url)
    
    async def _get_product_from_scraper(self, url: str) -> Dict[str, Any]:
        """Fetch product details using the standard scraper."""
        domain = self._extract_domain(url)
        
        if "amazon" in domain:
            # Use stealth scraper for Amazon directly
            return await self._get_product_from_stealth_scraper(url)
        elif "target" in domain:
            # Target implementation would go here
            return await self.scraper.scrape_target(url)
        elif "bestbuy" in domain:
            return await self.scraper.scrape_bestbuy(url)
        else:
            # Generic case - still use standard scraper but expect it to fail
            # This is a placeholder for potential future domain-specific handlers
            logger.warning(f"No specific scraper for domain {domain}, likely to fail")
            return {"status": "error", "message": f"No scraper implementation for {domain}"}
    
    async def _get_product_from_stealth_scraper(self, url: str) -> Dict[str, Any]:
        """Fetch product details using the stealth scraper approach."""
        domain = self._extract_domain(url)
        
        if "amazon" in domain:
            return await self.stealth_scraper.get_amazon_product_data(url)
        else:
            # Stealth scraper is primarily for Amazon, but we could extend it
            logger.warning(f"Stealth scraper not optimized for {domain}")
            return {"status": "error", "message": f"Stealth scraper not optimized for {domain}"}
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for easy identification."""
        try:
            # Simple domain extraction - could use urlparse for more robust parsing
            for domain in ["amazon", "target", "bestbuy", "ebay"]:
                if domain in url:
                    return domain
            return "unknown"
        except Exception:
            return "unknown"
    
    def _get_ranked_sources(self, domain: str) -> List[tuple]:
        """
        Get data sources ranked by historical performance.
        Adaptive strategy that learns which sources work best for each domain.
        
        Returns:
            List of tuples (source_name, source_function)
        """
        sources = [
            ("api", self._get_product_from_api),
            ("scraper", self._get_product_from_scraper),
            ("stealth", self._get_product_from_stealth_scraper)
        ]
        
        # For Amazon, prioritize stealth scraper after API
        if domain == "amazon":
            return [
                ("api", self._get_product_from_api),
                ("stealth", self._get_product_from_stealth_scraper),
                ("scraper", self._get_product_from_scraper)
            ]
        
        # For other domains, use general ranking based on success rates
        # This is a simplified ranking algorithm - in a real system, you might use
        # more sophisticated scoring combining success rate, response time, etc.
        if sum(self.source_stats["api"].values()) > 10:  # Only rerank after gathering data
            # Calculate success rates
            rates = {}
            for source, stats in self.source_stats.items():
                total = stats["success"] + stats["failure"]
                rates[source] = stats["success"] / total if total > 0 else 0
            
            # Sort sources by success rate
            sources.sort(key=lambda x: rates[x[0]], reverse=True)
        
        return sources
    
    def _record_success(self, source: str) -> None:
        """Record a successful API call for adaptive sourcing."""
        if source in self.source_stats:
            self.source_stats[source]["success"] += 1
    
    def _record_failure(self, source: str) -> None:
        """Record a failed API call for adaptive sourcing."""
        if source in self.source_stats:
            self.source_stats[source]["failure"] += 1
    
    async def find_alternatives(self, product_details: Dict[str, Any], max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Find alternative products to the one provided.
        Uses the specialized AlternativeFinder for better results.
        
        Args:
            product_details: Original product details
            max_results: Maximum number of alternatives to return
            
        Returns:
            List of alternative product details
        """
        # CRITICAL FIX: Ensure source is properly set before finding alternatives
        original_source = product_details.get('source', '').lower()
        url = product_details.get('url', '')
        
        # Always fix www to amazon if url contains amazon.com
        if original_source == 'www' and 'amazon' in url.lower():
            logger.info(f"Fixing source from 'www' to 'amazon' for alternatives search: {url}")
            product_details['source'] = 'amazon'
        
        # Log the search attempt for better debugging
        logger.info(f"Searching for alternatives for product from {product_details.get('source', 'unknown')} with title: {product_details.get('title', 'Unknown')}")
        
        # If we don't have a price, try to get it from the price_text
        if product_details.get('price') is None and product_details.get('price_text'):
            try:
                price_text = product_details.get('price_text', '')
                price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                if price_match:
                    price_str = price_match.group(1).replace(',', '')
                    price = float(price_str)
                    # Add it to the product details
                    product_details['price'] = price
                    logger.info(f"Extracted price ${price} from price_text '{price_text}' for alternatives search")
            except Exception as e:
                logger.error(f"Failed to extract price from price_text: {e}")
        
        # Use the advanced alternative finder for better results with a global timeout
        try:
            # Set a shorter global timeout for the entire alternatives search process
            # to prevent hanging and ensure quick response
            global_timeout = 20.0  # 20 seconds maximum for the entire alternatives search
            
            logger.info(f"Starting alternative search with {global_timeout}s timeout")
            
            # Create a task for the alternative search
            alternative_search_task = asyncio.create_task(
                self.alternative_finder.find_alternatives(product_details, max_results)
            )
            
            # Create a timeout task
            timeout_task = asyncio.create_task(asyncio.sleep(global_timeout))
            
            # Wait for either the search to complete or timeout
            done, pending = await asyncio.wait(
                {alternative_search_task, timeout_task},
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                
            # If the search task completed first, get the results
            if alternative_search_task in done:
                alternatives = await alternative_search_task
                logger.info(f"Alternative finder found {len(alternatives)} alternatives for {product_details.get('title', 'Unknown')}")
                
                # If no alternatives were found, try relaxed alternative method
                if not alternatives and max_results > 0:
                    logger.info("No alternatives found with regular method, trying relaxed method...")
                    alternatives = await self.scraper.find_relaxed_alternatives(product_details, max_results)
                    logger.info(f"Relaxed method found {len(alternatives)} alternatives")
                
                return alternatives
            else:
                # The timeout task completed first
                logger.warning(f"Alternative search timed out after {global_timeout}s. Trying relaxed method...")
                alternatives = await self.scraper.find_relaxed_alternatives(product_details, max_results)
                logger.info(f"Relaxed method found {len(alternatives)} alternatives after timeout")
                return alternatives
                
        except asyncio.CancelledError:
            logger.warning("Alternative search was cancelled. Trying relaxed method...")
            alternatives = await self.scraper.find_relaxed_alternatives(product_details, max_results)
            logger.info(f"Relaxed method found {len(alternatives)} alternatives after cancellation")
            return alternatives
        except Exception as e:
            logger.error(f"Error using alternative finder: {str(e)}")
            # If the alternative finder fails, try the relaxed method
            try:
                logger.info("Error in main alternative search, trying relaxed method...")
                alternatives = await self.scraper.find_relaxed_alternatives(product_details, max_results)
                logger.info(f"Relaxed method found {len(alternatives)} alternatives after error")
                return alternatives
            except Exception as relaxed_error:
                logger.error(f"Error in relaxed alternatives search: {str(relaxed_error)}")
                
                # As a final fallback, fall back to the original method with a shorter timeout
                try:
                    logger.info("Falling back to legacy alternative search")
                    fallback_timeout = 15.0
                    
                    # Create fallback search task
                    fallback_search_task = asyncio.create_task(
                        self.scraper.find_alternatives(product_details, max_results)
                    )
                    
                    # Create fallback timeout task
                    fallback_timeout_task = asyncio.create_task(asyncio.sleep(fallback_timeout))
                    
                    # Wait for either completion or timeout
                    done, pending = await asyncio.wait(
                        {fallback_search_task, fallback_timeout_task},
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()
                    
                    # If search completed, get results
                    if fallback_search_task in done:
                        alternatives = await fallback_search_task
                        logger.info(f"Fallback search found {len(alternatives)} alternatives")
                        return alternatives
                    else:
                        # The timeout task completed first
                        logger.warning(f"Fallback alternative search timed out after {fallback_timeout}s")
                        return []
                except asyncio.CancelledError:
                    logger.warning("Fallback search was cancelled.")
                    return []
                except Exception as fallback_error:
                    logger.error(f"Error in fallback alternatives search: {str(fallback_error)}")
                    return []
    
    def _identify_product_category(self, title: str, url: str) -> str:
        """Identify the product category from the title and URL."""
        title_lower = title.lower()
        url_lower = url.lower()
        
        # Check for shoes/footwear
        if any(word in title_lower or word in url_lower for word in 
              ['shoe', 'sneaker', 'trainer', 'boot', 'footwear']):
            return "shoes"
            
        # Check for electronics/computer
        if any(word in title_lower or word in url_lower for word in 
              ['laptop', 'computer', 'pc', 'desktop', 'macbook', 'chromebook']):
            return "computers"
            
        # Check for phones
        if any(word in title_lower or word in url_lower for word in 
              ['phone', 'iphone', 'smartphone', 'android', 'galaxy', 'pixel']):
            return "phones"
            
        # Check for TVs
        if any(word in title_lower or word in url_lower for word in 
              ['tv', 'television', 'smart tv', 'led tv', 'oled', 'qled']):
            return "tvs"
            
        # Check for audio
        if any(word in title_lower or word in url_lower for word in 
              ['headphone', 'earphone', 'earbud', 'airpod', 'speaker', 'soundbar']):
            return "audio"
            
        # Check for appliances
        if any(word in title_lower or word in url_lower for word in 
              ['refrigerator', 'washer', 'dryer', 'dishwasher', 'microwave', 'oven', 'vacuum']):
            return "appliances"
            
        # Check for gaming
        if any(word in title_lower or word in url_lower for word in 
              ['xbox', 'playstation', 'ps5', 'ps4', 'nintendo', 'switch', 'gaming', 'console']):
            return "gaming"
            
        # Check for home goods
        if any(word in title_lower or word in url_lower for word in 
              ['furniture', 'chair', 'table', 'desk', 'mattress', 'bed', 'sofa', 'couch']):
            return "home"
        
        # Default to general if no specific category is detected
        return "general"
    
    def _extract_brand_from_title(self, title: str) -> str:
        """Extract brand name from product title."""
        # Common approach: first word is often the brand
        parts = title.split()
        if len(parts) > 0:
            return parts[0]
        return ""
    
    def _extract_model_from_title(self, title: str) -> str:
        """Extract model number or name from product title."""
        # Look for patterns that might be model numbers
        model_patterns = [
            r'(\b[A-Z0-9]+-[A-Z0-9]+\b)',  # Matches patterns like "X-T30"
            r'(\b[A-Z][0-9]{1,4}\b)',      # Matches patterns like "A7" or "X100"
            r'(\b[A-Z]{1,3}[0-9]{2,4}\b)'  # Matches patterns like "EOS80D" or "A7III"
        ]
        
        for pattern in model_patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        
        # If no pattern matches, use words after brand (if title has multiple words)
        parts = title.split()
        if len(parts) > 1:
            return parts[1]
        
        return ""
    
    def _extract_key_attributes(self, title: str, category: str) -> List[str]:
        """Extract key product attributes based on category."""
        title_lower = title.lower()
        attributes = []
        
        # Extract size information
        size_match = re.search(r'(\d+(\.\d+)?)\s*(inch|"|in\b)', title_lower)
        if size_match:
            attributes.append(f"{size_match.group(1)} inch")
        
        # Extract color information
        color_match = re.search(r'\b(black|white|blue|red|green|yellow|gray|grey|silver|gold|rose gold|purple|pink)\b', title_lower)
        if color_match:
            attributes.append(color_match.group(1))
        
        # Category-specific attributes
        if category == "shoes":
            # Look for size
            shoe_size_match = re.search(r'size\s*(\d+(\.\d+)?)', title_lower)
            if shoe_size_match:
                attributes.append(f"size {shoe_size_match.group(1)}")
                
            # Look for gender
            if "men" in title_lower:
                attributes.append("men")
            elif "women" in title_lower:
                attributes.append("women")
            
        elif category == "computers":
            # Look for CPU
            cpu_match = re.search(r'\b(i3|i5|i7|i9|ryzen|core)\b', title_lower)
            if cpu_match:
                attributes.append(cpu_match.group(1))
                
            # Look for RAM
            ram_match = re.search(r'(\d+)\s*gb\s*(ram|memory)', title_lower)
            if ram_match:
                attributes.append(f"{ram_match.group(1)}GB RAM")
                
            # Look for storage
            storage_match = re.search(r'(\d+)\s*(gb|tb)\s*(ssd|hdd|storage)', title_lower)
            if storage_match:
                attributes.append(f"{storage_match.group(1)}{storage_match.group(2)} storage")
        
        elif category == "phones":
            # Look for storage
            storage_match = re.search(r'(\d+)\s*(gb|tb)', title_lower)
            if storage_match:
                attributes.append(f"{storage_match.group(1)}{storage_match.group(2)}")
                
            # Look for generation/version
            gen_match = re.search(r'((\d+)(nd|rd|th)?\s*gen)', title_lower)
            if gen_match:
                attributes.append(gen_match.group(1))
        
        return attributes
    
    def _generate_targeted_search_query(self, brand: str, model: str, attributes: List[str], category: str) -> str:
        """Generate a targeted search query based on product attributes."""
        query_parts = []
        
        # Always include brand if available
        if brand:
            query_parts.append(brand)
        
        # Include model for specific product targeting
        if model:
            query_parts.append(model)
        
        # Add the most important attributes (limit to 2 to avoid over-specification)
        important_attributes = attributes[:2] if attributes else []
        query_parts.extend(important_attributes)
        
        # Add category term if general attributes are limited
        if len(query_parts) < 3 and category != "general":
            category_terms = {
                "shoes": "shoes",
                "computers": "laptop",
                "phones": "smartphone",
                "tvs": "tv",
                "audio": "headphones",
                "appliances": "appliance",
                "gaming": "console",
                "home": "furniture"
            }
            if category in category_terms:
                query_parts.append(category_terms[category])
        
        # Join parts with spaces for the final query
        return " ".join(query_parts)
    
    async def _search_market_for_alternative(self, market: str, search_query: str, category: str, original_product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Search a specific market for an alternative product."""
        encoded_query = search_query.replace(" ", "+")
        
        # Set a reasonable timeout for each market search to avoid hanging
        search_timeout = 10.0  # 10 seconds max
        
        if market == "amazon":
            search_url = f"https://www.amazon.com/s?k={encoded_query}"
            try:
                # Use timeout to prevent hanging
                return await asyncio.wait_for(
                    self.scraper._get_amazon_search_result(search_url),
                    timeout=search_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Amazon search timed out after {search_timeout}s")
                return {"status": "error", "message": "Amazon search timed out", "source": "amazon"}
            except Exception as e:
                logger.error(f"Error searching Amazon: {e}")
                return {"status": "error", "message": f"Amazon search error: {str(e)}", "source": "amazon"}
        
        elif market == "target":
            search_url = f"https://www.target.com/s?searchTerm={encoded_query}"
            try:
                if hasattr(self.scraper, "_get_target_search_result"):
                    return await asyncio.wait_for(
                        self.scraper._get_target_search_result(search_url),
                        timeout=search_timeout
                    )
                else:
                    logger.warning("Target search method not found in scraper")
                    return {"status": "error", "message": "Target search not implemented", "source": "target"}
            except asyncio.TimeoutError:
                logger.warning(f"Target search timed out after {search_timeout}s")
                return {"status": "error", "message": "Target search timed out", "source": "target"}
            except Exception as e:
                logger.error(f"Error searching Target: {e}")
                return {"status": "error", "message": f"Target search error: {str(e)}", "source": "target"}
        
        elif market == "bestbuy":
            search_url = f"https://www.bestbuy.com/site/searchpage.jsp?st={encoded_query}"
            try:
                if hasattr(self.scraper, "_get_bestbuy_search_result"):
                    return await asyncio.wait_for(
                        self.scraper._get_bestbuy_search_result(search_url),
                        timeout=search_timeout
                    )
                else:
                    logger.warning("Best Buy search method not found in scraper")
                    return {"status": "error", "message": "Best Buy search not implemented", "source": "bestbuy"}
            except asyncio.TimeoutError:
                logger.warning(f"Best Buy search timed out after {search_timeout}s")
                return {"status": "error", "message": "Best Buy search timed out", "source": "bestbuy"}
            except Exception as e:
                logger.error(f"Error searching Best Buy: {e}")
                return {"status": "error", "message": f"Best Buy search error: {str(e)}", "source": "bestbuy"}
        
        else:
            return {"status": "error", "message": f"Unsupported market: {market}", "source": market}
    
    def cleanup(self):
        """Clean up resources from all providers."""
        try:
            self.api_fetcher.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up API fetcher: {str(e)}")
        
        try:
            # Call any cleanup methods that may exist on scrapers
            if hasattr(self.scraper, 'cleanup'):
                self.scraper.cleanup()
            if hasattr(self.stealth_scraper, 'cleanup'):
                self.stealth_scraper.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up scrapers: {str(e)}")
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a reasonable product title from URL path segments."""
        try:
            parsed_url = urlparse(url)
            segments = parsed_url.path.strip('/').split('/')
            
            # Find the longest segment that's likely the product name
            product_segment = ""
            for segment in segments:
                if len(segment) > len(product_segment) and not segment.startswith('dp/') and not segment.isdigit():
                    product_segment = segment
            
            # Clean and format the title
            if product_segment:
                title = product_segment.replace('-', ' ').replace('_', ' ').title()
                return title
                
            # Fallback to domain + product
            domain = self._extract_domain(url)
            return f"{domain.capitalize()} Product"
        except:
            return "Unknown Product"
    
    async def analyze_deal(self, product_details: Dict[str, Any], alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze if a product is a good deal compared to alternatives.
        Uses real data only - no synthetic data generation.
        
        Args:
            product_details: Original product details
            alternatives: List of alternative products
            
        Returns:
            Deal analysis with reasons
        """
        # Apply a reasonable timeout to the entire analysis
        try:
            return await asyncio.wait_for(
                self._perform_deal_analysis(product_details, alternatives),
                timeout=15.0  # 15 second timeout for analysis
            )
        except asyncio.TimeoutError:
            logger.warning("Deal analysis timed out. Returning basic analysis.")
            
            # Return a simple "cannot determine" verdict when we time out
            return {
                "is_good_deal": None,
                "verdict": "CANNOT DETERMINE ⚠️",
                "confidence": "very low",
                "price": product_details.get('price'),
                "holistic_score": 0,
                "reasons": [
                    f"Analysis of {product_details.get('source', 'unknown').capitalize()} listing:",
                    "- Analysis timed out before completion",
                    "- Price: " + (product_details.get('price_text', 'Price unavailable')),
                    "\nOverall Assessment: CANNOT DETERMINE if this is a good deal due to analysis timeout."
                ]
            }
        
    async def _perform_deal_analysis(self, product_details: Dict[str, Any], alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Internal method to perform the actual deal analysis, wrapped with timeout."""
        # CRITICAL FIX: Fix source again just in case
        original_source = product_details.get('source', '').lower()
        url = product_details.get('url', '')
        
        # Always fix www to amazon if url contains amazon.com
        if original_source == 'www' and 'amazon' in url.lower():
            logger.info(f"Fixing source from 'www' to 'amazon' for deal analysis: {url}")
            product_details['source'] = 'amazon'
            
        # Check if we have enough data for a meaningful analysis
        source = product_details.get('source', 'unknown')
        title = product_details.get('title', 'Unknown Product')
        price = product_details.get('price')
        price_text = product_details.get('price_text', 'Price unavailable') 
        rating_text = product_details.get('rating', 'No ratings')
        availability = product_details.get('availability', 'Unknown')
        
        # Extra attempt to extract price from price_text if not already available
        if price is None and price_text and price_text != 'Price unavailable':
            try:
                # Try harder to extract price from text
                price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                if price_match:
                    price_str = price_match.group(1).replace(',', '')
                    price = float(price_str)
                    logger.info(f"Successfully extracted price ${price} from price_text '{price_text}' during analysis")
                    
                    # Do a final sanity check on the extracted price
                    if price > 10000 or price < 1:
                        logger.warning(f"Extracted price ${price} is outside reasonable range - ignoring")
                        price = None
            except Exception as e:
                logger.error(f"Error extracting price from price_text during analysis: {e}")
        
        # Try to extract rating value
        rating = 0
        try:
            if rating_text and rating_text.lower() != 'no ratings':
                rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
        except Exception as e:
            logger.error(f"Failed to extract rating value: {e}")
        
        # Determine what data we have
        has_price = price is not None
        has_rating = rating > 0
        has_availability = availability is not None and availability.lower() not in ['unknown', 'none']
        
        logger.info(f"Deal analysis data check - Price: {has_price}, Rating: {has_rating}, Availability: {has_availability}")
        
        # Calculate confidence based on available data
        if has_price and has_rating and has_availability:
            confidence = "high"
        elif has_price and (has_rating or has_availability):
            confidence = "medium"
        elif has_price:
            confidence = "low"
        elif has_rating or has_availability:  # MODIFIED: Even without price, we can have some confidence if we have other data
            confidence = "medium-low"
        else:
            confidence = "very low"
            
        # Initialize reasons list
        reasons = []
        
        # Generate analysis intro based on available data
        reasons.append(f"Analysis of {source.capitalize()} listing:")
        
        # Add price analysis
        if has_price:
            reasons.append(f"- Price: {price_text}")
        else:
            reasons.append("- Price information not available")
            
        # Add rating analysis
        if has_rating:
            reasons.append(f"- Rating: {rating_text}")
        else:
            reasons.append("- Rating: No rating information available")
            
        # Add availability analysis
        if has_availability:
            reasons.append(f"- Availability: {availability}")
        else:
            reasons.append("- Availability: Information not available")
        
        # Calculate holistic score whether we have price or not
        holistic_score = 0
        
        # MODIFIED: Changed to calculate score even without price
        # Rating score (0-50 points when price is missing, 0-30 when price exists)
        rating_score = (rating / 5.0) * (50 if not has_price else 30) if has_rating else 0
        
        # Availability score (0-20 points when price is missing, 0-10 when price exists)
        availability_score = 0
        if has_availability:
            if "in stock" in availability.lower():
                availability_score = 20 if not has_price else 10
            elif "available" in availability.lower():
                availability_score = 15 if not has_price else 8
            elif "limited" in availability.lower():
                availability_score = 10 if not has_price else 5
        
        # Brand reputation based on source (0-30 points when price is missing, 0-10 when price exists)
        brand_score = 0
        if source.lower() in ["amazon", "target", "bestbuy"]:
            brand_score = 30 if not has_price else 10  # Major retailers
        elif source.lower() in ["walmart", "ebay"]:
            brand_score = 25 if not has_price else 8  # Established retailers
        else:
            brand_score = 15 if not has_price else 5  # Unknown retailers
            
        if has_price:
            # When we have price, use normal scoring system
            price_score = 25  # Neutral starting point
            holistic_score = price_score + rating_score + availability_score + brand_score
        else:
            # When price is missing, use alternative scoring system
            # Add scores from non-price factors with higher weights
            holistic_score = rating_score + availability_score + brand_score
            
        reasons.append(f"- Overall Value Score: {round(holistic_score, 1)}/100")
        
        # Price-based comparison for alternatives
        better_alternatives_price = []
        
        # Non-price based comparison for alternatives (ADDED)
        better_alternatives_nonprice = []
        
        # Analyze alternatives
        if alternatives:
            # MODIFIED: Separate price and non-price comparisons
            if has_price:
                # For alternatives with price data, compare prices
                better_alternatives_price = [
                    alt for alt in alternatives 
                    if alt.get("is_better_deal", False) and alt.get("price") is not None
                ]
                
            # For all alternatives, check for better ratings/availability regardless of price
            for alt in alternatives:
                alt_rating = 0
                alt_has_rating = False
                
                # Extract rating if available
                if alt.get("rating"):
                    try:
                        rating_match = re.search(r'(\d+(\.\d+)?)', alt.get("rating", ""))
                        if rating_match:
                            alt_rating = float(rating_match.group(1))
                            alt_has_rating = True
                    except Exception:
                        pass
                
                # Check if alternative has better non-price attributes
                if (alt_has_rating and has_rating and alt_rating > rating) or \
                   (alt_has_rating and not has_rating) or \
                   (alt.get("availability") and "in stock" in alt.get("availability").lower() and 
                    (not has_availability or "in stock" not in availability.lower())):
                    
                    # Add a reason for why this is better
                    alt_reason = []
                    if alt_has_rating and has_rating and alt_rating > rating:
                        alt_reason.append(f"Better rating ({alt_rating} vs {rating})")
                    elif alt_has_rating and not has_rating:
                        alt_reason.append(f"Has rating ({alt_rating}) while original doesn't")
                        
                    if alt.get("availability") and "in stock" in alt.get("availability").lower():
                        if not has_availability:
                            alt_reason.append("Has availability information while original doesn't")
                        elif "in stock" not in availability.lower():
                            alt_reason.append("Better availability")
                    
                    # Add to better non-price alternatives
                    alt_copy = alt.copy()
                    alt_copy["reason"] = ", ".join(alt_reason)
                    better_alternatives_nonprice.append(alt_copy)
            
            # Add results to reasons
            if better_alternatives_price:
                reasons.append(f"\nFound {len(better_alternatives_price)} potentially better options (price-based):")
                for alt in better_alternatives_price[:2]:  # Show top 2
                    alt_source = alt.get("source", "").capitalize()
                    alt_price = f"${alt.get('price')}" if alt.get("price") is not None else "Price unknown"
                    alt_reason = alt.get("reason", "")
                    
                    reasons.append(f"\n- {alt_source} alternative:")
                    reasons.append(f"  • Price: {alt_price}")
                    if alt.get("rating"):
                        reasons.append(f"  • Rating: {alt.get('rating')}")
                    if alt.get("availability"):
                        reasons.append(f"  • Availability: {alt.get('availability')}")
                    reasons.append(f"  • Key advantages: {alt_reason}")
            
            # Add non-price alternatives (ADDED)
            if not has_price and better_alternatives_nonprice:
                reasons.append(f"\nFound {len(better_alternatives_nonprice)} potentially better options (based on ratings/availability):")
                for alt in better_alternatives_nonprice[:2]:  # Show top 2
                    alt_source = alt.get("source", "").capitalize()
                    alt_price = f"${alt.get('price')}" if alt.get("price") is not None else "Price unknown"
                    alt_reason = alt.get("reason", "")
                    
                    reasons.append(f"\n- {alt_source} alternative:")
                    if alt.get("price") is not None:
                        reasons.append(f"  • Price: {alt_price}")
                    if alt.get("rating"):
                        reasons.append(f"  • Rating: {alt.get('rating')}")
                    if alt.get("availability"):
                        reasons.append(f"  • Availability: {alt.get('availability')}")
                    reasons.append(f"  • Key advantages: {alt_reason}")
            
            if not better_alternatives_price and not better_alternatives_nonprice:
                reasons.append("\nAlternatives found but none offered better overall value.")
        else:
            reasons.append("\nNo alternatives found for comparison.")
        
        # Overall assessment based on data quality
        is_good_deal = None  # Default to unknown
        if not has_price:
            # MODIFIED: Handle missing price but with other data
            if has_rating or has_availability:
                # When we have rating or availability but no price
                if better_alternatives_nonprice:
                    reasons.append("\nOverall Assessment: Based on non-price factors (rating, availability), better alternatives are available.")
                    verdict = "BETTER ALTERNATIVES AVAILABLE ⚠️"
                    is_good_deal = False
                else:
                    reasons.append("\nOverall Assessment: Cannot determine if this is the best price, but product has good ratings/availability.")
                    verdict = "GOOD RATINGS/AVAILABILITY ℹ️"
                    is_good_deal = None
            else:
                reasons.append("\nOverall Assessment: CANNOT DETERMINE if this is a good deal without price information.")
                verdict = "CANNOT DETERMINE ⚠️"
                is_good_deal = None
        elif len(alternatives) == 0:
            if not has_rating and not has_availability:
                reasons.append("\nOverall Assessment: CANNOT DETERMINE if this is a good deal with limited information and no alternatives.")
                verdict = "CANNOT DETERMINE ⚠️"
                is_good_deal = None
            else:
                reasons.append("\nOverall Assessment: This seems reasonable, but we couldn't find alternatives for a thorough comparison.")
                verdict = "LIKELY REASONABLE ℹ️"
                is_good_deal = True  # Slight positive bias when we have some data but no alternatives
        elif better_alternatives_price:
            reasons.append("\nOverall Assessment: Consider the alternatives above which may offer better overall value.")
            verdict = "BETTER ALTERNATIVES AVAILABLE ⚠️"
            is_good_deal = False  # Not a good deal if better alternatives exist
        else:
            reasons.append("\nOverall Assessment: This appears to be the best value among available options.")
            verdict = "GOOD DEAL ✓"
            is_good_deal = True  # Good deal if no better alternatives
        
        # Add confidence disclaimer
        if confidence in ["very low", "low", "medium-low"]:
            reasons.append(f"\nNote: This assessment has {confidence} confidence due to limited data or lack of alternatives for comparison.")
        
        # Add retailers compared
        compared_retailers = set([source.lower()])
        compared_retailers.update([alt.get("source", "").lower() for alt in alternatives])
        compared_retailers = [r.capitalize() for r in compared_retailers if r]
        if compared_retailers:
            confidence_note = "high confidence" if len(compared_retailers) >= 3 else "moderate confidence"
            reasons.append(f"\nRetailers compared: {', '.join(compared_retailers)} ({confidence_note})")
        
        # Add assessment factors
        reasons.append("\nNote: This comparison considers multiple factors for a holistic evaluation:")
        reasons.append("• Price and value for money" + (" (when available)" if not has_price else ""))
        reasons.append("• Customer ratings and review volume")
        reasons.append("• Product availability and shipping options")
        reasons.append("• Retailer reputation and reliability")
        
        return {
            "is_good_deal": is_good_deal,
            "verdict": verdict,
            "confidence": confidence,
            "price": price,
            "holistic_score": round(holistic_score, 1) if holistic_score > 0 else 0,
            "reasons": reasons
        }
    
    async def _try_direct_browser_scrape(self, url: str) -> Optional[float]:
        """Last resort method to extract price using direct browser scraping."""
        try:
            logger.info(f"Attempting direct browser scrape for {url}")
            
            # For Amazon products, try a special approach just to get the price
            if "amazon" in url.lower():
                # First try the focused price extraction method
                price = await self.stealth_scraper.get_amazon_product_price(url)
                if price is not None:
                    return price
                
                # If that fails, try via the standard data methods
                result = await self.stealth_scraper.get_amazon_product_data(url)
                if result and result.get("price") is not None:
                    return result.get("price")
                
                # If that still fails, try via the standard scraper
                result = await self.scraper.get_product_details(url)
                if result and result.get("price") is not None:
                    return result.get("price")
            
            # For other domains, use the appropriate scraper
            elif "target" in url.lower():
                result = await self.scraper.scrape_target(url)
                if result and result.get("price") is not None:
                    return result.get("price")
            
            elif "bestbuy" in url.lower():
                result = await self.scraper.scrape_bestbuy(url)
                if result and result.get("price") is not None:
                    return result.get("price")
            
            return None
        except Exception as e:
            logger.error(f"Error in direct browser scrape: {str(e)}")
            return None 