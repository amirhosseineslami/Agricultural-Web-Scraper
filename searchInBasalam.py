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
TIMEOUT_FOR_FINDING_NEXTPAGE_KEY = 155000
import re

import re

# Example mappings
PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٫", "0123456789.")

# Units and their conversion to kilograms
# volume-based units assume water density ~1g/ml if needed
UNIT_KEYWORDS = {
    "کیلوگرم": 1,
    "کیلو": 1,
    "کیلویی": 1,
    "کیلوئی": 1,
    "کیلوگرمی": 1,
    "گرم": 0.001,
    "گرمی": 0.001,
    "g": 0.001,
    "kg": 1,
    "تن": 1000,
    "لیتر": 1,  # assuming 1L = 1kg (water-like density)
    "لیتری": 1,
    "میلی‌لیتر": 0.001,
    "میلی لیتر": 0.001,
    "سی‌سی": 0.001,
    "سی سی": 0.001,
    "ml": 0.001,
    "l": 1,
}

# Regex-friendly keys including fuzzy/combined ones
UNIT_PATTERN = "|".join(
    sorted([re.escape(k) for k in UNIT_KEYWORDS], key=len, reverse=True)
)
# Persian/Arabic digits to Latin
PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٫", "0123456789.")


class SearchInBasalam:
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
        self, product_dic: dict = None
    ) -> list[dict]:
        if product_dic == None or "url" not in product_dic.keys():
            product_dic["url"] = (
                "https://basalam.com/cat/tools/%D8%AE%D8%A7%DA%A9-%DA%A9%D9%88%D8%AF-%D8%B3%D9%85%D9%88%D9%85"
            )

        elif (product_dic["url"]) == None:
            product_dic["url"] = (
                "https://basalam.com/cat/tools/%D8%AE%D8%A7%DA%A9-%DA%A9%D9%88%D8%AF-%D8%B3%D9%85%D9%88%D9%85"
            )

        # Search in subsequential
        await self.page.goto(product_dic["url"], timeout=TIMEOUT)

        print("here we're in the specific fertilizer category page")

        while True:
            # Assumes you're already on a fertilizer page
            product_blocks = await self.page.locator("a.EaqW1o.tED1ki._77T3WS").all()

            products = []
            book = PriceBook()

            for block in product_blocks:
                try:
                    # Get the <a> with class "product-name"
                    # name_el = block.locator("h3.wd-entities-title")
                    name = await block.locator("h2.Zkctoc.kLgrzf").inner_text()
                    href = "https://basalam.com" + await block.get_attribute("href")
                    print(name, href)

                    # Get the price
                    # Get the price element from the block
                    price_el = block.locator("span.VVeeBY")
                    price = None

                    try:
                        # Check if it exists
                        if await price_el.count() > 0:
                            price = await price_el.first.inner_text()
                        else:
                            price = "N/A"

                    except Exception as e:
                        traceback.print_exc()

                    product_dic = {
                        "name": name.strip(),
                        "price": price.strip(),
                        "url": href,
                        "category": product_dic["category"],
                    }
                    products.append(product_dic)
                    book.upsert(product_dic)
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

            next_page_locator = self.page.locator(
                "span.bs-pagination__arrow.bs-pagination__arrow--show"
            ).last
            next_page_link = None
            if await next_page_locator.inner_text() != "بعدی":
                break
            try:
                next_page_link = (
                    "https://basalam.com"
                    + await next_page_locator.get_attribute(
                        "href", timeout=TIMEOUT_FOR_FINDING_NEXTPAGE_KEY
                    )
                )
            except Exception as e:
                print(f"No next page found!{traceback.format_exc()}")

            if next_page_link is not None:
                print(next_page_link)
                await self.page.goto(next_page_link, timeout=TIMEOUT)

            else:
                break

        return products

    async def get_price_per_kg(
        self, product_dic: dict
    ) -> dict[str, float | str] | None:
        is_product_available = True
        try:
            await self.page.goto(product_dic["url"], timeout=TIMEOUT)

            # Find the locator for the span inside the 'out of stock' paragraph
            # out_of_stock_span = self.page.locator(
            #     "p.stock.out-of-stock.wd-style-default"
            # )
            # count = 0
            # try:
            #     count = await out_of_stock_span.count()
            # except Exception as e:
            #     print(traceback.format_exc())

            # # Check if the element exists
            # if out_of_stock_span is not None and count > 0:
            #     exist_text = await out_of_stock_span.first.inner_text()
            #     print(exist_text)  # e.g., "ناموجود"
            #     product_dic["is_available"] = False
            #     is_product_available = False

            full_text_price = product_dic["price"]
            digits_only = re.sub(r"[^\d]", "", str(full_text_price))  # → "1775000"
            price = int(digits_only)

            unit_kg_locator = self.page.locator(
                "p.bs-text.bs-text--body-sm.bs-text--fs-14"
            ).first
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
        rawProducts = (
            await self.extract_products_from_specific_fertilizer_category_page(
                {"category": "nan"}
            )
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

    # The function
    async def extract_amount_and_unit(
        self, text: str
    ) -> tuple[float | None, str | None]:
        """
        Extract and convert any weight or volume unit in Persian/English to kg.
        Returns (amount_in_kg: float | None, original_unit: str | None)
        """

        # Normalize Persian digits and decimal points
        normalized = text.translate(PERSIAN_TO_LATIN).replace(",", "")

        # Match pattern like "5 لیتر", "250گرمی", etc.
        pattern = rf"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>{UNIT_PATTERN})"
        match = re.search(pattern, normalized, flags=re.IGNORECASE)

        if match:
            raw_amount = match.group("amount")
            raw_unit = match.group("unit")

            try:
                amount = float(raw_amount)
            except ValueError:
                return None, None

            conversion_factor = UNIT_KEYWORDS.get(raw_unit.strip(), None)
            if conversion_factor is None:
                return None, raw_unit

            amount_in_kg = amount * conversion_factor
            return amount_in_kg, raw_unit

        return None, None
