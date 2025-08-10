from playwright.async_api import Page
import asyncio, re, traceback
from playwright.async_api import Page
import asyncio, re
from typing import List, Dict, Optional, Tuple, Union
import re
from typing import List, Dict
import traceback
from priceBook import PriceBook
from unitExtractor import UnitExtractor

TIMEOUT = 4500000
TIMEOUT_FOR_FINDING_NEXTPAGE_KEY = 1000
import re


# Persian/Arabic digits to Latin
PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٫", "0123456789.")

# Map Persian unit words to normalized English equivalents
UNIT_KEYWORDS = {
    "لیتر": "liter",
    "لیتری": "liter",
    "ل": "liter",
    "کیلوگرم": "kg",
    "کیلوگرمی": "kg",
    "کیلو": "kg",
    "کیلوئی": "kg",
    "کیلویی": "kg",
    "گرم": "g",
    "گرمی": "g",
    "g": "g",
}
import re

# Persian/Arabic digits to Latin
PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٫", "0123456789.")

# Map Persian unit words to normalized English equivalents
UNIT_KEYWORDS = {
    "لیتر": "liter",
    "لیتری": "liter",
    "ل": "liter",
    "کیلوگرم": "kg",
    "کیلوگرمی": "kg",
    "کیلو": "kg",
    "کیلوئی": "kg",
    "کیلویی": "kg",
    "گرم": "g",
    "گرمی": "g",
    "g": "g",
}


