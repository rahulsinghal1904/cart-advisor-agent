import logging
import asyncio
from typing import Dict, List, Any, Optional
from .price_api_fetcher import PriceAPIFetcher
from .price_scraper import PriceScraper, StealthScraper

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
        
        # Track success/failure rates for adaptive sourcing
        self.source_stats = {
            "api": {"success": 0, "failure": 0},
            "scraper": {"success": 0, "failure": 0},
            "stealth": {"success": 0, "failure": 0}
        }
        
        logger.info("Initialized PriceProvider with multi-tier strategy and fallbacks")
    
    async def get_product_details(self, url: str) -> Dict[str, Any]:
        """
        Get product details using a cascading fallback approach.
        
        Strategy:
        1. Try API-based fetching first (fastest, most reliable)
        2. If API fails, try the standard scraper
        3. If standard scraper fails, try the stealth scraper
        4. Return best available result or error
        
        Args:
            url: Product URL
            
        Returns:
            Dict with product details including price
        """
        domain = self._extract_domain(url)
        logger.info(f"Fetching product details for {url} from {domain}")
        
        # Determine optimal source order based on historical performance
        sources = self._get_ranked_sources(domain)
        
        result = None
        error_messages = []
        
        # Try each source in sequence until one succeeds
        for source_name, source_func in sources:
            try:
                logger.info(f"Trying {source_name} for {url}")
                result = await source_func(url)
                
                if result and result.get("status") == "success" and result.get("price"):
                    # Record success and return result
                    self._record_success(source_name)
                    result["provider"] = source_name
                    return result
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
        elif "walmart" in domain:
            return await self.scraper.scrape_walmart(url)
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
            for domain in ["amazon", "walmart", "bestbuy", "target", "ebay"]:
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
        Delegates to the standard scraper for this functionality.
        
        Args:
            product_details: Original product details
            max_results: Maximum number of alternatives to return
            
        Returns:
            List of alternative product details
        """
        return await self.scraper.find_alternatives(product_details, max_results)
    
    async def analyze_deal(self, product_details: Dict[str, Any], alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze if a product is a good deal compared to alternatives.
        Delegates to the standard scraper for this functionality.
        
        Args:
            product_details: Original product details
            alternatives: List of alternative products
            
        Returns:
            Deal analysis
        """
        return await self.scraper.analyze_deal(product_details, alternatives)
    
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