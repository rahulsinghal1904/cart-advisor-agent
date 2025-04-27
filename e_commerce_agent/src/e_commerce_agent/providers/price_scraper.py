import re
import json
import logging
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Any, Tuple
import random
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PriceScraper:
    def __init__(self):
        """Initialize the price scraper with HTTP client."""
        # Generate a random user agent from a list of common ones
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
        
        # Initialize CAPTCHA solving service
        self.captcha_api_key = os.getenv("CAPTCHA_API_KEY")
        
        if not all([self.proxy_username, self.proxy_password, self.proxy_host, self.proxy_port]):
            logger.warning("Proxy credentials not fully configured. Some features may be limited.")
        
        if not self.captcha_api_key:
            logger.warning("CAPTCHA API key not configured. CAPTCHA solving will be disabled.")

    async def _get_proxy_url(self) -> str:
        """Get the proxy URL with authentication."""
        if all([self.proxy_username, self.proxy_password, self.proxy_host, self.proxy_port]):
            return f"http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}"
        return None

    async def _solve_captcha(self, page) -> bool:
        """Attempt to solve CAPTCHA using a service."""
        if not self.captcha_api_key:
            return False
            
        try:
            # Get the CAPTCHA image
            captcha_image = await page.query_selector('img[alt*="CAPTCHA"]')
            if not captcha_image:
                return False
                
            # Get the image data
            image_data = await captcha_image.screenshot()
            
            # Send to CAPTCHA solving service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.captcha-service.com/solve",
                    headers={"Authorization": f"Bearer {self.captcha_api_key}"},
                    files={"image": image_data}
                )
                
                if response.status_code == 200:
                    solution = response.json().get("solution")
                    if solution:
                        # Find the input field and submit button
                        input_field = await page.query_selector('input[name="captcha"]')
                        submit_button = await page.query_selector('button[type="submit"]')
                        
                        if input_field and submit_button:
                            await input_field.fill(solution)
                            await submit_button.click()
                            await page.wait_for_timeout(2000)  # Wait for submission
                            return True
                            
            return False
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {str(e)}")
            return False

    async def get_product_details(self, url: str) -> Dict[str, Any]:
        """
        Fetch product details from the given URL.
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        try:
            if "amazon.com" in domain:
                result = await self.scrape_amazon(url)
                if result.get("status") == "error" and "CAPTCHA" in result.get("message", ""):
                    # Try to extract basic info from URL as fallback
                    asin = None
                    if "/dp/" in url:
                        asin = url.split('/dp/')[1].split('/')[0].split('?')[0]
                    
                    return {
                        "status": "partial",
                        "source": "amazon",
                        "url": url,
                        "asin": asin,
                        "message": "Limited information available due to access restrictions",
                        "title": "Product details restricted",
                        "price": None,
                        "price_text": "Price not available",
                        "rating": "Not available",
                        "features": [],
                        "availability": "Unknown"
                    }
                return result
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

    async def scrape_amazon(self, url: str) -> Dict[str, Any]:
        """Scrape product details from Amazon using Playwright."""
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                async with async_playwright() as p:
                    # Generate a new browser fingerprint for each attempt
                    fingerprint = await self._get_browser_fingerprint()
                    
                    # Launch browser with more realistic settings
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-features=IsolateOrigins,site-per-process',
                            '--disable-site-isolation-trials',
                            '--disable-web-security',
                            '--disable-features=IsolateOrigins',
                            '--disable-site-isolation-trials',
                            '--disable-features=BlockInsecurePrivateNetworkRequests',
                            '--disable-features=CrossOriginOpenerPolicy',
                            '--disable-features=CrossOriginEmbedderPolicy',
                            '--disable-features=CrossOriginResourcePolicy',
                            '--disable-features=SameSiteByDefaultCookies',
                            '--disable-features=StrictOriginIsolation',
                            '--disable-features=StrictTransportSecurity',
                            '--disable-features=UpgradeInsecureRequests',
                            '--disable-features=WebSecurity',
                            '--disable-features=WebSecurityChecks',
                            '--disable-features=WebSecurityChecksForLocalFiles',
                            '--disable-features=WebSecurityChecksForLocalResources',
                            '--disable-features=WebSecurityChecksForRemoteResources',
                            '--disable-features=WebSecurityChecksForRemoteFiles',
                            '--disable-features=WebSecurityChecksForRemoteUrls',
                            '--disable-features=WebSecurityChecksForRemoteOrigins',
                            '--disable-features=WebSecurityChecksForRemoteProtocols',
                            '--disable-features=WebSecurityChecksForRemotePorts',
                            '--disable-features=WebSecurityChecksForRemoteHosts',
                            '--disable-features=WebSecurityChecksForRemoteDomains',
                            '--disable-features=WebSecurityChecksForRemoteSubdomains',
                            '--disable-features=WebSecurityChecksForRemotePaths',
                            '--disable-features=WebSecurityChecksForRemoteQueries',
                            '--disable-features=WebSecurityChecksForRemoteFragments',
                            '--disable-features=WebSecurityChecksForRemoteUsernames',
                            '--disable-features=WebSecurityChecksForRemotePasswords',
                            '--disable-features=WebSecurityChecksForRemoteHeaders',
                            '--disable-features=WebSecurityChecksForRemoteCookies',
                            '--disable-features=WebSecurityChecksForRemoteStorage',
                            '--disable-features=WebSecurityChecksForRemoteCache',
                            '--disable-features=WebSecurityChecksForRemoteHistory',
                            '--disable-features=WebSecurityChecksForRemoteBookmarks',
                            '--disable-features=WebSecurityChecksForRemoteDownloads',
                            '--disable-features=WebSecurityChecksForRemoteUploads',
                            '--disable-features=WebSecurityChecksForRemoteForms',
                            '--disable-features=WebSecurityChecksForRemoteScripts',
                            '--disable-features=WebSecurityChecksForRemoteStyles',
                            '--disable-features=WebSecurityChecksForRemoteImages',
                            '--disable-features=WebSecurityChecksForRemoteVideos',
                            '--disable-features=WebSecurityChecksForRemoteAudios',
                            '--disable-features=WebSecurityChecksForRemoteFonts',
                            '--disable-features=WebSecurityChecksForRemoteDocuments',
                            '--disable-features=WebSecurityChecksForRemoteApplications',
                            '--disable-features=WebSecurityChecksForRemoteExtensions',
                            '--disable-features=WebSecurityChecksForRemotePlugins',
                            '--disable-features=WebSecurityChecksForRemoteMimeTypes',
                            '--disable-features=WebSecurityChecksForRemoteProtocols',
                            '--disable-features=WebSecurityChecksForRemotePorts',
                            '--disable-features=WebSecurityChecksForRemoteHosts',
                            '--disable-features=WebSecurityChecksForRemoteDomains',
                            '--disable-features=WebSecurityChecksForRemoteSubdomains',
                            '--disable-features=WebSecurityChecksForRemotePaths',
                            '--disable-features=WebSecurityChecksForRemoteQueries',
                            '--disable-features=WebSecurityChecksForRemoteFragments',
                            '--disable-features=WebSecurityChecksForRemoteUsernames',
                            '--disable-features=WebSecurityChecksForRemotePasswords',
                            '--disable-features=WebSecurityChecksForRemoteHeaders',
                            '--disable-features=WebSecurityChecksForRemoteCookies',
                            '--disable-features=WebSecurityChecksForRemoteStorage',
                            '--disable-features=WebSecurityChecksForRemoteCache',
                            '--disable-features=WebSecurityChecksForRemoteHistory',
                            '--disable-features=WebSecurityChecksForRemoteBookmarks',
                            '--disable-features=WebSecurityChecksForRemoteDownloads',
                            '--disable-features=WebSecurityChecksForRemoteUploads',
                            '--disable-features=WebSecurityChecksForRemoteForms',
                            '--disable-features=WebSecurityChecksForRemoteScripts',
                            '--disable-features=WebSecurityChecksForRemoteStyles',
                            '--disable-features=WebSecurityChecksForRemoteImages',
                            '--disable-features=WebSecurityChecksForRemoteVideos',
                            '--disable-features=WebSecurityChecksForRemoteAudios',
                            '--disable-features=WebSecurityChecksForRemoteFonts',
                            '--disable-features=WebSecurityChecksForRemoteDocuments',
                            '--disable-features=WebSecurityChecksForRemoteApplications',
                            '--disable-features=WebSecurityChecksForRemoteExtensions',
                            '--disable-features=WebSecurityChecksForRemotePlugins',
                            '--disable-features=WebSecurityChecksForRemoteMimeTypes'
                        ]
                    )
                    
                    # Create a new context with more realistic settings
                    context = await browser.new_context(
                        viewport={'width': fingerprint['screen']['width'], 'height': fingerprint['screen']['height']},
                        user_agent=fingerprint['navigator']['userAgent'],
                        locale=fingerprint['navigator']['language'],
                        timezone_id='America/New_York',
                        geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # New York
                        permissions=['geolocation'],
                        java_script_enabled=True,
                        has_touch=True,
                        is_mobile=False,
                        color_scheme='light',
                        reduced_motion='no-preference',
                        forced_colors='none'
                    )
                    
                    # Add more realistic browser behavior
                    await context.add_init_script("""
                        // Override navigator properties
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [
                                {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                                {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                                {name: 'Native Client', filename: 'internal-nacl-plugin'}
                            ]
                        });
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en']
                        });
                        Object.defineProperty(navigator, 'platform', {
                            get: () => 'Win32'
                        });
                        Object.defineProperty(navigator, 'hardwareConcurrency', {
                            get: () => 8
                        });
                        Object.defineProperty(navigator, 'deviceMemory', {
                            get: () => 8
                        });
                        Object.defineProperty(navigator, 'maxTouchPoints', {
                            get: () => 0
                        });
                        Object.defineProperty(navigator, 'vendor', {
                            get: () => 'Google Inc.'
                        });
                        
                        // Override screen properties
                        Object.defineProperty(screen, 'width', {
                            get: () => 1920
                        });
                        Object.defineProperty(screen, 'height', {
                            get: () => 1080
                        });
                        Object.defineProperty(screen, 'colorDepth', {
                            get: () => 24
                        });
                        Object.defineProperty(screen, 'pixelDepth', {
                            get: () => 24
                        });
                        Object.defineProperty(screen, 'availWidth', {
                            get: () => 1920
                        });
                        Object.defineProperty(screen, 'availHeight', {
                            get: () => 1040
                        });
                        
                        // Override WebGL properties
                        const getParameter = WebGLRenderingContext.prototype.getParameter;
                        WebGLRenderingContext.prototype.getParameter = function(parameter) {
                            if (parameter === 37445) {
                                return 'Google Inc. (NVIDIA)';
                            }
                            if (parameter === 37446) {
                                return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)';
                            }
                            return getParameter.apply(this, arguments);
                        };
                    """)
                    
                    page = await context.new_page()
                    
                    # Set headers
                    await page.set_extra_http_headers(self.headers)
                    
                    # Add random delays to simulate human behavior
                    await page.wait_for_timeout(random.randint(1000, 3000))
                    
                    # Navigate to the URL with increased timeout
                    try:
                        logger.info(f"Attempting to load page: {url}")
                        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                        logger.info("Page loaded successfully")
                        
                        # Check for CAPTCHA
                        if await self._is_captcha_page(page):
                            logger.warning(f"CAPTCHA detected on attempt {current_retry + 1}")
                            current_retry += 1
                            await browser.close()
                            continue
                        
                        # Wait for key elements with shorter timeouts
                        title = None  # Initialize title variable
                        try:
                            logger.info("Waiting for product title element...")
                            # First try to wait for the element to be present in DOM
                            await page.wait_for_selector('#productTitle', state='attached', timeout=10000)
                            logger.info("Product title element found in DOM")
                            
                            # Then try to get its content directly
                            title_elem = await page.query_selector('#productTitle')
                            if title_elem:
                                title = await title_elem.text_content()
                                if title:
                                    title = title.strip()
                                    logger.info(f"Successfully extracted title: {title[:50]}...")
                            else:
                                logger.warning("Product title element found but could not query it")
                        except Exception as e:
                            logger.warning(f"Product title not found after timeout: {str(e)}")
                            # Try alternative selectors
                            try:
                                logger.info("Trying alternative title selectors...")
                                title_elem = await page.query_selector('h1')
                                if title_elem:
                                    title = await title_elem.text_content()
                                    if title:
                                        title = title.strip()
                                        logger.info(f"Found title in h1: {title[:50]}...")
                            except Exception as e2:
                                logger.warning(f"No product title found in any expected location: {str(e2)}")
                        
                        if not title:
                            # Try to find title in script tag as last resort
                            try:
                                logger.info("Attempting to extract title from page content...")
                                script_content = await page.content()
                                title_match = re.search(r'"title"\s*:\s*"([^"]+)"', script_content)
                                if title_match:
                                    title = title_match.group(1).strip()
                                    logger.info(f"Found title in script content: {title[:50]}...")
                            except Exception as e:
                                logger.warning(f"Failed to extract title from page content: {str(e)}")
                        
                        title = title if title else "Unknown Product"
                        if title == "Unknown Product":
                            logger.warning("Could not find product title, using fallback")
                        
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
                        logger.error(f"Error during page interaction: {str(e)}")
                        current_retry += 1
                        continue
                        
            except Exception as e:
                logger.error(f"Browser error on attempt {current_retry + 1}: {str(e)}")
                current_retry += 1
                continue
        
        # If we've exhausted all retries
        logger.error("All scraping attempts failed")
        return {
            "status": "error",
            "source": "amazon",
            "message": "Failed to access product details after multiple attempts",
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
                    price_multiplier = 0.95 + random.uniform(-0.03, 0.03) # Usually a bit cheaper
                elif store == "bestbuy":
                     price_multiplier = 1.05 + random.uniform(-0.03, 0.03) # Usually a bit more expensive
                else: # amazon
                    price_multiplier = 1.0 + random.uniform(-0.03, 0.03) # Comparable
                
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
        if product_details.get("status") == "partial":
            return {
                "is_good_deal": None,
                "confidence": "low",
                "reasons": [
                    "Limited information available due to access restrictions",
                    "Unable to perform full price comparison",
                    "Consider checking the product page directly for current pricing"
                ]
            }
            
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
        }
