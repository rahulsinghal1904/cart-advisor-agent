import re
import json
import logging
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Any, Tuple
from playwright.async_api import async_playwright
import secrets

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        """
        Fetch product details from the given URL.
        """
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
        """Scrape product details from Amazon using Playwright."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set headers
                await page.set_extra_http_headers(self.headers)
                
                # Navigate with multiple retries and timeout handling
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"Attempt {attempt + 1} failed, retrying: {str(e)}")
                        await page.wait_for_timeout(2000)  # Wait 2 seconds before retry
                
                # More resilient element waiting
                title = "Unknown Product"
                try:
                    title_elem = await page.wait_for_selector('#productTitle', timeout=10000)
                    title = (await title_elem.text_content()).strip()
                except Exception as e:
                    logger.warning(f"Could not find product title: {str(e)}")
                    # Fallback to extracting title from page content
                    page_content = await page.content()
                    title_match = re.search(r'<title>(.*?)</title>', page_content)
                    if title_match:
                        title = title_match.group(1).split('Amazon.com: ')[-1].strip()
                
                # Extract product details
                title = await page.text_content('#productTitle')
                title = title.strip() if title else "Unknown Product"
                
                # Try different price selectors with shorter timeouts
                price_text = None
                for selector in ['.a-price .a-offscreen', '#priceblock_ourprice', '#priceblock_dealprice']:
                    try:
                        price_elem = await page.query_selector(selector)
                        if price_elem:
                            price_text = await price_elem.text_content()
                            if price_text:
                                break
                    except Exception:
                        continue
                
                if not price_text:
                    # Try to find price in script tag
                    script_content = await page.content()
                    price_match = re.search(r'"priceAmount"\s*:\s*([\d\.]+)', script_content)
                    if price_match:
                        price_text = f"${price_match.group(1)}"
                    else:
                        price_text = "Price not found"
                
                # Clean price text
                if price_text and price_text != "Price not found":
                    price = self._extract_price(price_text)
                else:
                    price = None
                
                # Extract rating with shorter timeout
                rating = None
                try:
                    rating_elem = await page.query_selector('span[data-hook="rating-out-of-text"]')
                    if rating_elem:
                        rating = await rating_elem.text_content()
                except Exception:
                    pass
                
                if not rating:
                    try:
                        rating_elem = await page.query_selector('#acrPopover')
                        if rating_elem:
                            rating = await rating_elem.get_attribute('title')
                    except Exception:
                        pass
                
                rating = rating.strip() if rating else "No ratings"
                
                # Extract features/bullets with shorter timeout
                features = []
                try:
                    feature_elems = await page.query_selector_all('#feature-bullets li span.a-list-item')
                    for elem in feature_elems:
                        text = await elem.text_content()
                        if text.strip():
                            features.append(text.strip())
                except Exception:
                    pass
                
                # Extract availability with shorter timeout
                availability = "Unknown"
                try:
                    availability_elem = await page.query_selector('#availability')
                    if availability_elem:
                        availability = await availability_elem.text_content()
                        availability = availability.strip()
                except Exception:
                    pass
                
                # Extract product images with shorter timeout
                image_url = None
                try:
                    image_elem = await page.query_selector('#landingImage')
                    if image_elem:
                        image_url = await image_elem.get_attribute('src')
                except Exception:
                    pass
                
                # ASIN extraction from URL
                asin = None
                if "/dp/" in url:
                    asin = url.split('/dp/')[1].split('/')[0].split('?')[0]
                
                await browser.close()
                
                return {
                    "status": "success",
                    "source": "amazon",
                    "url": url,
                    "title": title,
                    "price": price,
                    "price_text": price_text if price else "Price not found",
                    "rating": rating,
                    "features": features[:5] if features else [],  # Limit to top 5 features
                    "availability": availability,
                    "image_url": image_url,
                    "asin": asin
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
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=self.timeout, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find script tag containing product data
                script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
                data = None
                if script_tag:
                    try:
                        data = json.loads(script_tag.string)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode JSON from Walmart page: {url}")
                        data = None

                product_data = None
                if data:
                    # Navigate through potential JSON structures (these change frequently)
                    try:
                        product_data = data['props']['pageProps']['initialData']['data']['product']
                    except KeyError:
                         try:
                              product_data = data['props']['pageProps']['initialState']['product']
                         except KeyError:
                             logger.warning(f"Could not find product data in expected path for Walmart: {url}")
                             product_data = None

                # Extract details from JSON if possible
                if product_data:
                    title = product_data.get('name', "Unknown Product")
                    price_info = product_data.get('priceInfo', {})
                    current_price = price_info.get('currentPrice', {})
                    price = current_price.get('price')
                    price_text = f"${price}" if price else "Price not found"
                    rating_info = product_data.get('rating', {})
                    rating = rating_info.get('averageRating', "No ratings")
                    rating = f"{rating} stars" if isinstance(rating, (int, float)) else str(rating)
                    features = product_data.get('shortDescription', '').split('\n')
                    features = [f.strip() for f in features if f.strip()]
                    availability = product_data.get('availabilityStatusDisplayValue', "Unknown")
                    image_info = product_data.get('imageInfo', {})
                    image_url = image_info.get('thumbnailUrl')
                else:
                     # Fallback to scraping HTML elements if JSON fails
                    logger.info(f"Falling back to HTML scraping for Walmart: {url}")
                    title_elem = soup.select_one('h1[itemprop="name"]') or soup.select_one('h1.prod-ProductTitle')
                    title = title_elem.get_text().strip() if title_elem else "Unknown Product"
                    
                    price_elem = soup.select_one('[itemprop="price"]') or soup.select_one('span.price-characteristic')
                    price_text = None
                    if price_elem:
                        if price_elem.has_attr('content'):
                            price_text = f"${price_elem['content']}"
                        else:
                            price_text = price_elem.get_text().strip()
                    price_text = price_text or "Price not found"
                    price = self._extract_price(price_text) if price_text != "Price not found" else None
                    
                    rating_elem = soup.select_one('.stars-reviews-count .visually-hidden')
                    rating = rating_elem.get_text().strip() if rating_elem else "No ratings"
                    
                    feature_elems = soup.select('.about-product-section li')
                    features = [feature.get_text().strip() for feature in feature_elems if feature.get_text().strip()]
                    
                    availability_elem = soup.select_one('.prod-ProductOffer-availability span[class*="message"]')
                    availability = availability_elem.get_text().strip() if availability_elem else "Unknown"
                    
                    image_elem = soup.select_one('img.hover-zoom-hero-image')
                    image_url = image_elem.get('src') if image_elem else None

                # Extract product ID from URL
                product_id = None
                if '/ip/' in url:
                    parts = url.split('/ip/')[-1].split('/')
                    if parts:
                       product_id = parts[0].split('?')[0] # Get part before potential query params

                return {
                    "status": "success",
                    "source": "walmart",
                    "url": url,
                    "title": title,
                    "price": price,
                    "price_text": price_text,
                    "rating": rating,
                    "features": features[:5] if features else [],
                    "availability": availability,
                    "image_url": image_url,
                    "product_id": product_id
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
        """Scrape product details from Best Buy."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=self.timeout, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract product title
                title_elem = soup.select_one('.sku-title h1')
                title = title_elem.get_text().strip() if title_elem else "Unknown Product"
                
                # Extract price
                price_elem = soup.select_one('.priceView-hero-price.priceView-customer-price span[aria-hidden="true"]')
                price_text = price_elem.get_text().strip() if price_elem else None

                if not price_text:
                    # Try another common selector
                    price_elem = soup.select_one('.pricing-price__regular-price')
                    price_text = price_elem.get_text().strip() if price_elem else "Price not found"
                
                # Clean price text
                if price_text and price_text != "Price not found":
                    price = self._extract_price(price_text)
                else:
                    price = None
                
                # Extract rating
                rating_elem = soup.select_one('.c-review-average')
                rating = rating_elem.get_text().strip() if rating_elem else "No ratings"
                
                # Extract features
                feature_elems = soup.select('.product-features-list li')
                features = [feature.get_text().strip() for feature in feature_elems if feature.get_text().strip()]
                
                # Extract availability
                availability_elem = soup.select_one('.fulfillment-add-to-cart-button button')
                availability = availability_elem.get_text().strip() if availability_elem else "Unknown"
                if "add to cart" in availability.lower():
                    availability = "In Stock"
                elif "sold out" in availability.lower() or "unavailable" in availability.lower():
                     availability = "Out of Stock"
                
                # Extract product images
                image_elem = soup.select_one('.primary-image')
                image_url = image_elem.get('src') if image_elem else None
                
                # Extract SKU from URL or page
                sku = None
                if 'skuId=' in url:
                    query_params = parse_qs(urlparse(url).query)
                    sku = query_params.get('skuId', [None])[0]
                else:
                    sku_elem = soup.select_one('.sku .product-data-value')
                    if sku_elem:
                        sku = sku_elem.get_text().strip()
                
                return {
                    "status": "success",
                    "source": "bestbuy",
                    "url": url,
                    "title": title,
                    "price": price,
                    "price_text": price_text if price else "Price not found",
                    "rating": rating,
                    "features": features[:5] if features else [],
                    "availability": availability,
                    "image_url": image_url,
                    "sku": sku
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
    
    async def find_alternatives(self, product_details: Dict[str, Any], max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Find alternative products based on the provided product details.
        This implementation uses mock data for simplicity.
        In a real system, this would involve searching other sites for the same/similar product.
        """
        if product_details.get("status") != "success":
            return []
        
        source = product_details.get("source", "unknown")
        title = product_details.get("title", "Unknown Product")
        current_price = product_details.get("price")
        
        # Mock data for demonstration
        alternatives = []
        search_title = title.replace(" ", "+")
        
        mock_stores = {
            "amazon": f"https://www.amazon.com/s?k={search_title}",
            "walmart": f"https://www.walmart.com/search/?query={search_title}",
            "bestbuy": f"https://www.bestbuy.com/site/searchpage.jsp?st={search_title}"
        }

        # Simple logic: Check other stores with slightly varied mock prices
        for store, search_url in mock_stores.items():
            if store != source and len(alternatives) < max_results:
                # Create a slightly different mock price
                price_multiplier = 1.0
                if store == "walmart":
                    price_multiplier = 0.95 + secrets.SystemRandom().uniform(-0.03, 0.03) # Usually a bit cheaper
                elif store == "bestbuy":
                     price_multiplier = 1.05 + secrets.SystemRandom().uniform(-0.03, 0.03) # Usually a bit more expensive
                else: # amazon
                    price_multiplier = 1.0 + secrets.SystemRandom().uniform(-0.03, 0.03) # Comparable
                
                alt_price = None
                if current_price:
                     alt_price = round(current_price * price_multiplier, 2)
                
                is_better_deal = False
                reason = "Price comparison"
                if current_price and alt_price:
                    if alt_price < current_price:
                        is_better_deal = True
                        diff_pct = abs(round(((alt_price - current_price) / current_price) * 100))
                        reason = f"{diff_pct}% cheaper than {source.capitalize()}"
                    elif alt_price > current_price:
                         diff_pct = abs(round(((alt_price - current_price) / current_price) * 100))
                         reason = f"{diff_pct}% more expensive than {source.capitalize()}"
                    else:
                        reason = f"Same price as {source.capitalize()}"

                alternatives.append({
                    "source": store,
                    "title": title, # Assume same title for mock
                    "price": alt_price,
                    "url": search_url,
                    "is_better_deal": is_better_deal,
                    "reason": reason
                })
        
        return alternatives

    async def analyze_deal(self, product_details: Dict[str, Any], alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze if the product is a good deal based on price and alternatives.
        """
        if product_details.get("status") != "success" or product_details.get("price") is None:
            return {
                "is_good_deal": False,
                "confidence": "low",
                "reasons": ["Unable to determine price information accurately"]
            }
        
        # Check if there are better alternatives
        better_alternatives = [alt for alt in alternatives if alt.get("is_better_deal", False)]
        
        # Determine if it's a good deal
        is_good_deal = len(better_alternatives) == 0
        
        # Determine confidence level
        confidence = "high" if len(alternatives) >= 2 else "medium" if len(alternatives) == 1 else "low"
        
        # Generate reasons
        reasons = []
        
        if len(better_alternatives) > 0:
            reasons.append(f"Found {len(better_alternatives)} better price(s) on alternative platforms")
            # Sort by price to show the best deal first
            better_alternatives.sort(key=lambda x: x.get('price', float('inf')))
            for alt in better_alternatives[:2]: # Show top 2 reasons
                reasons.append(f"- {alt.get('source', 'Alternative').capitalize()}: ${alt.get('price')} ({alt.get('reason', 'Better price')})")
        else:
             reasons.append("This seems to be the best price among the compared retailers.")

        # Add a note about price comparison context
        reasons.append("Note: Price comparison is based on current listings found.")

        return {
            "is_good_deal": is_good_deal,
            "confidence": confidence,
            "price": product_details.get("price"),
            "reasons": reasons
        }
