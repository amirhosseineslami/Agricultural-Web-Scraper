import asyncio
from playwright.async_api import async_playwright
from searchInDigikoud import SearchInDigikoud
from searchInKoodforosh import SearchInKoodforosh



async def test():

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()


        await page.goto("https://koodforosh.com/showads/3167",timeout=60000)

        price_span = await page.query_selector(".innerpage-advertising-span")
        if not price_span:
            print("❌ price span not found")
            return

        


        raw_price = (await price_span.inner_text()).strip()
        print("Raw price text:", raw_price)


        product_name_el = await page.query_selector(".h1.h1")
        product_name = (await product_name_el.inner_text()).strip()
        print(product_name)



asyncio.run(test())