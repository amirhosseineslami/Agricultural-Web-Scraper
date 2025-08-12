import asyncio
from playwright.async_api import async_playwright
from searchInDigikoud import SearchInDigikoud
from searchInKoodforosh import SearchInKoodforosh
from priceBook import PriceBook
from searchInDigikood import SearchInDigikood
from searchInTorob import SearchInTorob
from searchInAgriplus import SearchInAgriplus
from searchInSepahankesht import SearchInSepahankesht
from searchInRoyalkesht import SearchInRoyalkesht
from searchInBasalam import SearchInBasalam


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await SearchInBasalam(page=page).get_all_prices()
        await SearchInDigikood(page).get_all_prices()
        await SearchInKoodforosh(page).get_all_prices()
        await SearchInDigikoud(page).get_all_prices()
        await SearchInSepahankesht(page=page).get_all_prices()
        await SearchInRoyalkesht(page=page).get_all_prices()
        await SearchInTorob(page).get_all_prices()
        await SearchInAgriplus(page).get_all_prices()

        input("Finished")


asyncio.run(main())
