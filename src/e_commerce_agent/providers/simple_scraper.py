"""
Simple scraper implementations for various retailers.
These scrapers are designed to mimic the flow and pattern of Amazon's scraper.
"""
import re
import json
import logging
import httpx
import asyncio
import random
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class SimpleScraper:
    """Base class for simple scrapers that mimic Amazon's pattern."""
    
    def __init__(self):
        """Initialize the scraper with common settings."""
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        ]
        self.headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Cache-Control": "max-age=0"
        }
    
    async def extract_product_data(self, url: str) -> Dict[str, Any]:
        """Scrape product details from the given URL."""
        # This should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement extract_product_data")
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a reasonable product title from the URL as fallback."""
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
                raw_title = segments[-1]
                
                # Replace hyphens and underscores with spaces
                title = re.sub(r'[-_]', ' ', raw_title)
                
                # Capitalize words
                title = ' '.join(word.capitalize() for word in title.split())
                
                # Clean up whitespace
                title = re.sub(r'\s+', ' ', title).strip()
                
                if len(title) > 5:  # If we have something meaningful
                    return title
            
            # Fallback: Look for product name in query parameters
            query = urlparse(url).query
            query_params = parse_qs(query)
            
            for param_name in ['title', 'name', 'product', 'item']:
                if param_name in query_params:
                    return query_params[param_name][0]
            
            # Last resort
            for segment in segments:
                if len(segment) > 5 and not segment.isdigit():
                    return re.sub(r'[-_]', ' ', segment).title()
                    
            # Ultimate fallback
            return "Unknown Product"
            
        except Exception as e:
            logger.error(f"Error extracting title from URL: {str(e)}")
            return "Unknown Product"


class TargetScraper(SimpleScraper):
    """Simple scraper for Target products that mimics Amazon's successful pattern."""
    
    async def extract_product_data(self, url: str) -> Dict[str, Any]:
        """Scrape product details from Target URL with multiple fallback techniques."""
        logger.info(f"Scraping Target product: {url}")
        
        # Extract item ID from URL if possible
        item_id = self._extract_target_item_id(url)
        if item_id:
            logger.info(f"Extracted Target item ID: {item_id}")
        
        # Extract a basic title from the URL as fallback
        title_from_url = self._extract_title_from_url(url)
        
        # Use browser-based extraction (most reliable)
        try:
            logger.info("Attempting browser-based extraction for Target")
            async with async_playwright() as p:
                # Use Chromium browser with longer timeout
                browser = await p.chromium.launch(headless=True)
                
                # Create context with realistic browser settings
                context = await browser.new_context(
                    user_agent=random.choice(self.user_agents),
                    viewport={"width": 1280, "height": 800},
                    device_scale_factor=1,
                    locale="en-US"
                )
                
                # Add stealth script to avoid detection
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """)
                
                # Create page with longer timeout
                page = await context.new_page()
                
                try:
                    # Navigate to product page with longer timeout
                    logger.info(f"Navigating to Target URL: {url}")
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    
                    # Wait for key elements to appear
                    logger.info("Waiting for product elements to load on Target page")
                    
                    # Wait for title element to appear
                    title_element = None
                    try:
                        title_element = await page.wait_for_selector('[data-test="product-title"]', 
                                                                     state="visible", timeout=10000)
                        logger.info("Found product title element")
                    except Exception as e:
                        logger.warning(f"Title element not found: {str(e)}")
                    
                    # Take screenshot for debugging
                    await page.screenshot(path="/tmp/target_debug.png")
                    logger.info("Took screenshot of Target page for debugging")
                    
                    # Extract product details using JavaScript for reliability
                    logger.info("Extracting product data from Target page")
                    product_data = await page.evaluate("""
                        () => {
                            // Get product title
                            let title = null;
                            const titleElement = document.querySelector('[data-test="product-title"]');
                            if (titleElement) {
                                title = titleElement.textContent.trim();
                            }
                            
                            // Get product price with fallbacks
                            let price = null;
                            let priceText = null;
                            
                            // Try main price selector
                            const priceElement = document.querySelector('[data-test="product-price"]');
                            if (priceElement) {
                                priceText = priceElement.textContent.trim();
                                // Extract numeric price if possible
                                const priceMatch = priceText.match(/\\$([\\d,]+\\.?\\d*)/);
                                if (priceMatch) {
                                    price = parseFloat(priceMatch[1].replace(',', ''));
                                }
                            }
                            
                            // If price not found, try broader search
                            if (!price) {
                                // Find any element with $ that looks like a price
                                const allElements = document.querySelectorAll('*');
                                for (const el of allElements) {
                                    const text = el.textContent || '';
                                    if (text && 
                                        text.includes('$') && 
                                        text.length < 20 &&
                                        !text.toLowerCase().includes('shipping') &&
                                        !text.toLowerCase().includes('free delivery')) {
                                        
                                        const match = text.match(/\\$([\\d,]+\\.?\\d*)/);
                                        if (match) {
                                            price = parseFloat(match[1].replace(',', ''));
                                            priceText = text.trim();
                                            break;
                                        }
                                    }
                                }
                            }
                            
                            // Get ratings
                            let rating = null;
                            const ratingElement = document.querySelector('[data-test="ratings"]');
                            if (ratingElement) {
                                rating = ratingElement.textContent.trim();
                            }
                            
                            // Get availability
                            let availability = null;
                            const availabilityElement = document.querySelector(
                                '[data-test="shipItButton"], [data-test="fulfillment-cell"]'
                            );
                            if (availabilityElement) {
                                availability = availabilityElement.textContent.trim();
                                // If button is present, it's probably in stock
                                if (availabilityElement.tagName.toLowerCase() === 'button') {
                                    availability = "In Stock";
                                }
                            }
                            
                            // Get image URL
                            let imageUrl = null;
                            const imageElement = document.querySelector('[data-test="product-image"] img');
                            if (imageElement && imageElement.src) {
                                imageUrl = imageElement.src;
                            }
                            
                            // Get product description
                            let description = null;
                            const descElement = document.querySelector('[data-test="item-details-description"]');
                            if (descElement) {
                                description = descElement.textContent.trim();
                            }
                            
                            return {
                                title,
                                price,
                                priceText,
                                rating,
                                availability,
                                imageUrl,
                                description,
                                pageTitle: document.title
                            };
                        }
                    """)
                    
                    # Log what we found
                    logger.info(f"Raw data from Target page: title={product_data.get('title')}, " +
                               f"price={product_data.get('price')}, price_text={product_data.get('priceText')}")
                    
                    # Extract values from the page data
                    title = product_data.get('title') or title_from_url
                    price = product_data.get('price')
                    price_text = product_data.get('priceText') or "Price not available"
                    rating = product_data.get('rating') or "No ratings"
                    availability = product_data.get('availability') or "Unknown"
                    image_url = product_data.get('imageUrl')
                    description = product_data.get('description')
                    
                    # If we couldn't get a good title, try from the page title
                    if (not title or len(title) < 3) and product_data.get('pageTitle'):
                        title = product_data.get('pageTitle').split(' : Target')[0].strip()
                    
                    # Final fallback to URL-based title
                    if not title or len(title) < 3:
                        title = title_from_url
                    
                    logger.info(f"Successfully extracted Target data: {title}, price: {price}")
                    
                    return {
                        "status": "success",
                        "source": "target",
                        "url": url,
                        "title": title,
                        "price": price,
                        "price_text": price_text,
                        "rating": rating,
                        "availability": availability,
                        "image_url": image_url,
                        "description": description,
                        "item_id": item_id
                    }
                
                except Exception as e:
                    logger.error(f"Error during Target page processing: {str(e)}")
                    # Continue to fallback methods
                
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Browser-based extraction failed for Target: {str(e)}")
        
        # Fallback to HTTP method if browser approach failed
        try:
            logger.info("Attempting HTTP-based extraction for Target")
            async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
                headers = {
                    "User-Agent": random.choice(self.user_agents),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache"
                }
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    # Parse HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract title
                    title = title_from_url
                    title_element = soup.select_one('[data-test="product-title"]')
                    if title_element:
                        title = title_element.text.strip()
                    
                    # Extract price
                    price = None
                    price_text = "Price not available"
                    price_element = soup.select_one('[data-test="product-price"]')
                    if price_element:
                        price_text = price_element.text.strip()
                        price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))
                    
                    # Extract rating
                    rating = "No ratings"
                    rating_element = soup.select_one('[data-test="ratings"]')
                    if rating_element:
                        rating = rating_element.text.strip()
                    
                    # Extract availability
                    availability = "Unknown"
                    availability_element = soup.select_one('[data-test="fulfillment"]')
                    if availability_element:
                        availability = availability_element.text.strip()
                    
                    # Extract image
                    image_url = None
                    image_element = soup.select_one('[data-test="product-image"] img')
                    if image_element and image_element.has_attr('src'):
                        image_url = image_element['src']
                    
                    # Extract description
                    description = None
                    description_element = soup.select_one('[data-test="item-details-description"]')
                    if description_element:
                        description = description_element.text.strip()
                    
                    logger.info(f"Successfully extracted Target data via HTTP method: {title}")
                    
                    return {
                        "status": "success",
                        "source": "target",
                        "url": url,
                        "title": title,
                        "price": price,
                        "price_text": price_text,
                        "rating": rating,
                        "availability": availability,
                        "image_url": image_url,
                        "description": description,
                        "item_id": item_id
                    }
                else:
                    logger.warning(f"HTTP request to Target returned status code: {response.status_code}")
        
        except Exception as e:
            logger.error(f"HTTP-based extraction failed for Target: {str(e)}")
        
        # Last resort - return basic info if all else fails
        logger.warning("All Target extraction methods failed, returning basic info")
        return {
            "status": "success",
            "source": "target",
            "url": url,
            "title": title_from_url,
            "price": None,
            "price_text": "Price not available",
            "rating": "No ratings",
            "availability": "Unknown",
            "item_id": item_id
        }
    
    def _extract_target_item_id(self, url: str) -> Optional[str]:
        """Extract item ID from Target URL."""
        try:
            # Try to find item ID in the URL query parameters
            parsed_url = urlparse(url)
            path = parsed_url.path
            
            # Format like /p/product-name/-/A-12345678
            match = re.search(r'A-(\d+)', path)
            if match:
                return match.group(1)
            
            # Also check query parameters
            query_params = parse_qs(parsed_url.query)
            if 'preselect' in query_params:
                return query_params['preselect'][0]
                
            return None
        except Exception:
            return None


class BestBuyScraper(SimpleScraper):
    """Simple scraper for Best Buy products that mimics Amazon's successful pattern."""
    
    async def extract_product_data(self, url: str) -> Dict[str, Any]:
        """Scrape product details from Best Buy URL with multiple fallback techniques."""
        logger.info(f"Scraping Best Buy product: {url}")
        
        # Extract SKU ID from URL if possible
        sku_id = self._extract_bestbuy_sku_id(url)
        if sku_id:
            logger.info(f"Extracted Best Buy SKU ID: {sku_id}")
        
        # Extract a basic title from the URL as fallback
        title_from_url = self._extract_title_from_bestbuy_url(url)
        
        # Use browser-based extraction (most reliable)
        try:
            logger.info("Attempting browser-based extraction for Best Buy")
            async with async_playwright() as p:
                # Use Chromium browser with longer timeout
                browser = await p.chromium.launch(headless=True)
                
                # Create context with realistic browser settings
                context = await browser.new_context(
                    user_agent=random.choice(self.user_agents),
                    viewport={"width": 1280, "height": 800},
                    device_scale_factor=1,
                    locale="en-US"
                )
                
                # Add stealth script to avoid detection
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """)
                
                # Create page
                page = await context.new_page()
                
                try:
                    # Navigate to product page with longer timeout
                    logger.info(f"Navigating to Best Buy URL: {url}")
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    
                    # Wait for key elements to appear
                    logger.info("Waiting for product elements to load on Best Buy page")
                    
                    # Try different selectors for product elements
                    selectors = [
                        '.sku-title h1',
                        '.heading-5',
                        '.priceView-customer-price',
                        '.pricing-price'
                    ]
                    
                    # Wait for any selector to become visible
                    for selector in selectors:
                        try:
                            await page.wait_for_selector(selector, state="visible", timeout=5000)
                            logger.info(f"Found Best Buy product element with selector: {selector}")
                            break
                        except Exception:
                            continue
                    
                    # Take screenshot for debugging
                    await page.screenshot(path="/tmp/bestbuy_debug.png")
                    logger.info("Took screenshot of Best Buy page for debugging")
                    
                    # Extract product details using JavaScript for reliability
                    logger.info("Extracting product data from Best Buy page")
                    product_data = await page.evaluate("""
                        () => {
                            // Get product title
                            let title = null;
                            
                            // Try different title selectors
                            const titleSelectors = [
                                '.sku-title h1', 
                                '.heading-5',
                                'h1'
                            ];
                            
                            for (const selector of titleSelectors) {
                                const element = document.querySelector(selector);
                                if (element) {
                                    title = element.textContent.trim();
                                    if (title) break;
                                }
                            }
                            
                            // Get product price with fallbacks
                            let price = null;
                            let priceText = null;
                            
                            // Try different price selectors
                            const priceSelectors = [
                                '.priceView-customer-price span',
                                '.priceView-hero-price',
                                '.pricing-price',
                                '.price-box'
                            ];
                            
                            for (const selector of priceSelectors) {
                                const element = document.querySelector(selector);
                                if (element) {
                                    priceText = element.textContent.trim();
                                    const priceMatch = priceText.match(/\\$([\\d,]+\\.?\\d*)/);
                                    if (priceMatch) {
                                        price = parseFloat(priceMatch[1].replace(',', ''));
                                        break;
                                    }
                                }
                            }
                            
                            // If price not found, try JSON-LD data
                            if (!price) {
                                try {
                                    const jsonLdScript = document.querySelector('script[type="application/ld+json"]');
                                    if (jsonLdScript) {
                                        const data = JSON.parse(jsonLdScript.textContent);
                                        if (data.offers && data.offers.price) {
                                            price = parseFloat(data.offers.price);
                                            priceText = '$' + price.toFixed(2);
                                        }
                                    }
                                } catch (e) {
                                    console.error("Error parsing JSON-LD", e);
                                }
                            }
                            
                            // If still no price, try broader search
                            if (!price) {
                                // Find any element with $ that looks like a price
                                const allElements = document.querySelectorAll('*');
                                for (const el of allElements) {
                                    const text = el.textContent || '';
                                    if (text && 
                                        text.includes('$') && 
                                        text.length < 20 &&
                                        !text.toLowerCase().includes('shipping') &&
                                        !text.toLowerCase().includes('free')) {
                                        
                                        const match = text.match(/\\$([\\d,]+\\.?\\d*)/);
                                        if (match) {
                                            price = parseFloat(match[1].replace(',', ''));
                                            priceText = text.trim();
                                            break;
                                        }
                                    }
                                }
                            }
                            
                            // Get ratings
                            let rating = null;
                            const ratingSelectors = [
                                '.customer-rating .c-ratings-reviews-score',
                                '.customer-reviews .c-review-average'
                            ];
                            
                            for (const selector of ratingSelectors) {
                                const element = document.querySelector(selector);
                                if (element) {
                                    rating = element.textContent.trim();
                                    break;
                                }
                            }
                            
                            // Get availability
                            let availability = null;
                            
                            // Check if there's an add to cart button (indicates in stock)
                            const cartButton = document.querySelector('.fulfillment-add-to-cart-button button:not([disabled])');
                            if (cartButton) {
                                availability = "In Stock";
                            } else {
                                // Check for out of stock indicators
                                const outOfStockElement = document.querySelector('.fulfillment-shipping-fulfillment-store-detail, .oos-col');
                                if (outOfStockElement) {
                                    availability = outOfStockElement.textContent.trim();
                                }
                            }
                            
                            // Get image URL
                            let imageUrl = null;
                            const imageSelectors = [
                                '.primary-image', 
                                '.carousel-main-image img',
                                '.picture-wrapper img'
                            ];
                            
                            for (const selector of imageSelectors) {
                                const element = document.querySelector(selector);
                                if (element && element.src) {
                                    imageUrl = element.src;
                                    break;
                                }
                            }
                            
                            // Get description
                            let description = null;
                            const descElement = document.querySelector('.product-description');
                            if (descElement) {
                                description = descElement.textContent.trim();
                            }
                            
                            return {
                                title,
                                price,
                                priceText,
                                rating,
                                availability,
                                imageUrl,
                                description,
                                pageTitle: document.title
                            };
                        }
                    """)
                    
                    # Log what we found
                    logger.info(f"Raw data from Best Buy page: title={product_data.get('title')}, " +
                               f"price={product_data.get('price')}, price_text={product_data.get('priceText')}")
                    
                    # Extract values from the page data
                    title = product_data.get('title') or title_from_url
                    price = product_data.get('price')
                    price_text = product_data.get('priceText') or "Price not available"
                    rating = product_data.get('rating') or "No ratings"
                    availability = product_data.get('availability') or "Unknown"
                    image_url = product_data.get('imageUrl')
                    description = product_data.get('description')
                    
                    # If we couldn't get a good title, try from the page title
                    if (not title or len(title) < 3) and product_data.get('pageTitle'):
                        title = product_data.get('pageTitle').split(' - Best Buy')[0].strip()
                    
                    # Final fallback to URL-based title
                    if not title or len(title) < 3:
                        title = title_from_url
                    
                    logger.info(f"Successfully extracted Best Buy data: {title}, price: {price}")
                    
                    return {
                        "status": "success",
                        "source": "bestbuy",
                        "url": url,
                        "title": title,
                        "price": price,
                        "price_text": price_text,
                        "rating": rating,
                        "availability": availability,
                        "image_url": image_url,
                        "description": description,
                        "sku_id": sku_id
                    }
                
                except Exception as e:
                    logger.error(f"Error during Best Buy page processing: {str(e)}")
                    # Continue to fallback methods
                
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Browser-based extraction failed for Best Buy: {str(e)}")
        
        # Fallback to HTTP method if browser approach failed
        try:
            logger.info("Attempting HTTP-based extraction for Best Buy")
            async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
                headers = {
                    "User-Agent": random.choice(self.user_agents),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache"
                }
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    # Parse HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Try to extract JSON-LD data first (most reliable)
                    product_data = self._extract_bestbuy_json_ld(soup)
                    if product_data and product_data.get('status') == 'success':
                        logger.info(f"Successfully extracted Best Buy data via JSON-LD")
                        return product_data
                    
                    # Extract title
                    title = title_from_url
                    title_element = soup.select_one('.sku-title h1, .heading-5')
                    if title_element:
                        title = title_element.text.strip()
                    
                    # Extract price
                    price = None
                    price_text = "Price not available"
                    price_element = soup.select_one('.priceView-customer-price span, .priceView-hero-price')
                    if price_element:
                        price_text = price_element.text.strip()
                        price_match = re.search(r'\$\s*([\d,]+\.?\d*)', price_text)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))
                    
                    # Extract rating
                    rating = "No ratings"
                    rating_element = soup.select_one('.customer-rating .c-ratings-reviews-score')
                    if rating_element:
                        rating = rating_element.text.strip()
                        rating_match = re.search(r'([\d\.]+)', rating)
                        if rating_match:
                            rating = f"{rating_match.group(1)} out of 5 stars"
                    
                    # Extract availability
                    availability = "Unknown"
                    available_element = soup.select_one('.fulfillment-add-to-cart-button button')
                    if available_element and not 'disabled' in available_element.attrs:
                        availability = "In Stock"
                    else:
                        out_of_stock = soup.select_one('.fulfillment-shipping-fulfillment-store-detail, .oos-col')
                        if out_of_stock and "not available" in out_of_stock.text.lower():
                            availability = "Out of Stock"
                    
                    # Extract image URL
                    image_url = None
                    image_element = soup.select_one('.primary-image, .carousel-main-image img')
                    if image_element and image_element.has_attr('src'):
                        image_url = image_element['src']
                    
                    logger.info(f"Successfully extracted Best Buy data via HTTP method: {title}")
                    
                    return {
                        "status": "success",
                        "source": "bestbuy",
                        "url": url,
                        "title": title,
                        "price": price,
                        "price_text": price_text,
                        "rating": rating,
                        "availability": availability,
                        "image_url": image_url,
                        "sku_id": sku_id
                    }
                else:
                    logger.warning(f"HTTP request to Best Buy returned status code: {response.status_code}")
        
        except Exception as e:
            logger.error(f"HTTP-based extraction failed for Best Buy: {str(e)}")
        
        # Last resort - return basic info if all else fails
        logger.warning("All Best Buy extraction methods failed, returning basic info")
        return {
            "status": "success",
            "source": "bestbuy",
            "url": url,
            "title": title_from_url,
            "price": None,
            "price_text": "Price not available",
            "rating": "No ratings",
            "availability": "Unknown",
            "sku_id": sku_id
        }
    
    def _extract_bestbuy_sku_id(self, url: str) -> Optional[str]:
        """Extract SKU ID from Best Buy URL."""
        try:
            # Try multiple patterns
            patterns = [
                r'/skus/(\d+)',
                r'/p/(\d+)',
                r'skuId=(\d+)',
                r'\.p\?id=(\d+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            return None
        except Exception:
            return None
    
    def _extract_bestbuy_json_ld(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract structured data from Best Buy product page."""
        try:
            json_ld_scripts = soup.select('script[type="application/ld+json"]')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Handle different schema formats
                    if isinstance(data, list):
                        data = data[0]
                    
                    if data.get("@type") == "Product":
                        # Extract product details
                        title = data.get("name")
                        
                        # Extract price
                        price = None
                        price_text = None
                        if "offers" in data:
                            offers = data["offers"]
                            if isinstance(offers, dict):
                                price = offers.get("price")
                                if price:
                                    price = float(price)
                                    price_text = f"${price}"
                            elif isinstance(offers, list) and len(offers) > 0:
                                offer = offers[0]
                                price = offer.get("price")
                                if price:
                                    price = float(price)
                                    price_text = f"${price}"
                        
                        # Extract rating
                        rating = None
                        if "aggregateRating" in data:
                            rating_value = data["aggregateRating"].get("ratingValue")
                            if rating_value:
                                rating = f"{rating_value} out of 5 stars"
                        
                        # Extract image
                        image_url = None
                        if "image" in data:
                            image = data["image"]
                            if isinstance(image, list) and len(image) > 0:
                                image_url = image[0]
                            else:
                                image_url = image
                        
                        # Create result
                        if title:
                            return {
                                "status": "success",
                                "source": "bestbuy",
                                "title": title,
                                "price": price,
                                "price_text": price_text or "Price not available",
                                "rating": rating or "No ratings",
                                "availability": "In Stock", # Default assumption from JSON-LD
                                "image_url": image_url
                            }
                except Exception as e:
                    logger.warning(f"Error parsing Best Buy JSON-LD data: {e}")
                    continue
            
            return None
        except Exception as e:
            logger.error(f"Error extracting Best Buy JSON-LD: {e}")
            return None
    
    def _extract_title_from_bestbuy_url(self, url: str) -> str:
        """Extract product title from Best Buy URL."""
        try:
            # Best Buy URLs often have the product name in them
            # Format: /site/product-name/1234567.p
            parsed_url = urlparse(url)
            path = parsed_url.path
            
            # Extract product name segment
            parts = path.split('/')
            for part in parts:
                if len(part) > 5 and part.endswith('.p'):
                    # Remove the .p and any ID at the end
                    name_part = re.sub(r'\d+\.p$', '', part)
                    # Clean up the name
                    name_part = name_part.replace('-', ' ').strip()
                    if name_part:
                        return name_part.title()
            
            # Try a different approach - extract from the last significant path part
            significant_parts = [p for p in parts if len(p) > 3 and not p.startswith('.')]
            if significant_parts:
                name_part = significant_parts[-1]
                # Remove any trailing ID or extension
                name_part = re.sub(r'[\d\.]+[a-z]?$', '', name_part)
                # Clean up the name
                name_part = name_part.replace('-', ' ').strip()
                if name_part:
                    return name_part.title()
            
            # Fallback to generic extraction
            return self._extract_title_from_url(url)
                
        except Exception:
            return "Unknown Best Buy Product" 