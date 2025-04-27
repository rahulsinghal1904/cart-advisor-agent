import asyncio
import logging
import os
import re
from typing import AsyncIterator, Dict, List, Any, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import AsyncOpenAI
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class PriceScraper:
    def __init__(self):
        """Initialize the price scraper with HTTP client."""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br"
        }
        self.timeout = 20.0
    
    async def get_product_details(self, url: str) -> Dict[str, Any]:
        """Fetch product details from the given URL."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        try:
            if "amazon.com" in domain:
                return await self.scrape_amazon(url)
            elif "walmart.com" in domain:
                return await self.scrape_walmart(url)
            elif "bestbuy.com" in domain:
                return await self.scrape_bestbuy(url)
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported website: {domain}",
                    "url": url
                }
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to scrape product: {str(e)}",
                "url": url
            }
    
    async def scrape_amazon(self, url: str) -> Dict[str, Any]:
        """Scrape product details from Amazon."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=self.timeout, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract product title
                title_elem = soup.select_one('#productTitle')
                title = title_elem.get_text().strip() if title_elem else "Unknown Product"
                
                # Extract price
                price_elem = soup.select_one('.a-price .a-offscreen')
                price_text = price_elem.get_text() if price_elem else None
                
                if not price_text:
                    # Try another selector
                    price_elem = soup.select_one('#priceblock_ourprice')
                    price_text = price_elem.get_text() if price_elem else "Price not found"
                
                # Clean price text
                if price_text:
                    price = self._extract_price(price_text)
                else:
                    price = None
                
                # Extract rating
                rating_elem = soup.select_one('span[data-hook="rating-out-of-text"]')
                rating = rating_elem.get_text().strip() if rating_elem else None
                
                if not rating:
                    # Try another selector
                    rating_elem = soup.select_one('#acrPopover')
                    rating = rating_elem.get('title', 'No ratings') if rating_elem else "No ratings"
                
                return {
                    "status": "success",
                    "source": "amazon",
                    "url": url,
                    "title": title,
                    "price": price,
                    "price_text": price_text,
                    "rating": rating
                }
                
        except Exception as e:
            logger.error(f"Error scraping Amazon {url}: {str(e)}")
            return {
                "status": "error",
                "source": "amazon",
                "message": f"Failed to scrape Amazon product: {str(e)}",
                "url": url
            }
    
    async def scrape_walmart(self, url: str) -> Dict[str, Any]:
        """Scrape product details from Walmart."""
        # Simplified - for demonstration
        return {
            "status": "success",
            "source": "walmart",
            "url": url,
            "title": "Sample Walmart Product",
            "price": 99.99,
            "price_text": "$99.99",
            "rating": "4.5 stars"
        }
    
    async def scrape_bestbuy(self, url: str) -> Dict[str, Any]:
        """Scrape product details from Best Buy."""
        # Simplified - for demonstration
        return {
            "status": "success",
            "source": "bestbuy",
            "url": url,
            "title": "Sample Best Buy Product",
            "price": 129.99,
            "price_text": "$129.99",
            "rating": "4.2 stars"
        }
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from price text."""
        if not price_text:
            return None
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', price_text)
        
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    async def find_alternatives(self, product_details: Dict[str, Any], max_results: int = 3) -> List[Dict[str, Any]]:
        """Find alternative products based on the provided product details."""
        if product_details.get("status") != "success":
            return []
        
        # For demonstration - mock alternatives
        source = product_details.get("source", "unknown")
        title = product_details.get("title", "Unknown Product")
        alternatives = []
        
        if source == "amazon":
            alternatives.append({
                "source": "walmart",
                "title": title,
                "price": round(product_details.get("price", 100) * 0.95, 2) if product_details.get("price") else None,
                "url": "https://www.walmart.com/search/?query=" + title.replace(" ", "+"),
                "is_better_deal": True,
                "reason": "5% cheaper than Amazon"
            })
        elif source == "walmart":
            alternatives.append({
                "source": "amazon",
                "title": title,
                "price": round(product_details.get("price", 100) * 1.02, 2) if product_details.get("price") else None,
                "url": "https://www.amazon.com/s?k=" + title.replace(" ", "+"),
                "is_better_deal": False,
                "reason": "2% more expensive than Walmart"
            })
        elif source == "bestbuy":
            alternatives.append({
                "source": "amazon",
                "title": title,
                "price": round(product_details.get("price", 100) * 0.97, 2) if product_details.get("price") else None,
                "url": "https://www.amazon.com/s?k=" + title.replace(" ", "+"),
                "is_better_deal": True,
                "reason": "3% cheaper than Best Buy"
            })
        
        return alternatives

    async def analyze_deal(self, product_details: Dict[str, Any], alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze if the product is a good deal based on price and alternatives."""
        if product_details.get("status") != "success" or product_details.get("price") is None:
            return {
                "is_good_deal": False,
                "confidence": "low",
                "reasons": ["Unable to determine price information accurately"]
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


class ModelProvider:
    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5"
    ):
        """Initialize model provider for queries."""
        # Model settings
        self.api_key = api_key or os.getenv("MODEL_API_KEY", "default_key")
        self.base_url = base_url
        self.model = model
        self.temperature = 0.0
        self.max_tokens = None
        self.date_context = datetime.now().strftime("%Y-%m-%d")

        # Set up system prompt
        self.system_prompt = (
            "You are an expert e-commerce price comparison assistant that helps users determine "
            "if product prices represent good deals. You have knowledge of typical pricing across "
            "Amazon, Walmart, and Best Buy. You can analyze prices, suggest alternatives, and "
            "help users make informed purchasing decisions. Today's date is " + self.date_context
        )
        
        # Initialize API client
        try:
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
            
    async def query_stream(self, query: str) -> AsyncIterator[str]:
        """Sends query to model and yields the response in chunks."""
        if not self.client:
            # Fallback response if client initialization failed
            yield "I can't connect to the AI model right now. Here's my analysis based on the data:"
            return

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": query}
            ]

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error during model query: {str(e)}")
            yield f"Sorry, I encountered an error while analyzing the product: {str(e)}"


