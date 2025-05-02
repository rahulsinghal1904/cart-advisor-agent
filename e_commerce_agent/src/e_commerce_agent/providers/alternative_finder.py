import re
import logging
import asyncio
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AlternativeFinder:
    """Enhanced alternative product finder with multi-strategy search capabilities."""
    
    def __init__(self, price_scraper):
        """
        Initialize the alternative finder with a reference to the price scraper.
        
        Args:
            price_scraper: An instance of PriceScraper for performing searches
        """
        self.scraper = price_scraper
        
    async def find_alternatives(self, product_details: Dict[str, Any], max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Find alternative products to the one provided using multiple search strategies.
        
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
        
        # FAST PATH: If we're missing critical data, don't waste time with expensive searches
        if product_details.get('status') != 'success':
            logger.warning(f"Skipping alternatives search for unsuccessful product fetch: {product_details.get('message', 'Unknown error')}")
            return []
            
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
        
        # FAST PATH: If we still don't have a price after trying to extract it, 
        # searching for alternatives is likely to be unproductive
        if product_details.get('price') is None:
            logger.warning("Skipping alternatives search because price is missing")
            return []
        
        # Get product information
        source = product_details.get('source', 'unknown').lower()
        title = product_details.get('title', 'Unknown Product')
        
        # Skip alternatives search if title is unusable
        if title == "Unknown Product" or len(title) < 5:
            logger.warning(f"Cannot search for alternatives without a valid product title: {title}")
            return []
            
        # Identify the category of the product for better search targeting
        category = self._identify_product_category(title, url)
        logger.info(f"Identified product category: {category}")
        
        # Use multi-strategy search with multiple retries
        alternatives = []
        error_count = 0 
        max_errors = 3  # Maximum allowed errors before giving up
        
        # Try to search for alternatives in all available markets except the source
        available_markets = ["amazon", "target", "bestbuy"]
        target_markets = [market for market in available_markets if market != source]
        
        # First try a direct search by title for every market
        for market in target_markets:
            if len(alternatives) >= max_results:
                break
                
            try:
                logger.info(f"Searching for alternatives on {market} for {title}")
                alt_result = await self._search_market_for_alternative(market, title, category, product_details)
                
                if alt_result and alt_result.get("status") == "success":
                    alternatives.append(alt_result)
                    logger.info(f"Found alternative on {market}: {alt_result.get('title', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error searching {market}: {str(e)}")
                error_count += 1
                if error_count >= max_errors:
                    logger.warning(f"Too many errors ({error_count}), stopping alternatives search")
                    break
        
        # If we don't have enough alternatives, try attribute-based search
        if len(alternatives) < max_results:
            # Extract attributes from product title
            brand = self._extract_brand_from_title(title)
            model = self._extract_model_from_title(title)
            attributes = self._extract_key_attributes(title, category)
            
            logger.info(f"Extracted product attributes - Brand: {brand}, Model: {model}, Attributes: {attributes}")
            
            # Generate targeted search query based on extracted attributes
            search_query = self._generate_targeted_search_query(brand, model, attributes, category)
            
            # Try remaining markets with the targeted query
            for market in target_markets:
                if market not in [alt.get("source", "").lower() for alt in alternatives] and len(alternatives) < max_results:
                    try:
                        logger.info(f"Searching {market} with targeted query: {search_query}")
                        alt_result = await self._search_market_for_alternative(market, search_query, category, product_details)
                        
                        if alt_result and alt_result.get("status") == "success":
                            alternatives.append(alt_result)
                            logger.info(f"Found alternative on {market} with targeted query: {alt_result.get('title', 'Unknown')}")
                    except Exception as e:
                        logger.error(f"Error searching {market} with targeted query: {str(e)}")
                        error_count += 1
                        if error_count >= max_errors:
                            break
        
        # Post-process alternatives to calculate if they're better deals
        processed_alternatives = []
        for alt in alternatives:
            if alt.get("price") is not None and product_details.get("price") is not None:
                # Calculate price difference
                price_diff = product_details.get("price") - alt.get("price")
                price_diff_percent = (price_diff / product_details.get("price")) * 100 if product_details.get("price") > 0 else 0
                
                # Determine if it's a better deal
                if price_diff_percent > 5:  # At least 5% cheaper
                    alt["is_better_deal"] = True
                    alt["reason"] = f"{abs(round(price_diff_percent))}% cheaper than original"
                else:
                    alt["is_better_deal"] = False
                    if price_diff_percent < -5:  # More expensive
                        alt["reason"] = f"{abs(round(price_diff_percent))}% more expensive than original"
                    else:
                        alt["reason"] = "Similar price to original"
            else:
                # Can't determine if it's a better deal without prices
                alt["is_better_deal"] = False
                alt["reason"] = "Cannot compare prices (missing data)"
                
            processed_alternatives.append(alt)
            
        return processed_alternatives[:max_results]
    
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
        
        # Set shorter timeouts to prevent hanging
        search_timeout = 8.0  # 8 seconds max for any search request
        
        logger.info(f"Searching for alternative on {market} with query: {search_query}")
        
        if market == "amazon":
            search_url = f"https://www.amazon.com/s?k={encoded_query}"
            try:
                # Add timeout to prevent hanging
                result = await asyncio.wait_for(
                    self.scraper._get_amazon_search_result(search_url),
                    timeout=search_timeout
                )
                logger.debug(f"Amazon search result status: {result.get('status', 'unknown')}")
                return result
            except asyncio.TimeoutError:
                logger.warning(f"Amazon search timed out after {search_timeout}s for query: {search_query}")
                return {"status": "error", "message": "Amazon search timed out", "source": "amazon"}
            except Exception as e:
                logger.error(f"Error searching Amazon: {e}")
                return {"status": "error", "message": f"Amazon search failed: {str(e)}", "source": "amazon"}
        
        elif market == "target":
            search_url = f"https://www.target.com/s?searchTerm={encoded_query}"
            # Target search not fully implemented
            return {"status": "error", "message": "Target search not implemented", "source": "target"}
        
        elif market == "bestbuy":
            search_url = f"https://www.bestbuy.com/site/searchpage.jsp?st={encoded_query}"
            try:
                # First try to see if the scraper has the method
                if hasattr(self.scraper, "_get_bestbuy_search_result"):
                    result = await asyncio.wait_for(
                        self.scraper._get_bestbuy_search_result(search_url),
                        timeout=search_timeout
                    )
                    logger.debug(f"Best Buy search result status: {result.get('status', 'unknown')}")
                    return result
                else:
                    logger.warning("Best Buy search not implemented in scraper")
                    return {"status": "error", "message": "Best Buy search not implemented", "source": "bestbuy"}
            except asyncio.TimeoutError:
                logger.warning(f"Best Buy search timed out after {search_timeout}s for query: {search_query}")
                return {"status": "error", "message": "Best Buy search timed out", "source": "bestbuy"}
            except Exception as e:
                logger.error(f"Error searching Best Buy: {e}")
                return {"status": "error", "message": f"Best Buy search failed: {str(e)}", "source": "bestbuy"}
        
        else:
            return {"status": "error", "message": f"Unsupported market: {market}", "source": market} 