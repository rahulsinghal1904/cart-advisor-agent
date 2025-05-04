import asyncio
import json
import sys
import os
import logging
import httpx
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, Optional
import time
import secrets

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleScraper:
    """A simplified scraper to test Walmart and Best Buy scrapers without dependencies."""
    
    def __init__(self):
        """Initialize the scraper with HTTP client."""
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0"
        ]
        
        self.headers = {
            "User-Agent": secrets.choice(self.user_agents),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.google.com/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "DNT": "1"
        }
        
        self.cookies = {
            # Common cookies that might help bypass bot detection
            "session-id": f"{secrets.SystemRandom().randint(100000000, 999999999)}",
            "session-token": f"{secrets.SystemRandom().randint(10000000, 99999999)}-{secrets.SystemRandom().randint(1000000, 9999999)}",
            "csm-hit": f"tb:{secrets.SystemRandom().randint(100000000000, 999999999999)}+s-{secrets.SystemRandom().randint(100000000000, 999999999999)}|{secrets.SystemRandom().randint(10000000000, 99999999999)}"
        }
        
        self.timeout = 30.0

    async def save_debug_html(self, url: str, html_content: str) -> str:
        """Save the HTML content to a file for debugging."""
        domain = url.split('/')[2].replace('www.', '')
        filename = f"debug_{domain}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        return filename

    async def scrape_walmart(self, url: str) -> Dict[str, Any]:
        """
        Scrape product details from Walmart.
        """
        try:
            # Randomize user agent to avoid detection
            headers = self.headers.copy()
            headers["User-Agent"] = secrets.choice(self.user_agents)
            
            # Add Walmart-specific headers
            headers["Referer"] = "https://www.walmart.com/"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    url, 
                    headers=headers,
                    cookies=self.cookies,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Save HTML for debugging
                debug_file = await self.save_debug_html(url, response.text)
                print(f"Saved HTML to {debug_file}")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check if we were redirected to an anti-bot page
                if "blocked" in response.url.path or "captcha" in response.url.path:
                    return {
                        "status": "error",
                        "source": "walmart",
                        "message": f"Detected anti-bot protection. Redirected to: {response.url}",
                        "url": url
                    }
                
                # Extract product title
                title_elem = soup.select_one('h1[itemprop="name"]')
                if not title_elem:
                    title_elem = soup.select_one('.prod-ProductTitle')
                if not title_elem:
                    title_elem = soup.select_one('h1.f3')  # New Walmart design
                if not title_elem:
                    title_elem = soup.find('h1')  # Last resort fallback
                title = title_elem.get_text().strip() if title_elem else "Unknown Product"
                
                # Extract price (try multiple patterns)
                price_text = None
                price = None
                
                # Try direct CSS selectors
                price_selectors = [
                    '[data-automation="product-price"]',
                    '.price-characteristic',
                    '[itemprop="price"]',
                    '.f1 .b8',  # New Walmart design
                    'span[data-testid="price-wrap"]'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        break
                
                # If direct selectors failed, try structured data
                if not price_text:
                    script_tags = soup.find_all('script', type='application/ld+json')
                    for script in script_tags:
                        try:
                            data = json.loads(script.string)
                            if isinstance(data, dict) and 'offers' in data:
                                offers = data['offers']
                                if isinstance(offers, dict) and 'price' in offers:
                                    price_text = str(offers['price'])
                                    break
                        except (json.JSONDecodeError, AttributeError):
                            continue
                
                # If we found price text, clean and convert it
                if price_text:
                    price = self._extract_price(price_text)
                
                # Extract other data
                rating = None
                rating_elem = soup.select_one('.stars-container')
                if not rating_elem:
                    rating_elem = soup.select_one('[itemprop="ratingValue"]')
                if rating_elem:
                    rating = rating_elem.get_text().strip()
                
                # Extract availability
                availability = "Unknown"
                availability_elem = soup.select_one('[data-automation="fulfillment-shipping-text"]')
                if not availability_elem:
                    availability_elem = soup.select_one('.fulfillment-shipping-text')
                if availability_elem:
                    availability = availability_elem.get_text().strip()
                
                # Extract image
                image_url = None
                image_elem = soup.select_one('img.prod-hero-image')
                if not image_elem:
                    image_elem = soup.select_one('[data-automation="image-main"]')
                if not image_elem:
                    # Try to find any large image
                    for img in soup.find_all('img'):
                        if img.get('src') and ('large' in img.get('src') or 'hero' in img.get('src')):
                            image_elem = img
                            break
                
                if image_elem:
                    image_url = image_elem.get('src')
                
                # Extract product features
                features = []
                feature_elems = soup.select('.product-description-content li')
                for elem in feature_elems[:5]:
                    features.append(elem.get_text().strip())
                
                return {
                    "status": "success" if title != "Unknown Product" else "error",
                    "source": "walmart",
                    "url": url,
                    "title": title,
                    "price": price,
                    "price_text": f"${price:.2f}" if price else "Price not available",
                    "rating": rating or "No ratings",
                    "features": features,
                    "availability": availability,
                    "image_url": image_url,
                    "debug_file": debug_file
                }
                
        except Exception as e:
            logger.error(f"Error scraping Walmart {url}: {str(e)}")
            return {
                "status": "error",
                "source": "walmart",
                "message": f"Failed to scrape Walmart product: {str(e)}",
                "url": url
            }
    
    async def scrape_bestbuy(self, url: str) -> Dict[str, Any]:
        """
        Scrape product details from Best Buy.
        """
        try:
            # Randomize user agent to avoid detection
            headers = self.headers.copy()
            headers["User-Agent"] = secrets.choice(self.user_agents)
            
            # Add Best Buy-specific headers
            headers["Referer"] = "https://www.bestbuy.com/"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    url, 
                    headers=headers,
                    cookies=self.cookies,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Save HTML for debugging
                debug_file = await self.save_debug_html(url, response.text)
                print(f"Saved HTML to {debug_file}")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check if we were redirected to an anti-bot page
                if "captcha" in response.url.path or "blocked" in response.url.path:
                    return {
                        "status": "error",
                        "source": "bestbuy",
                        "message": f"Detected anti-bot protection. Redirected to: {response.url}",
                        "url": url
                    }
                
                # Extract product title
                title_elem = soup.select_one('.sku-title h1')
                if not title_elem:
                    title_elem = soup.select_one('[data-track="product-title"]')
                if not title_elem:
                    title_elem = soup.find('h1')  # Last resort fallback
                title = title_elem.get_text().strip() if title_elem else "Unknown Product"
                
                # Extract price (try multiple patterns)
                price_text = None
                price = None
                
                # Try direct CSS selectors
                price_selectors = [
                    '.priceView-customer-price span',
                    '.priceView-hero-price span',
                    '[data-track="product-price"]',
                    '.priceView-price .sr-only'
                ]
                
                for selector in price_selectors:
                    price_elems = soup.select(selector)
                    for elem in price_elems:
                        text = elem.get_text().strip()
                        if '$' in text:
                            price_text = text
                            break
                    if price_text:
                        break
                
                # If direct selectors failed, try structured data
                if not price_text:
                    script_tags = soup.find_all('script', type='application/ld+json')
                    for script in script_tags:
                        try:
                            data = json.loads(script.string)
                            if isinstance(data, dict) and 'offers' in data:
                                offers = data['offers']
                                if isinstance(offers, dict) and 'price' in offers:
                                    price_text = f"${offers['price']}"
                                    break
                        except (json.JSONDecodeError, AttributeError):
                            continue
                
                # If we found price text, clean and convert it
                if price_text:
                    price = self._extract_price(price_text)
                
                # Extract other data
                rating = None
                rating_elem = soup.select_one('.customer-rating-average')
                if not rating_elem:
                    rating_elem = soup.select_one('[itemprop="ratingValue"]')
                if rating_elem:
                    rating = rating_elem.get_text().strip()
                
                # Extract availability
                availability = "Unknown"
                availability_elem = soup.select_one('.fulfillment-add-to-cart-button')
                if not availability_elem:
                    availability_elem = soup.select_one('[data-track="add-to-cart"]')
                if availability_elem:
                    availability = "In Stock"
                else:
                    availability = "Out of Stock"
                
                # Extract image
                image_url = None
                image_elem = soup.select_one('.primary-image')
                if not image_elem:
                    image_elem = soup.select_one('[data-track="product-image"]')
                if not image_elem:
                    # Try to find any large image
                    for img in soup.find_all('img'):
                        if img.get('alt') and title.lower() in img.get('alt').lower():
                            image_elem = img
                            break
                
                if image_elem:
                    image_url = image_elem.get('src')
                
                # Extract product features
                features = []
                feature_elems = soup.select('.feature-list .feature-bullets')
                if not feature_elems:
                    feature_elems = soup.select('.feature-list li')
                
                for elem in feature_elems[:5]:
                    features.append(elem.get_text().strip())
                
                return {
                    "status": "success" if title != "Unknown Product" else "error",
                    "source": "bestbuy",
                    "url": url,
                    "title": title,
                    "price": price,
                    "price_text": f"${price:.2f}" if price else "Price not available",
                    "rating": rating or "No ratings",
                    "features": features,
                    "availability": availability,
                    "image_url": image_url,
                    "debug_file": debug_file
                }
                
        except Exception as e:
            logger.error(f"Error scraping Best Buy {url}: {str(e)}")
            return {
                "status": "error",
                "source": "bestbuy",
                "message": f"Failed to scrape Best Buy product: {str(e)}",
                "url": url
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


async def test_scrapers():
    """Test the scraper implementations for Walmart and Best Buy."""
    print("Testing Walmart and Best Buy scrapers")
    print("-" * 50)
    
    # Initialize the scraper
    scraper = SimpleScraper()
    
    # Test URLs
    test_urls = [
        "https://www.walmart.com/ip/PlayStation-5-Digital-Edition-Console/493824815", 
        "https://www.walmart.com/ip/Apple-AirPods-with-Charging-Case-2nd-Generation/604342441",
        "https://www.bestbuy.com/site/apple-airpods-with-charging-case-2nd-generation-white/6084400.p?skuId=6084400", 
        "https://www.bestbuy.com/site/sony-playstation-5-console/6523167.p?skuId=6523167"
    ]
    
    # Test each URL
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        try:
            if "walmart.com" in url:
                result = await scraper.scrape_walmart(url)
            elif "bestbuy.com" in url:
                result = await scraper.scrape_bestbuy(url)
            else:
                print("Unsupported URL")
                continue
            
            # Check if we were redirected to a bot protection page
            if result.get("status") == "error" and "bot" in result.get("message", "").lower():
                print(f"Error: {result.get('message', 'Unknown error')}")
                continue
            
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"Source: {result.get('source', 'unknown')}")
            print(f"Title: {result.get('title', 'Not found')}")
            print(f"Price: {result.get('price_text', 'Not found')}")
            print(f"Rating: {result.get('rating', 'Not found')}")
            
            # Print the first few features if available
            if 'features' in result and result['features']:
                print("Features:")
                for i, feature in enumerate(result['features'][:3]):
                    print(f"  - {feature[:50]}{'...' if len(feature) > 50 else ''}")
            
            # Save detailed results to file for debugging
            domain = url.split('/')[2].replace('www.', '')
            with open(f"scraper_test_{domain}_{int(time.time())}.json", "w") as f:
                json.dump(result, f, indent=2)
                print(f"Detailed results saved to scraper_test_{domain}_{int(time.time())}.json")
            
        except Exception as e:
            print(f"Error testing {url}: {e}")


if __name__ == "__main__":
    asyncio.run(test_scrapers()) 
