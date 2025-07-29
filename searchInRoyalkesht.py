from playwright.async_api import Page
import asyncio, re, traceback
from playwright.async_api import Page
import asyncio, re
from typing import List, Dict, Optional, Tuple, Union
import re
from typing import List, Dict
import traceback
from priceBook import PriceBook

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


class SearchInRoyalkesht:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://royalkesht.com/"

    async def run(self):
        try:
            await self.page.goto(self.url, timeout=TIMEOUT)
            # Adjust the selector based on the site's search input

            await asyncio.sleep(60)  # keeps the browser open for 60 seconds

        except Exception as e:
            print(f"Error searching Sepahankesht: {e}")

    async def getListOfOnePageFertilizerCategories(self, page_url) -> list[dict]:

        await self.page.goto(page_url, timeout=TIMEOUT)

        firstLocator = self.page.locator("article.single-product-item")
        print(firstLocator.all)

        selector = "div.text"
        selector1 = "h3.title"

        categories = firstLocator.locator(selector).locator(selector1)

        categories_counts = await categories.count()

        print(categories_counts)

        result = []

        link_locator = await categories.locator("a").all()

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

        return result, page_url

    async def getListOfAllPagesFertilizerCategories(self) -> list[dict]:
        categoriesFinalList = []
        next_page_link = "https://royalkesht.com/%DA%A9%D9%88%D8%AF/page/1"

        while True:
            newList, next_page_link = await self.getListOfOnePageFertilizerCategories(
                next_page_link
            )
            categoriesFinalList += newList

            # check the next page
            try:
                nextPageText = next_page_link.split("/")[-1]
                print(nextPageText)
                nextPageNumber = int(nextPageText) + 1
                if nextPageNumber == 3:
                    return categoriesFinalList
                next_page_link = (
                    f"https://royalkesht.com/%DA%A9%D9%88%D8%AF/page/{nextPageNumber}"
                )

            except Exception as e:
                print(traceback.format_exc)
                return categoriesFinalList

    async def extract_products_from_specific_fertilizer_category_page(
        self, product_dic
    ) -> list[dict]:

        # Search in subsequential
        await self.page.goto(product_dic["url"], timeout=TIMEOUT)

        print("here we're in the specific fertilizer category page")

        # Assumes you're already on a fertilizer page
        firstblock = self.page.locator("section.d-flex.flex-column.align-items-top")

        product_blocks = await firstblock.locator(
            "div.sub-hero-list.m-flex-column.mt-5 >> div"
        ).all()
        print(product_blocks)

        products = []

        for block in product_blocks:
            try:
                print(f"{product_blocks.index(block)}th product")
                # Get the <a> with class "product-name"
                name_el = block.locator("h4")
                name = await name_el.inner_text(
                    timeout=TIMEOUT_FOR_FINDING_NEXTPAGE_KEY
                )
                href = (
                    await block.locator("div.more.text-center.mt-2")
                    .locator("a")
                    .get_attribute("href")
                )

                # Get the price
                # Get the price element from the block
                price_el = block.locator("span.price")

                # Check if it exists
                if await price_el.count() > 0:
                    price = await price_el.first.inner_text()
                else:
                    price = "N/A"

                products.append(
                    {
                        "name": name.strip(),
                        "price": price.strip(),
                        "price_per_kg": price.strip(),
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
                url = product_dic["url"]
                cat = product_dic["category"]
                print(
                    f"{url}{cat}⚠️ Skipping a product due to error: {traceback.format_exc()}"
                )

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
                kg, unit = await self.extract_amount_and_unit(unit_kg_text)
            except Exception as e:
                print(traceback.format_exc())

            # 1) get the visible text
            if kg is not None:
                print(unit_kg_text)
            else:
                kg, unit = await self.extract_amount_and_unit(product_dic["name"])
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
            product_dic["price_per_kg"] = price_per_kg
            product_dic["price"] = price
            product_dic["amount_kg"] = kg
            product_dic["is_available"] = is_product_available
            return product_dic

        except Exception as e:
            print(f"❌ Error parsing price per kg: {traceback.format_exc()}")
            return product_dic

    async def get_all_prices(self):
        book = PriceBook()
        finalList = []

        listOfSorts = await self.getListOfAllPagesFertilizerCategories()
        for sort in listOfSorts:
            rawProducts = (
                await self.extract_products_from_specific_fertilizer_category_page(sort)
            )
            print("rawproducts", rawProducts)

            for rawProduct in rawProducts:
                finalList.append(rawProduct)
                try:
                    book.upsert(rawProduct)
                except Exception as e:
                    traceback.print_exc()

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

    async def extract_amount_and_unit(
        self, text: str
    ) -> tuple[float | None, str | None]:
        """
        Extract number and unit from Persian product text.
        Returns (amount: float | None, unit: str | None)
        """

        # Step 1: Normalize digits first!
        normalized = text.translate(PERSIAN_TO_LATIN)

        # Step 2: Create a regex pattern like: "5 لیتر", "5لیتر", "250 گرمی", etc.
        unit_pattern = "|".join(re.escape(unit) for unit in UNIT_KEYWORDS.keys())
        pattern = rf"(\d+(?:\.\d+)?)\s*({unit_pattern})"

        match = re.search(pattern, normalized, flags=re.IGNORECASE)

        if match:
            amount = float(match.group(1))
            unit = UNIT_KEYWORDS.get(match.group(2), match.group(2))
            return amount, unit

        return None, None
