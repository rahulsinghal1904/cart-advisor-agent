#!/usr/bin/env python3
"""
Standalone test script for the price extraction functionality.
This script attempts to extract product prices from e-commerce URLs.
"""

import asyncio
import logging
import os
import sys
import json
import re
import random
import tempfile
from dotenv import load_dotenv
from urllib.parse import urlparse
from playwright.async_api import async_playwright, Page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("price_test")

class PriceExtractor:
    """Simplified extractor for testing price extraction only."""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="price_test_")
        self.desktop_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15"
        ]
    
    async def extract_price(self, url: str) -> dict:
        """Extract price from a product URL."""
        user_agent = random.choice(self.desktop_agents)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            # Add stealth script
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            
            try:
                print(f"Loading page: {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                print("Page loaded successfully")
                
                # Try to extract price from structured data first
                print("Extracting price from structured data...")
                price, price_text = await self._extract_price_from_structured_data(page)
                
                # If that fails, try visual elements
                if price is None:
                    print("No price in structured data, trying visual elements...")
                    price_text = await self._extract_price_from_visual_elements(page)
                    if price_text:
                        # Clean and extract price
                        price_str = re.sub(r'[^\d.]', '', price_text)
                        try:
                            price = float(price_str)
                        except ValueError:
                            price = None
                
                # If we got price as a number, format the text nicely
                if price is not None and (not price_text or price_text == "null"):
                    price_text = f"${price:.2f}"
                elif not price_text:
                    price_text = "Price not available"
                
                # Also extract title for verification
                title = await self._extract_title(page)
                
                return {
                    "success": price is not None,
                    "price": price,
                    "price_text": price_text,
                    "title": title,
                    "url": url
                }
                
            except Exception as e:
                print(f"Error during extraction: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "url": url
                }
            finally:
                await browser.close()
    
    async def _extract_title(self, page: Page) -> str:
        """Extract product title."""
        try:
            for selector in ["#productTitle", "h1", ".product-title"]:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        return text.strip()
        except:
            pass
            
        return "Unknown Product"
    
    async def _extract_price_from_structured_data(self, page: Page):
        """Extract price from structured data."""
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
                    // Look for common price patterns in scripts
                    const scripts = document.querySelectorAll('script:not([src])');
                    
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
            print(f"Error extracting structured data: {str(e)}")
            return None, None
    
    async def _extract_price_from_visual_elements(self, page: Page):
        """Extract price from visual elements on the page."""
        # First make sure prices have loaded
        try:
            for price_selector in [".a-price", "#priceblock_ourprice", ".a-color-price"]:
                try:
                    await page.wait_for_selector(price_selector, timeout=3000, state="visible")
                    break
                except:
                    continue
        except:
            pass
        
        # Now try various selectors
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
            "#price",  # Generic price id
            ".price-large",  # Amazon warehouse deals
            ".priceToPay .a-offscreen"  # Another Amazon price format
        ]
        
        # Try each selector
        for selector in price_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and '$' in text:
                        return text.strip()
            except:
                continue
        
        # If all selectors fail, try JavaScript approach
        try:
            price_text = await page.evaluate("""
                () => {
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
            return price_text
        except:
            pass
            
        return None


async def test_price_extraction():
    """Test price extraction on various e-commerce URLs."""
    extractor = PriceExtractor()
    
    test_urls = [
        "https://www.amazon.com/dp/B07ZPKN6YR",  # AirPods Pro
        "https://www.amazon.com/dp/B09JQL3MXB",  # PlayStation 5
        "https://www.amazon.com/dp/B088T7NWWR"   # Popular kitchen product
    ]
    
    total = len(test_urls)
    success = 0
    
    print("\n" + "="*60)
    print(" PRICE EXTRACTION TEST ")
    print("="*60)
    
    # Test each URL
    for i, url in enumerate(test_urls, 1):
        print(f"\n[{i}/{total}] Testing: {url}")
        result = await extractor.extract_price(url)
        
        if result["success"]:
            success += 1
            print(f"✓ SUCCESS: {result['title'][:50]}...")
            print(f"✓ PRICE: {result['price_text']} ({result['price']})")
        else:
            print(f"✗ FAILED: {result.get('error', 'Unknown error')}")
    
    # Print summary
    print("\n" + "="*60)
    print(f"RESULTS: {success}/{total} successful price extractions ({success/total*100:.1f}%)")
    print("="*60)
    
    return success > 0


if __name__ == "__main__":
    load_dotenv()
    print("\nTesting price extraction functionality...")
    result = asyncio.run(test_price_extraction())
    
    if result:
        print("\n✅ Price extraction is working!")
        sys.exit(0)
    else:
        print("\n❌ Price extraction failed on all test URLs.")
        sys.exit(1) 