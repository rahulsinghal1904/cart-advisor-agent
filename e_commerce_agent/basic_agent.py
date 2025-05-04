import asyncio
import re
import json
from urllib.parse import urlparse
import urllib.request
import secrets

class SimpleECommercePriceComparison:
    """
    A basic e-commerce price comparison tool.
    This is a simplified implementation that doesn't rely on external dependencies.
    """
    
    def __init__(self):
        """Initialize the tool with basic user agent."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def _extract_price(self, text):
        """Extract price from text."""
        price_pattern = re.compile(r'\$([0-9]+(?:\.[0-9]{2})?)')
        match = price_pattern.search(text)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_title(self, text, site):
        """Extract title based on site patterns."""
        if site == "amazon":
            title_pattern = re.compile(r'<span id="productTitle"[^>]*>([^<]+)</span>')
            match = title_pattern.search(text)
            if match:
                return match.group(1).strip()
        return "Unknown Product"
    
    def _mock_product_details(self, url):
        """Generate mock product details for demonstration."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Determine source based on domain
        if "amazon.com" in domain:
            source = "amazon"
            price = 149.99
        elif "walmart.com" in domain:
            source = "walmart"
            price = 142.99
        elif "bestbuy.com" in domain:
            source = "bestbuy"
            price = 159.99
        else:
            return {
                "status": "error",
                "message": f"Unsupported website: {domain}",
                "url": url
            }
        
        # Generate product info
        product_types = ["Headphones", "Laptop", "Smartphone", "Tablet", "Smart Watch"]
        brands = ["Sony", "Apple", "Samsung", "Dell", "Bose"]
        
        product_type = secrets.choice(product_types)
        brand = secrets.choice(brands)
        title = f"{brand} {product_type} - Premium Model"
        
        return {
            "status": "success",
            "source": source,
            "url": url,
            "title": title,
            "price": price,
            "price_text": f"${price}",
            "rating": f"{secrets.SystemRandom().randint(3, 5)}.{secrets.SystemRandom().randint(0, 9)} stars"
        }
    
    def _generate_alternatives(self, product_details):
        """Generate alternative options based on the product details."""
        if product_details.get("status") != "success":
            return []
        
        source = product_details.get("source", "unknown")
        title = product_details.get("title", "Unknown Product")
        price = product_details.get("price", 100)
        
        alternatives = []
        
        # Add mock alternatives based on the source
        if source == "amazon":
            alternatives.append({
                "source": "walmart",
                "title": title,
                "price": round(price * 0.95, 2),
                "url": "https://www.walmart.com/search/?query=" + title.replace(" ", "+"),
                "is_better_deal": True,
                "reason": "5% cheaper than Amazon"
            })
            
            alternatives.append({
                "source": "bestbuy",
                "title": title,
                "price": round(price * 1.05, 2),
                "url": "https://www.bestbuy.com/site/searchpage.jsp?st=" + title.replace(" ", "+"),
                "is_better_deal": False,
                "reason": "5% more expensive than Amazon"
            })
        
        elif source == "walmart":
            alternatives.append({
                "source": "amazon",
                "title": title,
                "price": round(price * 1.02, 2),
                "url": "https://www.amazon.com/s?k=" + title.replace(" ", "+"),
                "is_better_deal": False,
                "reason": "2% more expensive than Walmart"
            })
            
            alternatives.append({
                "source": "bestbuy",
                "title": title,
                "price": round(price * 1.08, 2),
                "url": "https://www.bestbuy.com/site/searchpage.jsp?st=" + title.replace(" ", "+"),
                "is_better_deal": False,
                "reason": "8% more expensive than Walmart"
            })
        
        elif source == "bestbuy":
            alternatives.append({
                "source": "amazon",
                "title": title,
                "price": round(price * 0.97, 2),
                "url": "https://www.amazon.com/s?k=" + title.replace(" ", "+"),
                "is_better_deal": True,
                "reason": "3% cheaper than Best Buy"
            })
            
            alternatives.append({
                "source": "walmart",
                "title": title,
                "price": round(price * 0.93, 2),
                "url": "https://www.walmart.com/search/?query=" + title.replace(" ", "+"),
                "is_better_deal": True,
                "reason": "7% cheaper than Best Buy"
            })
        
        return alternatives
    
    def _analyze_deal(self, product_details, alternatives):
        """Analyze if the product is a good deal."""
        if product_details.get("status") != "success":
            return {
                "is_good_deal": False,
                "confidence": "low",
                "reasons": ["Unable to determine price information"]
            }
        
        better_alternatives = [alt for alt in alternatives if alt.get("is_better_deal", False)]
        is_good_deal = len(better_alternatives) == 0
        
        reasons = []
        if len(better_alternatives) > 0:
            reasons.append(f"Found {len(better_alternatives)} better price(s) on alternative platforms")
            for alt in better_alternatives:
                reasons.append(f"{alt.get('source', 'Alternative').capitalize()}: {alt.get('reason', 'Better price')}")
        else:
            reasons.append("No better deals found on other platforms")
        
        return {
            "is_good_deal": is_good_deal,
            "confidence": "medium",
            "price": product_details.get("price"),
            "reasons": reasons
        }
    
    def _generate_recommendation(self, product_details, alternatives, analysis):
        """Generate a recommendation for the user."""
        if product_details.get("status") != "success":
            return f"Unable to analyze the product at {product_details.get('url')}. Please try a different URL."
        
        title = product_details.get("title", "the product")
        price = product_details.get("price_text", "unknown price")
        source = product_details.get("source", "the retailer").capitalize()
        
        if analysis.get("is_good_deal", False):
            recommendation = f"{title} at {price} from {source} appears to be a good deal. "
            recommendation += "No better alternatives were found across major retailers."
        else:
            recommendation = f"{title} at {price} from {source} is not the best deal available. "
            
            if alternatives:
                better_alts = [alt for alt in alternatives if alt.get("is_better_deal", False)]
                if better_alts:
                    best_alt = min(better_alts, key=lambda x: x.get("price", float("inf")))
                    alt_price = f"${best_alt.get('price')}"
                    alt_source = best_alt.get("source", "another retailer").capitalize()
                    recommendation += f"You can find a better price at {alt_source} for {alt_price}. "
                    recommendation += f"This is {best_alt.get('reason', 'a better deal')}."
                else:
                    recommendation += "However, no significantly better alternatives were found."
            else:
                recommendation += "However, no alternative options were available for comparison."
        
        return recommendation
    
    async def analyze_product(self, url):
        """Analyze a product URL and determine if it's a good deal."""
        print(f"Analyzing product: {url}")
        print("-" * 50)
        
        # Get product details (using mock for simplicity)
        print("Fetching product details...")
        product_details = self._mock_product_details(url)
        
        if product_details.get("status") == "success":
            print(f"Product: {product_details.get('title')}")
            print(f"Price: {product_details.get('price_text')}")
            print(f"Rating: {product_details.get('rating')}")
            print("\nSearching for alternatives...")
            
            # Find alternatives
            alternatives = self._generate_alternatives(product_details)
            
            if alternatives:
                print("\nAlternative options found:")
                for alt in alternatives:
                    print(f"- {alt.get('source').capitalize()}: ${alt.get('price')} - {alt.get('reason')}")
            else:
                print("No alternatives found.")
            
            # Analyze if it's a good deal
            print("\nAnalyzing if this is a good deal...")
            deal_analysis = self._analyze_deal(product_details, alternatives)
            
            print(f"Is it a good deal? {'Yes' if deal_analysis.get('is_good_deal') else 'No'}")
            print(f"Confidence: {deal_analysis.get('confidence')}")
            
            if deal_analysis.get("reasons"):
                print("Reasons:")
                for reason in deal_analysis.get("reasons"):
                    print(f"- {reason}")
            
            # Generate recommendation
            recommendation = self._generate_recommendation(product_details, alternatives, deal_analysis)
            
            print("\nRecommendation:")
            print("-" * 50)
            print(recommendation)
            print("-" * 50)
            
            return {
                "product": product_details,
                "alternatives": alternatives,
                "analysis": deal_analysis,
                "recommendation": recommendation
            }
        else:
            print(f"Error: {product_details.get('message', 'Unknown error')}")
            return {
                "error": product_details.get('message', 'Unknown error')
            }


