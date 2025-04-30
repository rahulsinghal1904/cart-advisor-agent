import re
import json
import logging
import httpx
import base64
import io
import os
import time
import random
import tempfile
import asyncio
from PIL import Image
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Any, Tuple, BinaryIO
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from dotenv import load_dotenv

# Make pytesseract truly optional
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    from PIL import ImageEnhance, ImageFilter
    TESSERACT_AVAILABLE = True
except ImportError:
    logging.warning("pytesseract not installed. Some CAPTCHA solving capabilities will be limited.")

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class StealthScraper:
    """CAPTCHA avoidance through stealth techniques and API alternatives."""
    
    def __init__(self):
        """Initialize the stealth scraper."""
        self.temp_dir = tempfile.mkdtemp(prefix="browser_data_")
        os.makedirs(os.path.join(self.temp_dir, "user_data"), exist_ok=True)
        
        # API keys for alternative data sources
        self.rainforest_api_key = os.getenv("RAINFOREST_API_KEY")
        self.use_rainforest = self.rainforest_api_key is not None
        
        # User agent rotation
        self.desktop_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
        ]
        
        self.mobile_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        ]
        
        logger.info(f"Initialized StealthScraper with data directory: {self.temp_dir}")
        
        if not self.use_rainforest:
            logger.warning("""
                Rainforest API key not found. For more reliable product data, consider:
                1. Signing up for Rainforest Data API at https://www.rainforestapi.com/
                2. Adding your API key as RAINFOREST_API_KEY in .env file
                
                Falling back to stealth browser techniques (less reliable).
            """)
    
    async def get_amazon_product_data(self, url: str) -> Dict[str, Any]:
        """
        Get Amazon product data using the most reliable method available.
        Tries Rainforest API first, then falls back to browser techniques.
        
        Args:
            url: Amazon product URL
            
        Returns:
            Dict containing product data
        """
        # Extract ASIN from URL
        asin = self._extract_asin_from_url(url)
        if not asin:
            logger.warning(f"Could not extract ASIN from URL: {url}")
            asin = "unknown"
        
        # Try Rainforest API first if available
        if self.use_rainforest and asin != "unknown":
            try:
                logger.info(f"Attempting to fetch product data via Rainforest API for ASIN: {asin}")
                product_data = await self._get_amazon_data_from_api(asin)
                if product_data:
                    logger.info(f"Successfully retrieved product data from Rainforest API for {asin}")
                    return {
                        "status": "success",
                        "source": "amazon",
                        "url": url,
                        "title": product_data.get("title"),
                        "price": product_data.get("price", {}).get("value"),
                        "price_text": f"${product_data.get('price', {}).get('value')}" if product_data.get("price", {}).get("value") else "Price not available",
                        "rating": f"{product_data.get('rating')} out of 5 stars" if product_data.get("rating") else "No ratings",
                        "features": product_data.get("features", [])[:5],
                        "availability": product_data.get("availability", {}).get("raw_text", "Unknown"),
                        "image_url": product_data.get("main_image", {}).get("link"),
                        "asin": asin
                    }
            except Exception as e:
                logger.error(f"Error fetching from Rainforest API: {str(e)}")
        
        # Fall back to browser techniques
        logger.info(f"Falling back to browser techniques for URL: {url}")
        return await self._get_product_data_with_browser(url)
    
    async def _get_amazon_data_from_api(self, asin: str) -> Dict[str, Any]:
        """
        Fetch Amazon product data from Rainforest API.
        
        Args:
            asin: Amazon product ASIN
            
        Returns:
            Dict containing product data
        """
        api_url = "https://api.rainforestapi.com/request"
        params = {
            "api_key": self.rainforest_api_key,
            "type": "product",
            "amazon_domain": "amazon.com",
            "asin": asin
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("product", {})
            else:
                logger.error(f"Rainforest API error: {response.status_code} - {response.text}")
                return None
    
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
    
    async def _get_product_data_with_browser(self, url: str) -> Dict[str, Any]:
        """
        Get product data using stealth browser techniques.
        Uses multiple layers of anti-detection measures.
        
        Args:
            url: Product URL
            
        Returns:
            Dict containing product data
        """
        # Determine if we should use mobile or desktop user agent
        use_mobile = random.random() < 0.3  # 30% chance of using mobile
        user_agent = random.choice(self.mobile_agents if use_mobile else self.desktop_agents)
        
        # Create unique browser profile for this session
        browser_data_dir = os.path.join(self.temp_dir, "user_data", f"session_{int(time.time())}")
        os.makedirs(browser_data_dir, exist_ok=True)
        
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                async with async_playwright() as p:
                    # Different browser types on different attempts
                    if current_retry == 0:
                        browser_type = p.chromium
                    elif current_retry == 1:
                        browser_type = p.firefox
                    else:
                        browser_type = p.webkit
                    
                    # Launch with extensive anti-fingerprinting
                    browser = await browser_type.launch(
                        headless=True,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-features=IsolateOrigins,site-per-process',
                            f'--user-agent={user_agent}',
                            '--disable-site-isolation-trials',
                            '--no-sandbox'
                        ]
                    )
                    
                    # Create context with realistic browser settings
                    viewport_width = 1920 if not use_mobile else 375
                    viewport_height = 1080 if not use_mobile else 812
                    
                    context = await browser.new_context(
                        user_agent=user_agent,
                        viewport={'width': viewport_width, 'height': viewport_height},
                        device_scale_factor=random.choice([1, 2]) if not use_mobile else 3,
                        locale=random.choice(['en-US', 'en-GB']),
                        timezone_id=random.choice(['America/New_York', 'America/Los_Angeles', 'Europe/London']),
                        geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                        permissions=['geolocation'],
                        is_mobile=use_mobile
                    )
                    
                    # Add stealth scripts
                    await context.add_init_script("""
                        // Make detection of automation more difficult
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                        
                        // Mask Chrome headless detection
                        if (window.chrome) {
                            window.chrome.runtime = {};
                        }
                        
                        // Make navigator properties undetectable
                        const originalQuery = window.navigator.permissions.query;
                        window.navigator.permissions.query = (parameters) => (
                            parameters.name === 'notifications' ?
                                Promise.resolve({ state: Notification.permission }) :
                                originalQuery(parameters)
                        );
                    """)
                    
                    # Create new page and navigate with full retry logic
                    page = await context.new_page()
                    
                    # Add request interception to modify headers
                    await page.route('**/*', lambda route: route.continue_(
                        headers={
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Cache-Control': 'max-age=0',
                            'Connection': 'keep-alive',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1',
                            'DNT': '1'
                        }
                    ))
                    
                    # Add realistic human behavior
                    await self._add_human_behavior(page)
                    
                    # Load the URL with proxy if needed
                    try:
                        logger.info(f"Loading page: {url}")
                        
                        # Random delay before navigation
                        await page.wait_for_timeout(random.randint(1000, 3000))
                        
                        # Navigate with timeout
                        response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                        
                        # Check response
                        if not response or response.status >= 400:
                            logger.warning(f"Got HTTP error: {response.status if response else 'No response'}")
                            current_retry += 1
                            continue
                        
                        # Check if page has anti-bot measures
                        if await self._is_blocked(page):
                            logger.warning(f"Detected anti-bot measures on attempt {current_retry + 1}")
                            current_retry += 1
                            continue
                            
                        # Add more human-like behavior
                        await self._simulate_human_behavior(page)
                        
                        # Extract product data
                        return await self._extract_product_data(page, url)
                        
                    except Exception as e:
                        logger.error(f"Error during page load: {str(e)}")
                        current_retry += 1
                        continue
                        
            except Exception as e:
                logger.error(f"Browser error on attempt {current_retry + 1}: {str(e)}")
                current_retry += 1
                
        # If all retries failed, return error
        return {
            "status": "error",
            "message": "Failed to access product data after multiple attempts",
            "url": url
        }
    
    async def _add_human_behavior(self, page: Page):
        """Add human-like behavior to the page."""
        # Set common cookies
        await page.evaluate("""() => {
            document.cookie = "session-id=" + Math.random().toString(36).substring(2, 15);
            document.cookie = "session-token=" + Math.random().toString(36).substring(2, 32);
        }""")
        
        # Impersonate common browser plugins
        await page.add_init_script("""
        if (!window.navigator.plugins) {
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        }
        if (!window.navigator.mimeTypes) {
            Object.defineProperty(navigator, 'mimeTypes', {
                get: () => [1, 2, 3, 4, 5],
            });
        }
        """)
        
        # Random mouse movements
        await page.mouse.move(
            random.randint(100, 500),
            random.randint(100, 500)
        )
        
    async def _is_blocked(self, page: Page) -> bool:
        """
        Check if the page has anti-bot measures or blocks.
        
        Args:
            page: Playwright page
            
        Returns:
            bool: True if blocked, False otherwise
        """
        page_content = await page.content()
        block_indicators = [
            "robot", "captcha", "automated access", "verify you're a human",
            "unusual traffic", "bot", "security challenge", "suspicious activity",
            "to continue to amazon", "sorry, we just need to make sure"
        ]
        
        page_title = await page.title()
        if any(indicator in page_title.lower() for indicator in ["robot", "captcha", "verify", "check"]):
            return True
            
        return any(indicator in page_content.lower() for indicator in block_indicators)
    
    async def _simulate_human_behavior(self, page: Page):
        """Simulate realistic human browsing behavior."""
        # Random initial wait
        await page.wait_for_timeout(random.randint(1000, 3000))
        
        # Random scroll behavior
        scroll_times = random.randint(2, 5)
        for i in range(scroll_times):
            await page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
            await page.wait_for_timeout(random.randint(500, 1500))
        
        # Move mouse to random positions
        for _ in range(random.randint(2, 4)):
            await page.mouse.move(
                random.randint(100, 800),
                random.randint(100, 600)
            )
            await page.wait_for_timeout(random.randint(300, 700))
        
        # Scroll back up partially
        if random.random() < 0.7:  # 70% chance
            await page.evaluate(f"window.scrollBy(0, {random.randint(-400, -100)})")
            await page.wait_for_timeout(random.randint(500, 1000))
    
    async def _extract_product_data(self, page: Page, url: str) -> Dict[str, Any]:
        """
        Extract product data from the page.
        Uses multiple selector strategies to maximize success.
        
        Args:
            page: Playwright page
            url: Original URL
            
        Returns:
            Dict containing product data
        """
        try:
            asin = self._extract_asin_from_url(url) or "unknown"
            
            # Try to extract price from structured data first (most reliable)
            price, price_text = await self._extract_price_from_structured_data(page)
            
            # Multi-strategy title extraction
            title = await self._extract_text_with_fallbacks(page, [
                "#productTitle", 
                ".product-title", 
                "h1", 
                '[data-component-type="s-product-title"]'
            ])
            
            # If price wasn't in structured data, try multiple visual selectors
            if price is None:
                # Multi-strategy price extraction - ensure we wait for prices to load
                try:
                    # Wait for price elements to be visible - try multiple common selectors
                    for price_selector in [
                        ".a-price", 
                        "#priceblock_ourprice", 
                        ".a-color-price",
                        '[data-a-color="price"]'
                    ]:
                        try:
                            # Wait with short timeouts to avoid long delays
                            await page.wait_for_selector(price_selector, timeout=3000, state="visible")
                            logger.info(f"Price element found with selector: {price_selector}")
                            break
                        except Exception:
                            continue
                except Exception:
                    logger.warning("Timed out waiting for price element")
                
                # Now try to extract the price with many selector strategies
                price_selectors = [
                    ".a-price .a-offscreen",  # Amazon primary price
                    "#priceblock_ourprice",  # Amazon old price element
                    "#priceblock_dealprice",  # Amazon deals
                    ".a-color-price",  # General Amazon price
                    ".a-price",  # Another Amazon price format
                    "#price_inside_buybox",  # Buybox price
                    "#corePrice_feature_div .a-offscreen",  # New Amazon price
                    "#corePriceDisplay_desktop_feature_div .a-offscreen",  # Another variation
                    '[data-a-color="price"] .a-offscreen',  # Generic Amazon price
                    ".a-price .a-price-whole",  # Just the whole price part (will need decimals separately)
                    "#price",  # Generic price id
                    ".price-large",  # Amazon warehouse deals
                    ".priceToPay .a-offscreen"  # Another Amazon price format
                ]
                
                # Try to find price with each selector
                price_text = await self._extract_text_with_fallbacks(page, price_selectors)
                
                # If still no price, try JavaScript evaluation to extract price directly from DOM
                if not price_text:
                    try:
                        price_text = await page.evaluate("""
                            () => {
                                // Try to find price in multiple ways
                                const priceElements = [
                                    ...document.querySelectorAll('.a-price .a-offscreen'),
                                    ...document.querySelectorAll('[data-a-color="price"]'),
                                    ...document.querySelectorAll('#priceblock_ourprice'),
                                    ...document.querySelectorAll('#priceblock_dealprice'),
                                    document.querySelector('#price'),
                                    document.querySelector('.offer-price'),
                                    document.querySelector('.priceToPay')
                                ].filter(el => el);
                                
                                for (const el of priceElements) {
                                    if (el.textContent && el.textContent.includes('$')) {
                                        return el.textContent.trim();
                                    }
                                }
                                
                                // Look for price in any element with $ sign
                                const allElements = document.querySelectorAll('*');
                                for (const el of allElements) {
                                    if (el.childNodes.length === 1 && 
                                        el.textContent && 
                                        el.textContent.includes('$') && 
                                        el.textContent.length < 15) {
                                        return el.textContent.trim();
                                    }
                                }
                                
                                return null;
                            }
                        """)
                    except Exception as e:
                        logger.error(f"Error using JavaScript to find price: {e}")
                
                # Clean and extract price if we found text
                if price_text:
                    # Clean price text - sometimes it contains extra characters
                    price_text = price_text.strip()
                    
                    # Remove non-numeric characters except decimal point
                    price_str = re.sub(r'[^\d.]', '', price_text)
                    try:
                        price = float(price_str)
                    except ValueError:
                        price = None
            
            # Multi-strategy rating extraction
            rating = await self._extract_text_with_fallbacks(page, [
                "#acrPopover", 
                ".a-icon-star", 
                ".reviewCountTextLinked", 
                '[data-hook="rating-out-of-text"]',
                '[data-hook="rating-snippet"]'
            ])
            
            # Multi-strategy features extraction  
            features = []
            feature_selectors = [
                "#feature-bullets .a-list-item",
                ".product-facts .a-list-item",
                ".bundle-components-list .a-list-item"
            ]
            
            for selector in feature_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    text = text.strip()
                    if text:
                        features.append(text)
                
                if features:
                    break
            
            # Multi-strategy availability extraction
            availability = await self._extract_text_with_fallbacks(page, [
                "#availability", 
                "#deliveryMessageMirId", 
                ".a-box-inner .a-color-success",
                '[data-feature-name="availability"]'
            ])
            
            # Image extraction
            image_url = await self._extract_attribute_with_fallbacks(page, [
                "#landingImage", 
                ".image-swatch .a-declarative",
                ".image-stretch",
                "img[data-old-hires]"
            ], "src")
            
            # Extract image URL from alternative attribute if needed
            if not image_url:
                image_url = await self._extract_attribute_with_fallbacks(page, [
                    "img[data-old-hires]"
                ], "data-old-hires")
            
            # Take a screenshot of the page for debugging
            logger.info(f"Extracted product data from {url}: {title[:30]}...")
            
            # Ensure we have at least placeholder price text if price is None
            if not price_text or price_text == "null":
                price_text = "Price not available"
            
            # Better price display if we have a number
            if price is not None:
                price_text = f"${price:.2f}"
            
            return {
                "status": "success",
                "source": "amazon",
                "url": url,
                "title": title or "Unknown Product",
                "price": price,
                "price_text": price_text,
                "rating": rating or "No ratings",
                "features": features[:5],
                "availability": availability or "Unknown",
                "image_url": image_url,
                "asin": asin
            }
            
        except Exception as e:
            logger.error(f"Error extracting product data: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to extract product data: {str(e)}",
                "url": url
            }
    
    async def _extract_text_with_fallbacks(self, page: Page, selectors: List[str]) -> Optional[str]:
        """
        Try to extract text using multiple selectors as fallbacks.
        
        Args:
            page: Playwright page
            selectors: List of CSS selectors to try
            
        Returns:
            Text content or None if not found
        """
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        return text.strip()
            except Exception:
                continue
        
        return None
    
    async def _extract_attribute_with_fallbacks(
        self, page: Page, selectors: List[str], attribute: str
    ) -> Optional[str]:
        """
        Try to extract an attribute using multiple selectors as fallbacks.
        
        Args:
            page: Playwright page
            selectors: List of CSS selectors to try
            attribute: Attribute name to extract
            
        Returns:
            Attribute value or None if not found
        """
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    value = await element.get_attribute(attribute)
                    if value:
                        return value
            except Exception:
                continue
        
        return None
    
    async def _extract_price_from_structured_data(self, page: Page) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract price from structured JSON-LD data on the page.
        This is often more reliable than scraping visible elements.
        
        Args:
            page: Playwright page
            
        Returns:
            Tuple of (price as float, price as string)
        """
        try:
            structured_data = await page.evaluate("""
                () => {
                    // Look for JSON-LD data
                    const jsonldElements = document.querySelectorAll('script[type="application/ld+json"]');
                    const jsonData = [];
                    
                    for (const element of jsonldElements) {
                        try {
                            const parsedData = JSON.parse(element.textContent);
                            jsonData.push(parsedData);
                        } catch (e) {
                            // Ignore parsing errors
                        }
                    }
                    
                    return jsonData;
                }
            """)
            
            # Extract price from structured data
            for data in structured_data:
                # Handle different schema formats
                if "@type" in data:
                    if data["@type"] == "Product":
                        # Standard product schema
                        if "offers" in data:
                            offers = data["offers"]
                            if isinstance(offers, dict):
                                if "price" in offers:
                                    price = offers["price"]
                                    try:
                                        return float(price), f"${float(price):.2f}"
                                    except ValueError:
                                        pass
                            elif isinstance(offers, list):
                                for offer in offers:
                                    if "price" in offer:
                                        price = offer["price"]
                                        try:
                                            return float(price), f"${float(price):.2f}"
                                        except ValueError:
                                            pass
            
            # Also check for inline variable declarations that might contain price
            price_variables = await page.evaluate("""
                () => {
                    // Look for common price variables in scripts
                    const scripts = document.querySelectorAll('script:not([src])');
                    let priceInfo = null;
                    
                    // Common price patterns in Amazon scripts
                    const patterns = [
                        /priceAmount['"]\s*:\s*([\d\.]+)/i,
                        /price['"]\s*:\s*([\d\.]+)/i,
                        /buyingPrice['"]\s*:\s*([\d\.]+)/i
                    ];
                    
                    for (const script of scripts) {
                        const content = script.textContent;
                        for (const pattern of patterns) {
                            const match = pattern.exec(content);
                            if (match && match[1]) {
                                try {
                                    const price = parseFloat(match[1]);
                                    if (!isNaN(price) && price > 0) {
                                        return price;
                                    }
                                } catch (e) {
                                    // Ignore parsing errors
                                }
                            }
                        }
                    }
                    
                    return null;
                }
            """)
            
            if price_variables:
                return float(price_variables), f"${float(price_variables):.2f}"
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            return None, None
    
    def cleanup(self):
        """Clean up temporary files and data."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")


class PriceScraper:
    def __init__(self):
        """Initialize the price scraper."""
        # Initialize user agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ]
        
        self.headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "DNT": "1",
            "Pragma": "no-cache"
        }
        self.timeout = 20.0
        
        # Initialize proxy settings
        self.proxy_username = os.getenv("PROXY_USERNAME")
        self.proxy_password = os.getenv("PROXY_PASSWORD")
        self.proxy_host = os.getenv("PROXY_HOST")
        self.proxy_port = os.getenv("PROXY_PORT")
        
        # Initialize stealth scraper
        self.stealth_scraper = StealthScraper()
        
        # Save cookies between sessions
        self.cookies_dir = os.path.join(tempfile.gettempdir(), "ecommerce_cookies")
        os.makedirs(self.cookies_dir, exist_ok=True)
        
        if not all([self.proxy_username, self.proxy_password, self.proxy_host, self.proxy_port]):
            logger.warning("Proxy credentials not fully configured. Some features may be limited.")

    async def _get_proxy_url(self) -> str:
        """Get the proxy URL with authentication."""
        if all([self.proxy_username, self.proxy_password, self.proxy_host, self.proxy_port]):
            return f"http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}"
        return None

    async def get_product_details(self, url: str) -> Dict[str, Any]:
        """
        Fetch product details from the given URL using the most reliable method.
        This updated version uses API-first approach with browser fallback.
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        try:
            if "amazon.com" in domain:
                # Use the new stealth strategy
                return await self.stealth_scraper.get_amazon_product_data(url)
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

<<<<<<< Updated upstream
    async def _is_captcha_page(self, page) -> bool:
        """Check if the current page is a CAPTCHA/verification page."""
        try:
            # Check for common CAPTCHA indicators
            captcha_indicators = [
                "Enter the characters you see below",
                "Sorry, we just need to make sure you're not a robot",
                "Type the characters you see in this image",
                "To discuss automated access to Amazon data please contact"
            ]
            
            page_content = await page.content()
            return any(indicator in page_content for indicator in captcha_indicators)
        except Exception as e:
            logger.error(f"Error checking for CAPTCHA: {str(e)}")
            return False

    async def _get_browser_fingerprint(self) -> Dict[str, Any]:
        """Generate a realistic browser fingerprint."""
        return {
            "navigator": {
                "userAgent": self.headers["User-Agent"],
                "language": "en-US",
                "languages": ["en-US", "en"],
                "platform": "Win32",
                "hardwareConcurrency": 8,
                "deviceMemory": 8,
                "maxTouchPoints": 0,
                "vendor": "Google Inc.",
                "plugins": [
                    {"name": "Chrome PDF Plugin", "filename": "internal-pdf-viewer"},
                    {"name": "Chrome PDF Viewer", "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
                    {"name": "Native Client", "filename": "internal-nacl-plugin"}
                ],
                "mimeTypes": [
                    {"type": "application/pdf", "suffixes": "pdf"},
                    {"type": "application/x-google-chrome-pdf", "suffixes": "pdf"}
                ]
            },
            "screen": {
                "width": 1920,
                "height": 1080,
                "colorDepth": 24,
                "pixelDepth": 24,
                "availWidth": 1920,
                "availHeight": 1040
            },
            "mediaDevices": {
                "audioInputs": 1,
                "audioOutputs": 1,
                "videoInputs": 1
            },
            "webGL": {
                "vendor": "Google Inc. (NVIDIA)",
                "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)"
            }
        }
    async def scrape_walmart(self, url: str) -> Dict[str, Any]:
        """Scrape product details from Walmart robustly."""
        max_retries = 3
        retry = 0

        while retry < max_retries:
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(url, timeout=60000)

                    # Check for CAPTCHA
                    page_text = await page.content()
                    if any(phrase in page_text for phrase in ["Verify your identity", "robot check", "captcha"]):
                        logger.warning(f"Walmart CAPTCHA detected on try {retry+1}")
                        retry += 1
                        await browser.close()
                        continue

                    title = await self.safe_text(page, 'h1.prod-ProductTitle') or await self.safe_text(page, 'h1[itemprop="name"]')
                    price_major = await page.get_attribute('span.price-characteristic', 'content')
                    price_minor = await page.get_attribute('span.price-mantissa', 'content')

                    if price_major:
                        price_text = f"{price_major}.{price_minor or '00'}"
                        price = float(price_text)
                    else:
                        price = None

                    await browser.close()

                    return {
                        "status": "success",
                        "source": "walmart",
                        "url": url,
                        "title": title or "Unknown Product",
                        "price_text": f"${price:.2f}" if price else "Price not found",
                        "price": price,
                    }

            except Exception as e:
                logger.error(f"Walmart scraping error: {e}")
                retry += 1
                continue

        # Fallback if browser scraping fails
        logger.warning("Walmart browser scraping failed. Falling back to HTTPX + BeautifulSoup...")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                soup = BeautifulSoup(response.text, 'html.parser')

                title_elem = soup.find('h1', {'class': 'prod-ProductTitle'})
                price_elem = soup.find('span', {'class': 'price-characteristic'})

                title = title_elem.text.strip() if title_elem else "Unknown Product"
                price_text = price_elem['content'] if price_elem and 'content' in price_elem.attrs else None
                price = float(price_text) if price_text else None

                return {
                    "status": "partial",
                    "source": "walmart",
                    "url": url,
                    "title": title,
                    "price_text": f"${price:.2f}" if price else "Price not found",
                    "price": price,
                }
        except Exception as e:
            logger.error(f"Walmart fallback scraping failed: {e}")
            return {
                "status": "error",
                "source": "walmart",
                "url": url,
                "message": f"Failed to scrape Walmart product after retries and fallback: {e}"
            }


    async def scrape_bestbuy(self, url: str) -> Dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)

            title = await self.safe_text(page, '.sku-title h1')
            price = await self.safe_text(page, '.priceView-hero-price span[aria-hidden="true"]')

            await browser.close()

            return {
                "status": "success",
                "source": "bestbuy",
                "url": url,
                "title": title or "Unknown Product",
                "price_text": price or "Price not found",
                "price": self._extract_price(price),
            }
    async def safe_text(self, page, selector: str) -> Optional[str]:
        try:
            elem = await page.query_selector(selector)
            if elem:
                text = await elem.text_content()
                return text.strip()
        except Exception:
            pass
        return None

    async def scrape_amazon(self, url: str) -> Dict[str, Any]:
        """Scrape product details from Amazon using Playwright."""
        max_retries = 3
        current_retry = 0
=======
    async def scrape_walmart(self, url: str) -> Dict[str, Any]:
        """
        Scrape product details from Walmart using Playwright browser automation.
        This approach is more effective against anti-scraping measures.
        """
        logger.info(f"Scraping Walmart product: {url}")
        return await self._scrape_walmart_with_browser(url)
    
    async def _scrape_walmart_with_browser(self, url: str) -> Dict[str, Any]:
        """
        Use browser automation to scrape Walmart product data.
        More reliable than HTTP requests for modern e-commerce sites.
        """
        user_agent = random.choice(self.user_agents)
>>>>>>> Stashed changes
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US'
                )
                
                # Add stealth scripts to avoid detection
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    if (window.chrome) { window.chrome.runtime = {}; }
                    
                    // Add common browser plugins
                    if (!window.navigator.plugins) {
                        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    }
                    if (!window.navigator.languages) {
                        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                    }
                """)
                
                page = await context.new_page()
                
                try:
                    # Add cookies to help avoid detection
                    await page.context.add_cookies([
                        {
                            "name": "session-id",
                            "value": f"{random.randint(100000000, 999999999)}",
                            "domain": ".walmart.com",
                            "path": "/"
                        },
                        {
                            "name": "session-token",
                            "value": f"{random.randint(10000000, 99999999)}-{random.randint(1000000, 9999999)}",
                            "domain": ".walmart.com",
                            "path": "/"
                        }
                    ])
                    
                    # Set up network request interception to monitor API requests and extract price data
                    prices_from_xhr = []
                    
                    async def handle_response(response):
                        if "walmart.com/api" in response.url:
                            try:
                                if response.status == 200:
                                    resp_text = await response.text()
                                    if "price" in resp_text.lower() and ('"price":' in resp_text or '"currentPrice":' in resp_text):
                                        prices_from_xhr.append(resp_text)
                                        logger.info(f"Found potential price data in API response: {response.url}")
                            except Exception as e:
                                logger.warning(f"Error processing API response: {str(e)}")
                    
                    # Monitor network responses
                    page.on("response", handle_response)
                    
                    logger.info(f"Navigating to Walmart URL: {url}")
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    
                    # Wait for a core element to indicate the page has loaded
                    try:
                        await page.wait_for_selector('h1', timeout=5000)
                    except Exception:
                        logger.warning("Could not find h1 on Walmart page, continuing anyway")
                    
                    # Wait for a bit longer to capture API responses
                    await page.wait_for_timeout(5000)
                    
                    # Scroll down to trigger any lazy-loaded content
                    await page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
                    await page.wait_for_timeout(random.randint(500, 1500))
                    
                    # Scroll further
                    await page.evaluate(f"window.scrollBy(0, {random.randint(700, 1000)})")
                    await page.wait_for_timeout(random.randint(500, 1500))
                    
                    # Check if we hit a captcha or security page
                    page_url = page.url
                    if "blocked" in page_url or "captcha" in page_url:
                        logger.warning(f"Detected Walmart anti-bot page: {page_url}")
                        return {
                            "status": "error",
                            "source": "walmart",
                            "message": "Encountered anti-bot protection",
                            "url": url
                        }
                    
                    # Try to extract from window.__PRELOADED_STATE__
                    preloaded_state = await page.evaluate("""
                        () => {
                            if (window.__PRELOADED_STATE__) {
                                return JSON.stringify(window.__PRELOADED_STATE__);
                            }
                            return null;
                        }
                    """)
                    
                    if preloaded_state:
                        prices_from_xhr.append(preloaded_state)
                    
                    # Try to wait for Walmart price elements
                    try:
                        await page.wait_for_selector('[data-testid="price-wrap"],[data-automation="price-wrap"]', timeout=2000)
                    except Exception:
                        logger.info("Could not find price-wrap element")
                    
                    # Extract product information using JavaScript for most reliability
                    product_data = await page.evaluate("""
                        () => {
                            const data = {};
                            
                            // Extract title - try multiple possible selectors
                            const titleSelectors = [
                                'h1[itemprop="name"]',
                                '.prod-ProductTitle',
                                'h1.f3',
                                'h1',
                                '[data-testid="product-title"]'
                            ];
                            
                            for (const selector of titleSelectors) {
                                const elem = document.querySelector(selector);
                                if (elem) {
                                    data.title = elem.textContent.trim();
                                    break;
                                }
                            }
                            
                            // PRICE EXTRACTION - AGGRESSIVE APPROACH
                            
                            // 1. Try direct Walmart price selectors
                            const priceSelectors = [
                                '[data-automation="product-price"]',
                                '[data-testid="price-wrap"]',
                                '.price-characteristic',
                                '[itemprop="price"]',
                                '.f1 .b8',
                                '.prod-PriceSection .price-characteristic'
                            ];
                            
                            for (const selector of priceSelectors) {
                                const elem = document.querySelector(selector);
                                if (elem) {
                                    const text = elem.textContent.trim();
                                    if (text && (text.includes('$') || /^\d+\.\d{2}$/.test(text))) {
                                        data.price_text = text.includes('$') ? text : '$' + text;
                                        console.log("Found price with selector: " + selector + " = " + data.price_text);
                                        break;
                                    }
                                }
                            }
                            
                            // 2. Look for prices in structured data
                            if (!data.price_text) {
                                const jsonLdElements = document.querySelectorAll('script[type="application/ld+json"]');
                                for (const element of jsonLdElements) {
                                    try {
                                        const json = JSON.parse(element.textContent);
                                        let price = null;
                                        
                                        if (json.offers && json.offers.price) {
                                            price = json.offers.price;
                                        } else if (json.price) {
                                            price = json.price;
                                        }
                                        
                                        if (price) {
                                            data.price_text = '$' + price;
                                            console.log("Found price in JSON-LD: " + data.price_text);
                                            break;
                                        }
                                    } catch (e) {
                                        // Ignore parsing errors
                                    }
                                }
                            }
                            
                            // 3. Try global variables
                            if (!data.price_text && window.__PRELOADED_STATE__) {
                                try {
                                    const productData = window.__PRELOADED_STATE__.product;
                                    if (productData && productData.products && productData.products[0]) {
                                        const priceInfo = productData.products[0].priceInfo;
                                        if (priceInfo && priceInfo.currentPrice) {
                                            data.price_text = '$' + priceInfo.currentPrice.price;
                                            console.log("Found price in __PRELOADED_STATE__: " + data.price_text);
                                        }
                                    }
                                } catch (e) {
                                    console.log("Error extracting from __PRELOADED_STATE__: " + e);
                                }
                            }
                            
                            // 4. Scan for any element with price-like text
                            if (!data.price_text) {
                                const allElements = document.querySelectorAll('*');
                                const priceRegex = /\$\s*(\d+(\.\d{1,2})?)/;
                                
                                for (const el of allElements) {
                                    if (el.children.length === 0) {  // Only check leaf nodes
                                        const text = el.textContent.trim();
                                        if (text && text.length < 15) {  // Short text to avoid paragraphs
                                            const match = text.match(priceRegex);
                                            if (match) {
                                                data.price_text = text;
                                                console.log("Found price text in element: " + data.price_text);
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // 5. Extract from any element with price in attribute
                            if (!data.price_text) {
                                const priceElements = document.querySelectorAll('[class*="price"],[id*="price"],[data-*="price"]');
                                for (const el of priceElements) {
                                    const text = el.textContent.trim();
                                    if (text && text.includes('$') && /\$\s*\d+(\.\d{1,2})?/.test(text) && text.length < 15) {
                                        data.price_text = text;
                                        console.log("Found price in element with price in attribute: " + data.price_text);
                                        break;
                                    }
                                }
                            }
                            
                            // Extract other data
                            const ratingSelectors = [
                                '.stars-container',
                                '[itemprop="ratingValue"]'
                            ];
                            
                            for (const selector of ratingSelectors) {
                                const elem = document.querySelector(selector);
                                if (elem) {
                                    data.rating = elem.textContent.trim();
                                    break;
                                }
                            }
                            
                            // Extract availability
                            const availabilitySelectors = [
                                '.fulfillment-add-to-cart-button',
                                '[data-track="add-to-cart"]',
                                '[data-button-state="ADD_TO_CART"]',
                                '.add-to-cart-button'
                            ];
                            
                            for (const selector of availabilitySelectors) {
                                const elem = document.querySelector(selector);
                                if (elem && !elem.disabled) {
                                    data.availability = "In Stock";
                                    break;
                                }
                            }
                            
                            if (!data.availability) {
                                data.availability = "Out of Stock";
                            }
                            
                            // Extract image
                            const imageSelectors = [
                                '.primary-image',
                                '[data-track="product-image"]',
                                '.product-image'
                            ];
                            
                            for (const selector of imageSelectors) {
                                const elem = document.querySelector(selector);
                                if (elem && elem.src) {
                                    data.image_url = elem.src;
                                    break;
                                }
                            }
                            
                            // If still no image, try to find any product image
                            if (!data.image_url) {
                                const images = document.querySelectorAll('img');
                                for (const img of images) {
                                    if (img.src && img.alt && data.title && img.alt.includes(data.title.substring(0, 10))) {
                                        data.image_url = img.src;
                                        break;
                                    }
                                }
                            }
                            
                            // Extract features
                            const featureElems = document.querySelectorAll('.product-description-content li');
                            data.features = [];
                            for (let i = 0; i < Math.min(featureElems.length, 5); i++) {
                                data.features.push(featureElems[i].textContent.trim());
                            }
                            
                            return data;
                        }
                    """)
                    
                    # Process XHR captured data to extract price
                    price = None
                    price_text = product_data.get('price_text')
                    
                    if not price_text and prices_from_xhr:
                        for xhr_data in prices_from_xhr:
                            try:
                                # Try to parse JSON data
                                if '"currentPrice":' in xhr_data or '"price":' in xhr_data:
                                    # Simple regex pattern to extract price
                                    price_pattern = re.compile(r'"(?:currentPrice|price)"\s*:\s*(\d+\.?\d*)')
                                    match = price_pattern.search(xhr_data)
                                    if match:
                                        price_value = match.group(1)
                                        price = float(price_value)
                                        price_text = f"${price:.2f}"
                                        logger.info(f"Extracted price from XHR data: {price_text}")
                                        break
                            except Exception as e:
                                logger.warning(f"Error parsing XHR data for price: {str(e)}")
                    
                    # Clean price and convert to float
                    if price_text and not price:
                        price = self._extract_price(price_text)
                    
                    # Take a screenshot for debugging
                    filename = f"debug_walmart_{int(time.time())}.png"
                    await page.screenshot(path=filename)
                    logger.info(f"Saved screenshot to {filename}")
                    
                    return {
                        "status": "success",
                        "source": "walmart",
                        "url": url,
                        "title": product_data.get('title', 'Unknown Product'),
                        "price": price,
                        "price_text": price_text if price_text else "Price not available",
                        "rating": product_data.get('rating', 'No ratings'),
                        "features": product_data.get('features', []),
                        "availability": product_data.get('availability', 'Unknown'),
                        "image_url": product_data.get('image_url')
                    }
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Error in Walmart browser scraper: {str(e)}")
            return {
                "status": "error",
                "source": "walmart",
                "message": f"Failed to scrape Walmart product: {str(e)}",
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
        current_rating = self._extract_rating_value(product_details.get("rating", "0"))
        
        # Mock data for demonstration
        alternatives = []
        search_title = title.replace(" ", "+")
        
        mock_stores = {
            "amazon": f"https://www.amazon.com/s?k={search_title}",
            "walmart": f"https://www.walmart.com/search/?query={search_title}",
            "bestbuy": f"https://www.bestbuy.com/site/searchpage.jsp?st={search_title}"
        }

        # Simple logic: Check other stores with slightly varied mock prices and ratings
        for store, search_url in mock_stores.items():
            if store != source and len(alternatives) < max_results:
                # Create a slightly different mock price
                price_multiplier = 1.0
                if store == "walmart":
                    price_multiplier = 0.95 + random.uniform(-0.03, 0.03) # Usually a bit cheaper
                elif store == "bestbuy":
                     price_multiplier = 1.05 + random.uniform(-0.03, 0.03) # Usually a bit more expensive
                else: # amazon
                    price_multiplier = 1.0 + random.uniform(-0.03, 0.03) # Comparable
                
                alt_price = None
                if current_price:
                     alt_price = round(current_price * price_multiplier, 2)
                
                # Generate mock ratings - slightly varied from original
                alt_rating_value = min(5.0, max(1.0, current_rating + random.uniform(-0.5, 0.5)))
                alt_rating = f"{alt_rating_value:.1f} out of 5 stars"
                
                # Generate mock availability status
                availability_options = ["In Stock", "Few Left", "In Stock", "In Stock", "Ships in 2 days"]
                alt_availability = random.choice(availability_options)
                
                # Generate mock review count
                review_count = random.randint(10, 500)
                
                # Calculate a holistic deal score (0-100)
                # This considers both price and non-price factors
                price_score = 0
                if current_price and alt_price:
                    # Lower price is better (0-50 points)
                    price_diff_pct = ((current_price - alt_price) / current_price) * 100
                    price_score = min(50, max(0, 25 + price_diff_pct))
                
                # Rating score (0-30 points)
                # Higher rating is better
                rating_score = (alt_rating_value / 5.0) * 30
                
                # Reviews volume score (0-10 points)
                # More reviews means more confidence in the rating
                review_volume_score = min(10, (review_count / 100) * 10)
                
                # Availability score (0-10 points)
                availability_score = 10 if alt_availability == "In Stock" else 5
                
                # Calculate total holistic score
                holistic_score = price_score + rating_score + review_volume_score + availability_score
                
                # Determine if it's a better deal overall
                is_better_deal = holistic_score > 50  # Threshold for being a "better deal"
                
                # Generate reason text based on multiple factors
                price_reason = ""
                if current_price and alt_price:
                    if alt_price < current_price:
                        diff_pct = abs(round(((alt_price - current_price) / current_price) * 100))
                        price_reason = f"{diff_pct}% cheaper than {source.capitalize()}"
                    elif alt_price > current_price:
                        diff_pct = abs(round(((alt_price - current_price) / current_price) * 100))
                        price_reason = f"{diff_pct}% more expensive than {source.capitalize()}"
                    else:
                        price_reason = f"Same price as {source.capitalize()}"
                
                # Create combined reason text
                reasons = []
                if price_reason:
                    reasons.append(price_reason)
                if alt_rating_value > current_rating + 0.3:
                    reasons.append(f"Higher customer rating ({alt_rating_value:.1f} vs {current_rating:.1f})")
                if review_count > 100:
                    reasons.append(f"Has {review_count} customer reviews")
                if alt_availability == "In Stock":
                    reasons.append("In stock and ready to ship")
                
                # Join all reasons
                reason = " | ".join(reasons)

                alternatives.append({
                    "source": store,
                    "title": title, # Assume same title for mock
                    "price": alt_price,
                    "url": search_url,
                    "is_better_deal": is_better_deal,
                    "reason": reason,
                    "rating": alt_rating,
                    "review_count": review_count,
                    "availability": alt_availability,
                    "holistic_score": round(holistic_score, 1)
                })
        
        return alternatives

    def _extract_rating_value(self, rating_text: str) -> float:
        """Extract numeric rating value from rating text."""
        try:
            # Try to extract a number from text like "4.5 out of 5 stars"
            match = re.search(r'(\d+(\.\d+)?)', rating_text)
            if match:
                return float(match.group(1))
            return 0.0
        except (ValueError, TypeError, AttributeError):
            return 0.0

    async def analyze_deal(self, product_details: Dict[str, Any], alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze if the product is a good deal based on a holistic approach that considers
        price, ratings, reviews, and availability.
        """
        if product_details.get("status") == "partial":
            return {
                "is_good_deal": None,
                "confidence": "low",
                "reasons": [
                    "Limited information available due to access restrictions",
                    "Unable to perform full comparison",
                    "Consider checking the product page directly for current information"
                ]
            }
            
        if product_details.get("status") != "success" or product_details.get("price") is None:
            return {
                "is_good_deal": False,
                "confidence": "low",
                "reasons": ["Unable to determine product information accurately"]
            }
        
        # Check if there are better alternatives based on holistic score
        better_alternatives = [alt for alt in alternatives if alt.get("is_better_deal", False)]
        
        # Calculate the product's own holistic score
        current_price = product_details.get("price", 0)
        current_rating = self._extract_rating_value(product_details.get("rating", "0"))
        
        # Mock review count for current product
        current_review_count = random.randint(10, 500)
        
        # Mock availability for current product
        availability_options = ["In Stock", "Few Left", "In Stock", "In Stock", "Ships in 2 days"]
        current_availability = product_details.get("availability", random.choice(availability_options))
        
        # Base score is 50 since we're comparing against itself
        price_score = 25  # Neutral price score
        
        # Rating score (0-30 points)
        rating_score = (current_rating / 5.0) * 30
        
        # Reviews volume score (0-10 points)
        review_volume_score = min(10, (current_review_count / 100) * 10)
        
        # Availability score (0-10 points)
        availability_score = 10 if "in stock" in current_availability.lower() else 5
        
        # Calculate total holistic score for current product
        current_holistic_score = price_score + rating_score + review_volume_score + availability_score
        
        # Add holistic score to the product details for reference
        product_details["holistic_score"] = round(current_holistic_score, 1)
        product_details["review_count"] = current_review_count
        
        # Sort alternatives by holistic score to find the best overall option
        if alternatives:
            alternatives.sort(key=lambda x: x.get('holistic_score', 0), reverse=True)
        
        # Determine if it's a good deal based on holistic comparison
        is_good_deal = True
        if better_alternatives:
            best_alt = alternatives[0]  # Already sorted by holistic score
            is_good_deal = current_holistic_score >= best_alt.get("holistic_score", 0)
        
        # Determine confidence level
        confidence = "high" if len(alternatives) >= 2 else "medium" if len(alternatives) == 1 else "low"
        
        # Generate reasons
        reasons = []
        
        # Add current product analysis
        product_name = product_details.get("source", "").capitalize()
        reasons.append(f"Analysis of {product_name} listing:")
        if current_rating > 0:
            reasons.append(f"- Rating: {current_rating:.1f}/5 stars from approximately {current_review_count} reviews")
        if current_availability:
            reasons.append(f"- Availability: {current_availability}")
        
        # Compare with alternatives
        if better_alternatives:
            reasons.append(f"\nFound {len(better_alternatives)} potentially better options across platforms:")
            # Show top 2 alternatives
            for alt in better_alternatives[:2]:
                alt_source = alt.get('source', 'Alternative').capitalize()
                alt_price = alt.get('price')
                alt_rating = alt.get('rating', 'No rating')
                alt_review_count = alt.get('review_count', 0)
                alt_availability = alt.get('availability', 'Unknown')
                
                reasons.append(f"\n- {alt_source} alternative:")
                reasons.append(f"  • Price: ${alt_price:.2f}")
                if "rating" in alt_rating.lower():
                    reasons.append(f"  • {alt_rating} ({alt_review_count} reviews)")
                else:
                    reasons.append(f"  • Rating: {alt_rating} ({alt_review_count} reviews)")
                reasons.append(f"  • Availability: {alt_availability}")
                reasons.append(f"  • Key advantages: {alt.get('reason', 'Alternative option')}")
        else:
            if alternatives:
                reasons.append("\nNo better alternatives found across the compared retailers.")
            else:
                reasons.append("\nNo alternatives found for comparison.")

        # Add advice based on holistic analysis
        if is_good_deal:
            if alternatives:
                reasons.append("\nOverall Assessment: This appears to be the best value when considering price, ratings, and availability.")
            else:
                reasons.append("\nOverall Assessment: This seems reasonable, but we couldn't find alternatives for a thorough comparison.")
        else:
            reasons.append("\nOverall Assessment: Consider the alternatives above which may offer better overall value.")

        # Add a note about the comparison context
        reasons.append("\nNote: This comparison considers price, customer ratings, review volume, and availability status.")

        return {
            "is_good_deal": is_good_deal,
            "confidence": confidence,
            "price": product_details.get("price"),
            "holistic_score": round(current_holistic_score, 1),
            "reasons": reasons
        }
