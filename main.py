import asyncio
from playwright.async_api import async_playwright
from searchInDigikoud import SearchInDigikoud
from searchInKoodforosh import SearchInKoodforosh
from priceBook import PriceBook
from searchInDigikood import SearchInDigikood
            
async def main():
    async with async_playwright() as p:
        data = []
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        #await SearchInDigikood(page).get_price_per_kg("https://www.digikood.com/product/%d8%a7%d9%88%d8%b1%d9%87-%d8%b3%d9%88%d9%84%d9%81%d8%a7%d8%aa/","fdsa","fsdaf")
        
        data += await SearchInKoodforosh(page).get_all_prices()
        data += await SearchInDigikoud(page).get_all_prices()
        data += await SearchInDigikood(page).get_all_prices()

        print(data)
        

asyncio.run(main())