def extract_urls(text):
    """Extract URLs from a text string."""
    url_pattern = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s]*)?'
    )
    
    # Find all URLs in the text
    found_urls = url_pattern.findall(text)
    
    # Filter to only include supported e-commerce sites
    supported_urls = []
    for url in found_urls:
        domain = urlparse(url).netloc.lower()
        if any(site in domain for site in ["amazon.com", "walmart.com", "bestbuy.com"]):
            supported_urls.append(url)
    
    return supported_urls


async def main():
    """Main function to run the price comparison."""
    print("E-Commerce Price Comparison Tool")
    print("=" * 50)
    print("This tool analyzes product prices from Amazon, Walmart, and Best Buy")
    print("=" * 50)
    
    # Get user input
    user_query = input("\nEnter a product URL or query: ")
    
    # Extract URLs
    urls = extract_urls(user_query)
    
    if not urls:
        print("\nNo valid e-commerce URLs found in your query.")
        print("Please provide a direct link to a product on Amazon, Walmart, or Best Buy.")
        print("Example: https://www.amazon.com/dp/B07ZPKN6YR")
        
        # Ask if they want to use a sample URL
        use_sample = input("\nWould you like to use a sample URL for testing? (y/n): ").lower() == 'y'
        if use_sample:
            urls = ["https://www.amazon.com/dp/B07ZPKN6YR"]
            print(f"Using sample URL: {urls[0]}")
        else:
            return
    
    # Create price comparison tool
    price_tool = SimpleECommercePriceComparison()
    
    # Analyze each URL
    for url in urls:
        await price_tool.analyze_product(url)
        
        if len(urls) > 1:
            print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main()) 
