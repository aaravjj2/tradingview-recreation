import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.cboe.com/us/options/market_statistics/historical_data/")
        await page.wait_for_load_state("networkidle")
        
        # Scroll to bottom to trigger lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        
        await page.screenshot(path="analysis/page_screenshot.png", full_page=True)
        print("Screenshot saved.")
        
        # Also print all visible text to a file
        text = await page.inner_text("body")
        with open("analysis/page_text.txt", "w") as f:
            f.write(text)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
