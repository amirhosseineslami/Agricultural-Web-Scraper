import asyncio
from playwright.async_api import async_playwright
from searchInDigikoud import SearchInDigikoud
from searchInKoodforosh import SearchInKoodforosh
from priceBook import PriceBook
from searchInDigikood import SearchInDigikood
from searchInTorob import SearchInTorob
            
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        #await SearchInTorob(page).get_all_prices()

        await SearchInDigikood(page).get_all_prices()
        await SearchInKoodforosh(page).get_all_prices()
        await SearchInDigikoud(page).get_all_prices()
        

asyncio.run(main())

