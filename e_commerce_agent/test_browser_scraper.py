import asyncio
import logging
import random
import re
import json
import time
from urllib.parse import urlparse
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def scrape_with_advanced_browser(url: str):
    """Use Playwright with advanced stealth techniques to scrape a product page."""
    
    # Get the domain to determine which site we're scraping
    domain = urlparse(url).netloc.lower()
    site_type = None
    
    if "walmart.com" in domain:
        site_type = "walmart"
    elif "bestbuy.com" in domain:
        site_type = "bestbuy"
    else:
        logger.error(f"Unsupported site: {domain}")
        return {"status": "error", "message": f"Unsupported site: {domain}"}
    
    logger.info(f"Scraping {site_type.capitalize()} URL: {url}")
    
    # List of realistic user agents
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.65"
    ]
    
    # Use a random user agent
    user_agent = random.choice(user_agents)
    
    async with async_playwright() as p:
        # Launch a persistent context to maintain cookies between sessions
        # Using a persistent context can help avoid detection
        browser_data_dir = f"./browser_data_{site_type}"
        
        # Browser options
        browser_type = p.chromium
        browser_options = {
            "headless": False,  # Set to True when not debugging
            "slow_mo": 50,  # Slows down Playwright operations to avoid detection
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                f"--user-agent={user_agent}",
                "--disable-site-isolation-trials",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized"
            ]
        }
        
        browser = await browser_type.launch(**browser_options)
        
        try:
            # Create a new context with specific device parameters
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
                locale='en-US',
                timezone_id='America/New_York',
                geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                permissions=['geolocation'],
                is_mobile=False,
                has_touch=False,
                user_agent=user_agent
            )
            
            # Add extensive stealth scripts to simulate a real user
            await context.add_init_script('''
                // Mask WebDriver property
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => false
                });
                
                // Mask automation-related properties
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                  parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );
                
                // Add plugins
                if (navigator.plugins.length === 0) {
                  Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5].map(() => {
                      return {
                        length: 1,
                        item: () => ({ type: 'application/x-google-chrome-pdf' }),
                        namedItem: () => ({ type: 'application/pdf' }),
                        description: 'Portable Document Format',
                        filename: 'internal-pdf-viewer',
                        name: 'Chrome PDF Plugin'
                      };
                    })
                  });
                }
                
                // Add languages
                if (navigator.languages.length === 0) {
                  Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                  });
                }
                
                // Canvas fingerprint
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                  if (type === 'image/png' && this.width === 200 && this.height === 30) {
                    // This is likely a fingerprint test
                    return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAABuCAYAAABiSarYAAAgAElEQVR4XuzVMQ0AMAgEsGFSy+h/pQYYdLlSwBs5TgAgIUSkFBHpPYm1zjoTkV4FKQCAhABQWlVRVaMiUgIA';
                  }
                  return originalToDataURL.apply(this, arguments);
                };
                
                // WebGL fingerprint
                const getParameterProxyHandler = {
                  apply: function(target, thisArg, args) {
                    const param = args[0];
                    if (param === 37445) {
                      return 'Intel Inc.';
                    } else if (param === 37446) {
                      return 'Intel Iris OpenGL Engine';
                    }
                    return Reflect.apply(target, thisArg, args);
                  }
                };
                
                // Apply the proxy to WebGL's getParameter function if it exists
                if (window.WebGLRenderingContext) {
                  const getParameter = WebGLRenderingContext.prototype.getParameter;
                  WebGLRenderingContext.prototype.getParameter = new Proxy(getParameter, getParameterProxyHandler);
                }
            ''')
            
            # Create a new page
            page = await context.new_page()
            
            # Set extra HTTP headers to appear more like a real user
            await page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'DNT': '1',
                'Upgrade-Insecure-Requests': '1',
                'Referer': 'https://www.google.com/'
            })
            
            # Add cookies - these can sometimes help avoid bot detection
            if site_type == "walmart":
                await context.add_cookies([
                    {
                        "name": "next-day",
                        "value": "0",
                        "domain": ".walmart.com",
                        "path": "/"
                    },
                    {
                        "name": "location-data",
                        "value": '{"postalCode":"10001","stateOrProvinceCode":"NY","city":"NEW YORK","storeId":2130,"isZipLocated":true}',
                        "domain": ".walmart.com",
                        "path": "/"
                    },
                    {
                        "name": "auth",
                        "value": """MTAyOTYyMDE4WbuSt3o%2BiZqX5h0zsBkRJSbXyEJcAKSoBYHAm56xZE1a8jN8g5vc%2FgNPeKu5fNRQNrHR%2FSYxJLhQDy1jkJ0mWlwl3coCKvlOt7eOicOFKn9UMzJ7aPpgMmfwvbT7kOtTVGLB3wjKwQRxf%2BlO3CBcSBTjO3ZiZ90QG5MN%2FZoVx4fZbTl6rFjfE27YxjHYaZErUDu1cxhFnBESdMhKyGw%2FMB32vUXw%2BfYHR4H2lv1wlQdFR7LrJ3bWj5g70R3UMBOCFCkUKAGp3IjTmvHGfzKnmbsdPAVi6V3sRjjO7s2hGXyKFqWfmSDh9Qf%2Bw5d9JHUCUHKPMNnmcWxc2TL2KxS3i21JDCgR4i7dFhxztgbVTGj3MsGnrHg%3D""",
                        "domain": ".walmart.com",
                        "path": "/"
                    }
                ])
            elif site_type == "bestbuy":
                await context.add_cookies([
                    {
                        "name": "locStoreId",
                        "value": "1402",
                        "domain": ".bestbuy.com",
                        "path": "/"
                    },
                    {
                        "name": "physical_location_storage",
                        "value": "granted",
                        "domain": ".bestbuy.com",
                        "path": "/"
                    },
                    {
                        "name": "vt",
                        "value": "e9cef410-8b42-11ee-887b-dd6d6d6b51a2",
                        "domain": ".bestbuy.com",
                        "path": "/"
                    }
                ])
            
            # Monitor network requests to capture API responses with price data
            price_data_from_network = []
            
            async def handle_response(response):
                # Only process responses that might contain product data
                url = response.url
                if (
                    (site_type == "walmart" and "walmart.com/api" in url) or
                    (site_type == "bestbuy" and ("api.bestbuy.com" in url or "apollographql" in url))
                ):
                    try:
                        if response.status == 200:
                            content_type = response.headers.get("content-type", "")
                            if "json" in content_type or "javascript" in content_type:
                                resp_text = await response.text()
                                if "price" in resp_text.lower():
                                    logger.info(f"Found potential price data in API response: {url}")
                                    price_data_from_network.append(resp_text)
                    except Exception as e:
                        logger.warning(f"Error processing API response: {str(e)}")
            
            # Set up response handler
            page.on("response", handle_response)
            
            # Navigate to the URL with more realistic timing
            logger.info(f"Navigating to URL: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for page to load a bit
            await page.wait_for_timeout(2000)
            
            # Perform some human-like interactions
            # Move mouse randomly
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await page.wait_for_timeout(random.randint(300, 700))
            
            # Scroll down to trigger lazy loading
            for i in range(3):
                await page.evaluate(f"window.scrollBy(0, {random.randint(300, 600)})")
                await page.wait_for_timeout(random.randint(500, 1000))
            
            # Check if we've been redirected to a bot detection page
            current_url = page.url
            if (
                (site_type == "walmart" and ("blocked" in current_url or "captcha" in current_url)) or
                (site_type == "bestbuy" and ("captcha" in current_url or "access-denied" in current_url))
            ):
                logger.error(f"Redirected to anti-bot page: {current_url}")
                # Take a screenshot for debugging
                await page.screenshot(path=f"{site_type}_blocked_{int(time.time())}.png")
                return {"status": "error", "message": f"Anti-bot protection detected: {current_url}"}
            
            # Wait for specific elements based on the site
            selectors_to_wait_for = []
            
            if site_type == "walmart":
                selectors_to_wait_for = [
                    'h1[itemprop="name"]',
                    'h1',
                    '[data-testid="price-wrap"]',
                    '[data-automation="product-price"]'
                ]
            elif site_type == "bestbuy":
                selectors_to_wait_for = [
                    '.sku-title h1',
                    'h1',
                    '[data-testid="customer-price"]',
                    '.priceView-customer-price'
                ]
            
            # Wait for at least one of the selectors to be available
            for selector in selectors_to_wait_for:
                try:
                    await page.wait_for_selector(selector, timeout=2000)
                    logger.info(f"Found selector: {selector}")
                    break
                except Exception:
                    continue
            
            # Take a screenshot for debugging
            screenshot_path = f"{site_type}_product_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
            
            # Extract product data using appropriate selectors for each site
            if site_type == "walmart":
                product_data = await extract_walmart_data(page, price_data_from_network)
            else:  # Best Buy
                product_data = await extract_bestbuy_data(page, price_data_from_network)
            
            # Save the extracted data
            result_file = f"{site_type}_data_{int(time.time())}.json"
            with open(result_file, "w") as f:
                json.dump(product_data, f, indent=2)
            logger.info(f"Saved data to {result_file}")
            
            return product_data
            
        finally:
            await browser.close()

async def extract_walmart_data(page, price_data_from_network):
    """Extract product data from Walmart page."""
    # First attempt to extract data using JavaScript
    product_data = await page.evaluate("""
        () => {
            // Helper function to extract text from a selector safely
            const extractText = (selector) => {
                const elem = document.querySelector(selector);
                return elem ? elem.textContent.trim() : null;
            };
            
            // Helper function to extract attribute from a selector safely
            const extractAttr = (selector, attr) => {
                const elem = document.querySelector(selector);
                return elem ? elem.getAttribute(attr) : null;
            };
            
            const data = {
                title: null,
                price: null,
                price_text: null,
                currency: "USD",
                rating: null,
                availability: null,
                image_url: null,
                features: []
            };
            
            // Extract title - try multiple possible selectors
            const titleSelectors = [
                'h1[itemprop="name"]',
                '.prod-ProductTitle',
                'h1.f3',
                'h1'
            ];
            
            for (const selector of titleSelectors) {
                data.title = extractText(selector);
                if (data.title) break;
            }
            
            // Extract price - try multiple possible selectors
            const priceSelectors = [
                '[data-automation="product-price"]',
                '[data-testid="price-wrap"]',
                '.price-characteristic',
                '[itemprop="price"]',
                '.f1 .b8'
            ];
            
            let priceElem = null;
            for (const selector of priceSelectors) {
                priceElem = document.querySelector(selector);
                if (priceElem) {
                    data.price_text = priceElem.textContent.trim();
                    break;
                }
            }
            
            // Try to extract from structured data
            if (!data.price_text) {
                const jsonLdElements = document.querySelectorAll('script[type="application/ld+json"]');
                for (const element of jsonLdElements) {
                    try {
                        const json = JSON.parse(element.textContent);
                        if (json.offers && json.offers.price) {
                            data.price_text = `$${json.offers.price}`;
                            break;
                        }
                    } catch (e) {
                        // Ignore parsing errors
                    }
                }
            }
            
            // Try to extract from global state
            if (!data.price_text && window.__PRELOADED_STATE__) {
                try {
                    const state = window.__PRELOADED_STATE__;
                    if (state.product && state.product.products && state.product.products.length > 0) {
                        const product = state.product.products[0];
                        if (product.priceInfo && product.priceInfo.currentPrice) {
                            data.price_text = `$${product.priceInfo.currentPrice.price}`;
                        }
                    }
                } catch (e) {
                    console.error("Error extracting from global state:", e);
                }
            }
            
            // Extract rating
            const ratingSelectors = [
                '.stars-container',
                '[itemprop="ratingValue"]'
            ];
            
            for (const selector of ratingSelectors) {
                data.rating = extractText(selector);
                if (data.rating) break;
            }
            
            // Extract availability
            const availabilitySelectors = [
                '[data-automation="fulfillment-shipping-text"]',
                '.fulfillment-shipping-text'
            ];
            
            for (const selector of availabilitySelectors) {
                data.availability = extractText(selector);
                if (data.availability) break;
            }
            
            // Extract image URL
            const imageSelectors = [
                'img.prod-hero-image',
                '[data-automation="image-main"]'
            ];
            
            for (const selector of imageSelectors) {
                data.image_url = extractAttr(selector, 'src');
                if (data.image_url) break;
            }
            
            // If we couldn't find image with specific selectors, try to find any large product image
            if (!data.image_url) {
                const images = document.querySelectorAll('img');
                for (const img of images) {
                    const src = img.getAttribute('src');
                    if (src && (src.includes('large') || src.includes('hero'))) {
                        data.image_url = src;
                        break;
                    }
                }
            }
            
            // Extract features
            const featureElems = document.querySelectorAll('.product-description-content li');
            for (let i = 0; i < Math.min(featureElems.length, 5); i++) {
                data.features.push(featureElems[i].textContent.trim());
            }
            
            return data;
        }
    """)
    
    # Process network data for price information
    if not product_data.get('price_text') and price_data_from_network:
        for data in price_data_from_network:
            try:
                # Try to extract price from API response
                price_pattern = re.compile(r'"(?:currentPrice|price)"\s*:\s*(\d+\.?\d*)')
                match = price_pattern.search(data)
                if match:
                    price_value = match.group(1)
                    product_data['price'] = float(price_value)
                    product_data['price_text'] = f"${price_value}"
                    logger.info(f"Extracted price from network data: {product_data['price_text']}")
                    break
            except Exception as e:
                logger.warning(f"Error extracting price from network data: {str(e)}")
    
    # Convert price to a number if it's not already
    if product_data.get('price_text') and not product_data.get('price'):
        try:
            price_text = product_data['price_text']
            price_match = re.search(r'(\d+\.\d+|\d+)', price_text)
            if price_match:
                product_data['price'] = float(price_match.group(1))
        except Exception as e:
            logger.warning(f"Error converting price text to number: {str(e)}")
    
    # Add metadata
    product_data['url'] = page.url
    product_data['source'] = 'walmart'
    product_data['status'] = 'success' if product_data.get('title') else 'error'
    
    return product_data

async def extract_bestbuy_data(page, price_data_from_network):
    """Extract product data from Best Buy page."""
    # First attempt to extract data using JavaScript
    product_data = await page.evaluate("""
        () => {
            // Helper function to extract text from a selector safely
            const extractText = (selector) => {
                const elem = document.querySelector(selector);
                return elem ? elem.textContent.trim() : null;
            };
            
            // Helper function to extract attribute from a selector safely
            const extractAttr = (selector, attr) => {
                const elem = document.querySelector(selector);
                return elem ? elem.getAttribute(attr) : null;
            };
            
            const data = {
                title: null,
                price: null,
                price_text: null,
                currency: "USD",
                rating: null,
                availability: null,
                image_url: null,
                features: []
            };
            
            // Extract title
            const titleSelectors = [
                '.sku-title h1',
                '[data-track="product-title"]',
                'h1'
            ];
            
            for (const selector of titleSelectors) {
                data.title = extractText(selector);
                if (data.title) break;
            }
            
            // Extract price
            const priceSelectors = [
                '[data-testid="customer-price"]',
                '.priceView-customer-price span',
                '.priceView-hero-price span',
                '[data-track="product-price"]',
                '.priceView-price span'
            ];
            
            for (const selector of priceSelectors) {
                const elems = document.querySelectorAll(selector);
                for (const elem of elems) {
                    const text = elem.textContent.trim();
                    if (text && text.includes('$')) {
                        data.price_text = text;
                        break;
                    }
                }
                if (data.price_text) break;
            }
            
            // Try to extract from structured data
            if (!data.price_text) {
                const jsonLdElements = document.querySelectorAll('script[type="application/ld+json"]');
                for (const element of jsonLdElements) {
                    try {
                        const json = JSON.parse(element.textContent);
                        if (json.offers && json.offers.price) {
                            data.price_text = `$${json.offers.price}`;
                            break;
                        }
                    } catch (e) {
                        // Ignore parsing errors
                    }
                }
            }
            
            // Try to get price from Apollo state
            if (!data.price_text && window.__APOLLO_STATE__) {
                try {
                    const state = window.__APOLLO_STATE__;
                    const stateStr = JSON.stringify(state);
                    const priceMatch = stateStr.match(/"(?:currentPrice|price)"\\?:\\?\\?"?\$?(\d+(?:\.\d+)?)"?/);
                    if (priceMatch && priceMatch[1]) {
                        data.price_text = `$${priceMatch[1]}`;
                    }
                } catch (e) {
                    console.error("Error extracting from Apollo state:", e);
                }
            }
            
            // Extract rating
            const ratingSelectors = [
                '.customer-rating-average',
                '[itemprop="ratingValue"]'
            ];
            
            for (const selector of ratingSelectors) {
                data.rating = extractText(selector);
                if (data.rating) break;
            }
            
            // Extract availability
            const availabilitySelectors = [
                '.fulfillment-add-to-cart-button',
                '[data-track="add-to-cart"]'
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
            
            // Extract image URL
            const imageSelectors = [
                '.primary-image',
                '[data-track="product-image"]'
            ];
            
            for (const selector of imageSelectors) {
                data.image_url = extractAttr(selector, 'src');
                if (data.image_url) break;
            }
            
            // Extract features
            const featureElems = document.querySelectorAll('.feature-list .feature-bullets') || 
                                document.querySelectorAll('.feature-list li');
            for (let i = 0; i < Math.min(featureElems.length, 5); i++) {
                data.features.push(featureElems[i].textContent.trim());
            }
            
            return data;
        }
    """)
    
    # Process network data for price information
    if not product_data.get('price_text') and price_data_from_network:
        for data in price_data_from_network:
            try:
                # Try to extract price from API response
                price_pattern = re.compile(r'"(?:currentPrice|price)"\s*:\s*(\d+\.?\d*)')
                match = price_pattern.search(data)
                if match:
                    price_value = match.group(1)
                    product_data['price'] = float(price_value)
                    product_data['price_text'] = f"${price_value}"
                    logger.info(f"Extracted price from network data: {product_data['price_text']}")
                    break
            except Exception as e:
                logger.warning(f"Error extracting price from network data: {str(e)}")
    
    # Convert price to a number if it's not already
    if product_data.get('price_text') and not product_data.get('price'):
        try:
            price_text = product_data['price_text']
            price_match = re.search(r'(\d+\.\d+|\d+)', price_text)
            if price_match:
                product_data['price'] = float(price_match.group(1))
        except Exception as e:
            logger.warning(f"Error converting price text to number: {str(e)}")
    
    # Add metadata
    product_data['url'] = page.url
    product_data['source'] = 'bestbuy'
    product_data['status'] = 'success' if product_data.get('title') else 'error'
    
    return product_data

async def main():
    """Main function to run tests."""
    print("Advanced Browser Scraping Test")
    print("-" * 50)
    
    test_urls = [
        # Best Buy URLs
        "https://www.bestbuy.com/site/apple-airpods-with-charging-case-2nd-generation-white/6084400.p?skuId=6084400",
        "https://www.bestbuy.com/site/sony-playstation-5-console/6523167.p?skuId=6523167",
        
        # Walmart URLs
        "https://www.walmart.com/ip/PlayStation-5-Digital-Edition-Console/493824815",
        "https://www.walmart.com/ip/Apple-AirPods-with-Charging-Case-2nd-Generation/604342441"
    ]
    
    # Start with Best Buy since it's less likely to block
    best_buy_urls = [url for url in test_urls if "bestbuy.com" in url]
    walmart_urls = [url for url in test_urls if "walmart.com" in url]
    
    # Test Best Buy first
    for url in best_buy_urls:
        print(f"\nTesting URL: {url}")
        result = await scrape_with_advanced_browser(url)
        print(f"Status: {result.get('status', 'unknown')}")
        if result.get('status') == 'success':
            print(f"Title: {result.get('title', 'Not found')}")
            print(f"Price: {result.get('price_text', 'Not found')}")
            print(f"Rating: {result.get('rating', 'Not found')}")
            if result.get('features'):
                print("Features:")
                for feature in result.get('features', [])[:2]:
                    print(f"  - {feature[:50]}...")
    
    # Test Walmart with a delay to avoid detection
    await asyncio.sleep(2)
    for url in walmart_urls:
        print(f"\nTesting URL: {url}")
        result = await scrape_with_advanced_browser(url)
        print(f"Status: {result.get('status', 'unknown')}")
        if result.get('status') == 'success':
            print(f"Title: {result.get('title', 'Not found')}")
            print(f"Price: {result.get('price_text', 'Not found')}")
            print(f"Rating: {result.get('rating', 'Not found')}")
            if result.get('features'):
                print("Features:")
                for feature in result.get('features', [])[:2]:
                    print(f"  - {feature[:50]}...")

if __name__ == "__main__":
    asyncio.run(main()) 