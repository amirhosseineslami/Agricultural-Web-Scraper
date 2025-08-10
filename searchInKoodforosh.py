from playwright.async_api import Page
import asyncio, re
from typing import List, Dict, Optional, Tuple, Union
import re
from typing import List, Dict
import traceback

TIMOUT_TIME = 35_000
from priceBook import PriceBook

PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


class SearchInKoodforosh:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://koodforosh.com/"

    async def run(self):
        try:
            await self.page.goto(self.url, timeout=30000)
            # Adjust the selector based on the site's search input

            await asyncio.sleep(60)  # keeps the browser open for 60 seconds

        #     search_selector = 'input[type="search"], input[name="q"], input[placeholder*="search"]'

        #     search_box = await self.page.wait_for_selector(search_selector, timeout=5000)
        #     await search_box.fill(query)
        #     await search_box.press("Enter")

        #     # Wait some time for the results to load
        #     await self.page.wait_for_timeout(5000)
        #     print(f"Search for '{query}' completed on Digikoud.")

        except Exception as e:
            print(f"Error searching Koodforosh: {e}")

    async def get_fertilizer_categories_list(self) -> List[Dict[str, str]]:
        url = "https://koodforosh.com"
        await self.page.goto(url, timeout=TIMOUT_TIME)

        # wait until the list is on the page
        await self.page.wait_for_selector("ul.country-sales li a")

        anchors = await self.page.query_selector_all("ul.country-sales li a")

        fertilizer_categories: List[Dict[str, str]] = []
        for a in anchors:
            text = (await a.inner_text()).strip()
            if "کود" in text:  # keep only fertilizer items
                href = await a.get_attribute("href")  # absolute URL from the DOM
                fertilizer_categories.append({"category": text, "url": href})

        print(fertilizer_categories)
        return fertilizer_categories

    #     async def extract_products_from_specific_fertilizer_page(self,url:str) -> list[dict]:

    #         await self.page.goto(url,timeout=60000)
    #         print("here we're in the specific fertilizer page")

    #         # Assumes you're already on a fertilizer page like: https://digikoud.com/21-کود-های-مرکب
    #         product_blocks = await self.page.query_selector_all(".product-meta")

    #         products = []

    #         for block in product_blocks:
    #             try:
    #                 # Get the <a> with class "product-name"
    #                 name_el = await block.query_selector("a.product-name")
    #                 name = await name_el.inner_text()
    #                 href = await name_el.get_attribute("href")

    #                 # Get the price
    #                 price_el = await block.query_selector(".price.product-price")
    #                 price = await price_el.inner_text() if price_el else "N/A"

    #                 products.append({
    #                     "name": name.strip(),
    #                     "price": price.strip(),
    #                     "url": href
    #                 })
    #                 print(f"""
    # name: {name.strip()}
    # price: {price.strip()}
    # url: {href}
    #                       """)
    #             except Exception as e:
    #                 print(f"⚠️ Skipping a product due to error: {e}")

    #         return products

    async def extract_products_from_specific_fertilizer_page(
        self, url: str, category_name: str
    ) -> List[Dict[str, str | int]]:
        """Scrape one fertilizer‑listing page and return [{name, price, url}, …]."""

        products: List[Dict[str, str | int]] = []
        await self.page.goto(url, timeout=TIMOUT_TIME)
        await self.auto_scroll_to_bottom()

        try:
            await self.page.wait_for_selector(".product-content")

        except Exception as e:
            print(traceback.format_exc())
            return products

        cards = await self.page.query_selector_all(".product-content")

        for card in cards:
            try:
                # --- name & link -------------------------------------------------
                a_el = await card.query_selector("a")
                href = await a_el.get_attribute("href")
                name = (await a_el.inner_text()).strip()

                # --- price -------------------------------------------------------
                price_el = await card.query_selector(".product-price")
                raw_price = (await price_el.inner_text()).strip()

                # raw_price sample: "قیمت : ۹۹,۰۰۰ تومان"
                # 1) keep only the first group of digits with comma separators
                m = re.search(r"([\d,]+)", raw_price.translate(PERSIAN_TO_LATIN))
                price = int(m.group(1).replace(",", "")) if m else None

                products.append(
                    {
                        "name": name,
                        "price": price,
                        "url": href,
                        "category": category_name,
                    }
                )

            except Exception as e:
                print(f"⚠️  Skipped a product due to error: {e}")

        return products

    async def get_price_per_kg(
        self, productUrl, category
    ) -> Dict[str, str | float] | None:
        try:
            await self.page.goto(productUrl, timeout=60000)

            product_name_el = await self.page.query_selector(".h1.h1")
            product_name = (await product_name_el.inner_text()).strip()
            print(product_name)

            price_span = await self.page.query_selector(".innerpage-advertising-span")
            if not price_span:
                print("❌ price span not found")
                return

            raw_price = (await price_span.inner_text()).strip()
            print("Raw price text:", raw_price)

            if ("ماه" in raw_price) or ("سال" in raw_price) or ("رایگان" in raw_price):
                raw_price = "nan"

            # Final calculation
            print(
                f"""
    name: {product_name}
    total price: {raw_price}
    price/kg: "nan"
    category: {category}
    """
            )
            return {
                "name": product_name,
                "url": productUrl,
                "price_per_kg": "nan",
                "price": raw_price,
                "category": category,
            }

        except Exception as e:
            print(f"❌ Error parsing price per kg: {e}")
            return None

    async def get_all_prices(self) -> List[Dict[str, str | float]]:
        book = PriceBook()

        all_products_and_prices: List[Dict[str, str | float]] = []

        listOfSorts = await self.get_fertilizer_categories_list()
        for sort in listOfSorts:
            rawProducts = await self.extract_products_from_specific_fertilizer_page(
                sort["url"], sort["category"]
            )

            for rawProduct in rawProducts:
                fullData = await self.get_price_per_kg(
                    rawProduct["url"], rawProduct["category"]
                )
                all_products_and_prices.append(fullData)

                try:
                    book.upsert(fullData)
                except Exception as e:
                    print(traceback.format_exc())

        return all_products_and_prices

    async def auto_scroll_to_bottom(self):
        await self.page.wait_for_timeout(2000)

        last_height = await self.page.evaluate("() => document.body.scrollHeight")

        while True:
            await self.page.evaluate(
                """() => {
                    return new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 100;
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            totalHeight += distance;

                            if (totalHeight >= document.body.scrollHeight) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }"""
            )
            await self.page.wait_for_timeout(1500)

            new_height = await self.page.evaluate("() => document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
