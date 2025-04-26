from playwright.sync_api import sync_playwright

def fetch_amazon_details(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)

        title = page.locator("#productTitle").nth(0).text_content()
        price = page.locator(".a-offscreen").first.text_content()
        rating = page.locator(".a-icon-star").first.text_content()
        review_count = page.locator("#acrCustomerReviewText").nth(0).text_content()

        browser.close()

        return {
            "title": title.strip() if title else None,
            "price": price.strip() if price else None,
            "rating": rating.strip() if rating else None,
            "review_count": review_count.strip() if review_count else None
        }
