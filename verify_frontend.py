
import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Create screenshots directory
        if not os.path.exists('screenshots'):
            os.makedirs('screenshots')

        # 1. Verify Docs Page
        await page.goto(f'file://{os.getcwd()}/docs.html')
        await page.screenshot(path='screenshots/docs.png', full_page=True)
        print("Captured screenshots/docs.png")

        # 2. Verify SFLN Transfer Page (Empty)
        await page.goto(f'file://{os.getcwd()}/demoservice/js-transfer.html')
        await page.screenshot(path='screenshots/transfer_empty.png', full_page=True)
        print("Captured screenshots/transfer_empty.png")

        # 3. Verify SFLN Transfer Page (Paired via Hash)
        await page.goto(f'file://{os.getcwd()}/demoservice/js-transfer.html#test-node-12345')
        await page.reload() # Ensure hash is processed
        await page.wait_for_timeout(1000)
        await page.screenshot(path='screenshots/transfer_paired.png', full_page=True)
        print("Captured screenshots/transfer_paired.png")

        # 4. Click "Share Link" and capture
        await page.click('a:has-text("共有リンク")')
        await page.wait_for_timeout(500)
        await page.screenshot(path='screenshots/transfer_share.png', full_page=True)
        print("Captured screenshots/transfer_share.png")

        # 5. Verify Main Index Links
        await page.goto(f'file://{os.getcwd()}/index.html')
        links = await page.query_selector_all('a')
        for link in links:
            text = await link.inner_text()
            href = await link.get_attribute('href')
            if "SFLN Transfer" in text:
                print(f"Verified Transfer Link: {text} -> {href}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