class MockModelProvider:
    """A mock model provider for testing without an actual OpenAI API key."""
    
    def __init__(self, *args, **kwargs):
        self.system_prompt = "Mock model provider for testing"
    
    async def query_stream(self, query: str) -> AsyncIterator[str]:
        """Returns a mocked streaming response."""
        price_info = "price information" in query.lower()
        product_info = "product details" in query.lower()
        
        if price_info and product_info:
            response = "Based on my analysis, this doesn't seem to be a particularly good deal. Walmart has this product for about 5% less, which would be a better option. I'd recommend checking there before making a purchase."
        else:
            response = "I need a specific product URL to analyze whether it's a good deal. Please provide a link to an Amazon, Walmart, or Best Buy product you're interested in."
        
        # Split the response into chunks to simulate streaming
        chunks = [response[i:i+10] for i in range(0, len(response), 10)]
        
        for chunk in chunks:
            await asyncio.sleep(0.05)  # Simulate network delay
            yield chunk


async def analyze_product(url: str, use_mock: bool = False):
    """Analyze a product URL and determine if it's a good deal."""
    print(f"Analyzing product: {url}")
    print("-" * 50)
    
    # Initialize components
    price_scraper = PriceScraper()
    
    if use_mock:
        model_provider = MockModelProvider()
    else:
        api_key = os.getenv("MODEL_API_KEY")
        if not api_key or api_key in ["your_openai_api_key_here", "sk-example"]:
            print("WARNING: Using mock provider since no valid API key was found")
            model_provider = MockModelProvider()
        else:
            model_provider = ModelProvider(api_key=api_key)
    
    # Process the product URL
    print("Fetching product details...")
    product_details = await price_scraper.get_product_details(url)
    
    if product_details.get("status") == "success":
        print(f"Product: {product_details.get('title')}")
        print(f"Price: {product_details.get('price_text')}")
        print(f"Rating: {product_details.get('rating')}")
        print("\nSearching for alternatives...")
        
        # Find alternatives
        alternatives = await price_scraper.find_alternatives(product_details)
        
        if alternatives:
            print("\nAlternative options found:")
            for alt in alternatives:
                print(f"- {alt.get('source').capitalize()}: ${alt.get('price')} - {alt.get('reason')}")
        else:
            print("No alternatives found.")
        
        # Analyze if it's a good deal
        print("\nAnalyzing if this is a good deal...")
        deal_analysis = await price_scraper.analyze_deal(product_details, alternatives)
        
        print(f"Is it a good deal? {'Yes' if deal_analysis.get('is_good_deal') else 'No'}")
        print(f"Confidence: {deal_analysis.get('confidence')}")
        
        if deal_analysis.get("reasons"):
            print("Reasons:")
            for reason in deal_analysis.get("reasons"):
                print(f"- {reason}")
        
        # Generate analysis from model
        print("\nGenerating detailed analysis...")
        summary_prompt = f"""
Analyze this product and determine if it's a good deal:

Product Details:
- Title: {product_details.get('title')}
- Price: {product_details.get('price_text')}
- Source: {product_details.get('source')}
- Rating: {product_details.get('rating')}

Alternative Options:
{json.dumps(alternatives, indent=2)}

Deal Analysis:
{json.dumps(deal_analysis, indent=2)}

Provide your analysis on whether this is a good deal and explain why. If there are better alternatives, mention them.
"""
        
        print("\nAI Analysis:")
        print("-" * 50)
        async for chunk in model_provider.query_stream(summary_prompt):
            print(chunk, end="", flush=True)
        print("\n" + "-" * 50)
    else:
        print(f"Error: {product_details.get('message', 'Unknown error')}")


async def main():
    """Main function to run the price comparison."""
    print("E-Commerce Price Comparison Tool")
    print("=" * 50)
    print("This tool analyzes product prices from Amazon, Walmart, and Best Buy")
    print("=" * 50)
    
    url = input("\nEnter a product URL from Amazon, Walmart, or Best Buy: ")
    if not url:
        # Use a default URL for testing
        url = "https://www.amazon.com/dp/B07ZPKN6YR"
        print(f"Using example URL: {url}")
    
    use_mock = input("\nUse mock AI responses? (y/n, default: y): ").lower() != 'n'
    
    await analyze_product(url, use_mock)


# Import json for the detailed analysis
import json

if __name__ == "__main__":
    asyncio.run(main()) 