class SearchInSepahankesht:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://sepahankesht.com/"

    async def run(self):
        try:
            await self.page.goto(self.url, timeout=TIMEOUT)
            # Adjust the selector based on the site's search input

            await asyncio.sleep(60)  # keeps the browser open for 60 seconds

        except Exception as e:
            print(f"Error searching Sepahankesht: {e}")

    async def getListOfFertilizerCategories(self) -> list[dict]:
        list_url = "https://sepahankesht.com/"

        await self.page.goto(list_url, timeout=TIMEOUT)

        firstLocator = self.page.locator(
            "ul.wd-sub-menu.wd-sub-accented.wd-grid-f-inline.color-scheme-dark"
        )
        print(firstLocator.all)

        selector = "li"

        categories = firstLocator.locator(selector)

        categories_counts = await categories.count()

        print(categories_counts)

        result = []

        allcat = categories.first

        link_locator = await allcat.locator("a").all()

        for link in link_locator:
            name = await link.inner_text()
            print(name)
            url = await link.get_attribute("href")
            if len(name) < 2:
                name = url.split("/")[-1]

            result.append(
                {
                    "category": name.strip(),
                    "url": url,
                }
            )

            print(
                f"""
                  category:{name.strip()}
                  Url:{url}
"""
            )

        return result

    async def extract_products_from_specific_fertilizer_category_page(
        self, product_dic
    ) -> list[dict]:

        # Search in subsequential
        await self.page.goto(product_dic["url"], timeout=TIMEOUT)

        print("here we're in the specific fertilizer category page")

        while True:
            # Assumes you're already on a fertilizer page
            product_blocks = await self.page.locator("div.product-element-bottom").all()

            products = []

            for block in product_blocks:
                try:
                    # Get the <a> with class "product-name"
                    name_el = block.locator("h3.wd-entities-title")
                    name = await name_el.inner_text()
                    href = await name_el.locator("a").get_attribute("href")

                    # Get the price
                    # Get the price element from the block
                    price_el = block.locator(
                        "span.woocommerce-Price-amount.amount >> bdi"
                    )

                    # Check if it exists
                    if await price_el.count() > 0:
                        price = await price_el.first.inner_text()
                    else:
                        price = "N/A"

                    products.append(
                        {
                            "name": name.strip(),
                            "price": price.strip(),
                            "url": href,
                            "category": product_dic["category"],
                        }
                    )
                    print(
                        f"""
    name: {name.strip()}
    price: {price.strip()}
    url: {href}
    category: {product_dic["category"]}
                        """
                    )
                except Exception as e:
                    print(
                        f"⚠️ Skipping a product due to error: {traceback.format_exc()}"
                    )

            next_page_locator = self.page.locator("a.next.page-numbers")
            next_page_text = None
            next_page_link = None
            try:
                next_page_text = await next_page_locator.inner_text(
                    timeout=TIMEOUT_FOR_FINDING_NEXTPAGE_KEY
                )
                next_page_link = await next_page_locator.get_attribute(
                    "href", timeout=TIMEOUT_FOR_FINDING_NEXTPAGE_KEY
                )
            except Exception as e:
                print(f"No next page found!{traceback.format_exc}")

            if next_page_text is not None and next_page_link is not None:
                print(next_page_link, next_page_text)
                await self.page.goto(next_page_link, timeout=TIMEOUT)

            else:
                break

        return products

    async def get_price_per_kg(self, product_dic) -> dict[str, float | str] | None:
        is_product_available = True
        try:
            await self.page.goto(product_dic["url"], timeout=TIMEOUT)

            # Find the locator for the span inside the 'out of stock' paragraph
            out_of_stock_span = self.page.locator(
                "p.stock.out-of-stock.wd-style-default"
            )
            count = 0
            try:
                count = await out_of_stock_span.count()
            except Exception as e:
                print(traceback.format_exc())

            # Check if the element exists
            if out_of_stock_span is not None and count > 0:
                exist_text = await out_of_stock_span.first.inner_text()
                print(exist_text)  # e.g., "ناموجود"
                product_dic["is_available"] = False
                is_product_available = False

            full_text_price = product_dic["price"]
            digits_only = re.sub(r"[^\d]", "", full_text_price)  # → "1775000"
            price = int(digits_only)

            unit_kg_locator = self.page.locator("span.wd-attr-term").first
            print(unit_kg_locator)

            kg = None
            unit_kg_text = None
            try:
                unit_kg_text = await unit_kg_locator.inner_text()  # now it's a str
                kg, unit = await UnitExtractor().extract_amount_and_unit(unit_kg_text)
            except Exception as e:
                print(traceback.format_exc())

            # 1) get the visible text
            if kg is not None:
                print(unit_kg_text)
            else:
                kg, unit = await UnitExtractor().extract_amount_and_unit(
                    product_dic["name"]
                )
                if kg is not None and int(kg) > 0:
                    product_dic["amount_kg"] = kg
                else:
                    product_dic["amount_kg"] = "nan"
                    kg = None

            price_per_kg = 0

            # Final calculation
            if kg is not None and kg > 0:
                price_per_kg = price / kg
            else:
                price_per_kg = "nan"

            # If Price wasn't logical

            if price <= 0:
                price = "nan"
                price_per_kg = "nan"

            print(
                f"""
    name: {product_dic["name"]}
    total price: {price}
    price/kg: {price_per_kg}
url: {product_dic["url"]}
amount_kg:{kg},
"is_available":{is_product_available}
    """
            )
            product_dic["price_per_kg"] = PriceExtractor().extract_price_and_currency(
                price_per_kg
            )
            product_dic["price"] = PriceExtractor().extract_price_and_currency(price)
            product_dic["amount_kg"] = kg
            product_dic["is_available"] = is_product_available
            return product_dic

        except Exception as e:
            print(f"❌ Error parsing price per kg: {traceback.format_exc()}")
            return product_dic

    async def get_all_prices(self):
        book = PriceBook()
        finalList = []

        listOfSorts = await self.getListOfFertilizerCategories()
        for sort in listOfSorts:
            rawProducts = (
                await self.extract_products_from_specific_fertilizer_category_page(sort)
            )

            for rawProduct in rawProducts:
                fullData = await self.get_price_per_kg(rawProduct)
                finalList.append(fullData)
                try:
                    book.upsert(fullData)
                except Exception as e:
                    print(traceback.format_exc())

        return finalList

    async def auto_scroll_to_bottom(
        self,
        wait_time: int = 2000,
        scroll_pause: int = 1000,
    ):
        print("🔽 Starting auto-scroll...")

        prev_count = 0
        same_count_tries = 0

        while True:
            # Count the number of product cards
            product_cards = await self.page.locator("div.product-small.box").all()
            current_count = len(product_cards)
            print(f"📦 Product count: {current_count}")

            if current_count == prev_count:
                same_count_tries += 1
                if same_count_tries >= 1:
                    print("✅ No new products loaded. Stopping scroll.")
                    break
            else:
                same_count_tries = 0

            prev_count = current_count

            # Scroll to the bottom
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(scroll_pause)
