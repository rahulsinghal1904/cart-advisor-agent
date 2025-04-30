import asyncio
import logging
from playwright.async_api import async_playwright
import random
import re
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def scrape_walmart(url: str):
    """Simple Walmart scraper using Playwright."""
    logger.info(f"Scraping Walmart URL: {url}")
    
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ]
    
    user_agent = random.choice(user_agents)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1920, 'height': 1080}
            )
            
            # Add stealth script
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            
            page = await context.new_page()
            
            # Navigate to the URL
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Take a screenshot
            screenshot_path = f"walmart_test_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
            
            # Check for anti-bot page
            current_url = page.url
            if "blocked" in current_url or "captcha" in current_url:
                logger.warning(f"Detected anti-bot page: {current_url}")
                return {
                    "status": "error",
                    "message": "Anti-bot protection detected"
                }
            
            # Extract basic product information
            title = await page.evaluate("""
                () => {
                    const titleElem = document.querySelector('h1');
                    return titleElem ? titleElem.textContent.trim() : 'Title not found';
                }
            """)
            
            price_text = await page.evaluate("""
                () => {
                    // Try common price selectors
                    const selectors = [
                        '[data-automation="product-price"]',
                        '[data-testid="price-wrap"]',
                        '.price-characteristic'
                    ];
                    
                    for (const selector of selectors) {
                        const elem = document.querySelector(selector);
                        if (elem) {
                            return elem.textContent.trim();
                        }
                    }
                    
                    return 'Price not found';
                }
            """)
            
            return {
                "status": "success",
                "url": url,
                "title": title,
                "price_text": price_text,
                "screenshot": screenshot_path
            }
            
        finally:
            await browser.close()

async def scrape_bestbuy(url: str):
    """Simple Best Buy scraper using Playwright."""
    logger.info(f"Scraping Best Buy URL: {url}")
    
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ]
    
    user_agent = random.choice(user_agents)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1920, 'height': 1080}
            )
            
            # Add stealth script
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            
            page = await context.new_page()
            
            # Navigate to the URL
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Take a screenshot
            screenshot_path = f"bestbuy_test_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
            
            # Check for anti-bot page
            current_url = page.url
            if "captcha" in current_url or "blocked" in current_url:
                logger.warning(f"Detected anti-bot page: {current_url}")
                return {
                    "status": "error",
                    "message": "Anti-bot protection detected"
                }
            
            # Extract basic product information
            title = await page.evaluate("""
                () => {
                    const titleElem = document.querySelector('.sku-title h1') || document.querySelector('h1');
                    return titleElem ? titleElem.textContent.trim() : 'Title not found';
                }
            """)
            
            price_text = await page.evaluate("""
                () => {
                    // Try common price selectors
                    const selectors = [
                        '[data-testid="customer-price"]',
                        '.priceView-customer-price span',
                        '.priceView-price span'
                    ];
                    
                    for (const selector of selectors) {
                        const elems = document.querySelectorAll(selector);
                        for (const elem of elems) {
                            const text = elem.textContent.trim();
                            if (text && text.includes('$')) {
                                return text;
                            }
                        }
                    }
                    
                    return 'Price not found';
                }
            """)
            
            return {
                "status": "success",
                "url": url,
                "title": title,
                "price_text": price_text,
                "screenshot": screenshot_path
            }
            
        finally:
            await browser.close()

async def main():
    """Test both scrapers."""
    print("Testing Simple Walmart and Best Buy Scrapers")
    print("-" * 50)
    
    # Test URLs
    walmart_url = "https://www.walmart.com/ip/Apple-AirPods-with-Charging-Case-2nd-Generation/604342441"
    bestbuy_url = "https://www.bestbuy.com/site/apple-airpods-with-charging-case-2nd-generation-white/6084400.p"
    
    # Test Walmart
    print(f"\nTesting Walmart scraper with URL: {walmart_url}")
    try:
        walmart_result = await scrape_walmart(walmart_url)
        print(f"Status: {walmart_result.get('status', 'unknown')}")
        print(f"Title: {walmart_result.get('title', 'Not found')}")
        print(f"Price: {walmart_result.get('price_text', 'Not found')}")
        print(f"Screenshot: {walmart_result.get('screenshot', 'No screenshot')}")
    except Exception as e:
        print(f"Error scraping Walmart: {str(e)}")
    
    # Test Best Buy
    print(f"\nTesting Best Buy scraper with URL: {bestbuy_url}")
    try:
        bestbuy_result = await scrape_bestbuy(bestbuy_url)
        print(f"Status: {bestbuy_result.get('status', 'unknown')}")
        print(f"Title: {bestbuy_result.get('title', 'Not found')}")
        print(f"Price: {bestbuy_result.get('price_text', 'Not found')}")
        print(f"Screenshot: {bestbuy_result.get('screenshot', 'No screenshot')}")
    except Exception as e:
        print(f"Error scraping Best Buy: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 