import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.cboe.com/us/options/market_statistics/historical_data/")
        await page.wait_for_load_state("networkidle")
        
        content = await page.content()
        with open("analysis/page.html", "w") as f:
            f.write(content)
            
        # Also take a screenshot of the full page
        await page.screenshot(path="analysis/full_page.png", full_page=True)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
