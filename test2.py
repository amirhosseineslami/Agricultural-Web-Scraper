import asyncio
from playwright.async_api import async_playwright
from searchInDigikoud import SearchInDigikoud
from searchInKoodforosh import SearchInKoodforosh

TIMEOUT = 6000_000

async def test():

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        



        CATEGORY_URL = "https://www.digikood.com/"
        await page.goto(CATEGORY_URL, timeout=60_000)


        try:
            # ── 1.  Locate the <h3 class="wd-entities-title"> inside the grid item
            title_locators = page.locator("h3.wd-entities-title")
            
            for title_locator in title_locators:

                raw_title = await title_locator.text_content()             # e.g. "کود های پتاسه (10)"
                print(raw_title)

                # ── 2.  Strip off anything from the first "(" onward
                category_name = raw_title.split("(")[0].strip()
                print("Category name:", category_name)                     # → کود های پتاسه


        except TimeoutError:
            print("Could not find the title in time.")



asyncio.run(test())