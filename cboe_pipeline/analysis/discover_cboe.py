import asyncio
import os
import json
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launch browser with devtools to capture network
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            record_har_path="analysis/cboe_download.har",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Navigating to Cboe...")
        await page.goto("https://www.cboe.com/us/options/market_statistics/historical_data/")
        
        # Wait for the form to load
        # Use simple selectors based on likely structure or visual text
        try:
            await page.wait_for_selector("input[name='symbol']", timeout=10000)
            print("Form found.")
        except:
            print("Form selector not found immediately, dumping page content...")
            await page.screenshot(path="analysis/page_dump.png")
            # Continue anyway to see if we can find it by text
        
        # Fill symbol
        await page.fill("input[name='symbol']", "SPY")
        
        # NOTE: The date selection might be a dropdown or input. 
        # I'll try to find it. Inspecting common patterns. 
        # Usually Cboe has a "Download" button.
        
        # Let's interactively solve this or try to be generic. 
        # For this script, I will try to just keep the page open for a few seconds to let network settle
        # and see if there are XHRs on load. 
        # But the prompt requires "submit at least one download".
        
        # If I can't predict the selector, I might need to inspect it first.
        # However, I will try to "click" the Download button if I find it.
        
        try:
            # Attempt to find a button with text "Download"
            async with page.expect_request(lambda request: "historical_data" in request.url and request.method == "POST") as request_info:
                await page.click("button:has-text('Download')")
                request = await request_info.value
                print(f"Captured Request: {request.url}")
                print(f"Method: {request.method}")
                print(f"Headers: {request.headers}")
                print(f"Post Data: {request.post_data}")
                
        except Exception as e:
            print(f"Could not automatically click download: {e}")
            print("Taking screenshot...")
            await page.screenshot(path="analysis/failed_click.png")

        # Keep open for a bit to ensure HAR is saved
        await asyncio.sleep(5)
        
        await context.close()
        await browser.close()

if __name__ == "__main__":
    if not os.path.exists("analysis"):
        os.makedirs("analysis")
    asyncio.run(run())
