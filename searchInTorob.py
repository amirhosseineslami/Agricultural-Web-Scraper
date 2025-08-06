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
from priceExractor import PriceExtractor

PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
BLACK_LIST_PRODUCTS = []
TIMEOUT = 4500000

# Persian and English digits mapping
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ENGLISH_DIGITS = "0123456789"
PERSIAN_TO_ENGLISH = str.maketrans("".join(PERSIAN_DIGITS), "".join(ENGLISH_DIGITS))


# Unit keywords to look for
UNIT_KEYWORDS = ["لیتر", "لیتری", "کیلوگرم", "کیلو", "کیلوئی", "کیلویی", "کیلوگرمی"]

# Build regex pattern dynamically
unit_pattern = "|".join(UNIT_KEYWORDS)
pattern = re.compile(rf"(\d+|[۰-۹]+)\s*({unit_pattern})")


class SearchInTorob:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://torob.com/"

    async def run(self):
        try:
            await self.page.goto(self.url, timeout=TIMEOUT)
            # Adjust the selector based on the site's search input

            await asyncio.sleep(60)  # keeps the browser open for 60 seconds

        except Exception as e:
            print(f"Error searching torob: {e}")

    async def getListOfFertilizerCategories(self) -> list[dict]:
        list_url = "https://torob.com/"

        await self.page.goto(list_url, timeout=TIMEOUT)

        selector = "div.hover-mask"
        categories = await self.page.query_selector_all(selector)
        print(categories)

        result = []

        for i in range(11):
            link = categories[i]
            name = await (
                await link.query_selector("h3.wd-entities-title")
            ).inner_text()
            url = await (await link.query_selector("a")).get_attribute("href")

            # Try to extract count from the <span> inside
            span = await link.query_selector("span")
            count = 0
            if span:
                text = await span.inner_text()
                try:
                    count = int(text.strip())
                except:
                    pass  # Ignore parse errors

            result.append(
                {
                    "category": name.strip(),
                    "count": count,
                    "url": url + "?per_page=400/",
                }
            )

            print(
                f"""
                  category:{name.strip()}
                  Url:{url}?per_page=400/
                  Count:{count}
"""
            )

        return result

    async def extract_products_from_specific_fertilizer_category_page(
        self,
        url: str = "https://torob.com/browse/440/%D8%AE%D8%A7%DA%A9-%DA%A9%D9%88%D8%AF-%D9%88-%D8%B3%D9%85%D9%88%D9%85-fertilizer/",
        category: str | None = "nan",
    ) -> list[dict]:

        await self.page.goto(url, timeout=TIMEOUT)
        print("here we're in the specific fertilizer category page")

        await self.auto_scroll_to_bottom()
        print("Now we're totaly in the bottom of the website!")

        all_products_block = self.page.locator("div.ProductCards_cards__MYvdn").first
        print(all_products_block)

        product_blocks = await all_products_block.locator("a").all()
        print(product_blocks)
        print(product_blocks.count)

        products = []

        book = PriceBook()

        for block in product_blocks:
            try:

                # Extract href
                href = "https://torob.com" + await block.get_attribute("href")
                print(href)

                product_name = await block.locator(
                    "h2.ProductCard_desktop_product-name__JwqeK"
                ).inner_text()

                # filter just fertilizers
                if product_name in BLACK_LIST_PRODUCTS:
                    continue

                amount_kg = 0
                # get kg from name of the product
                amount_kg_list: list = await self.extract_amount(product_name)
                if len(amount_kg_list) > 0:
                    amount_kg = int(amount_kg_list[0][0])

                product_price = await block.locator(
                    "div.ProductCard_desktop_product-price-text__y20OV"
                ).inner_text()

                digits_only = PriceExtractor().extract_price_and_currency(product_price)
                pure_price_int = int(digits_only)

                is_available = False
                if pure_price_int > 0:
                    is_available = True

                if amount_kg > 0:
                    price_per_kg = pure_price_int / amount_kg
                else:
                    price_per_kg = "nan"
                    amount_kg = "nan"

                product_detail_dictionary = {
                    "name": product_name,
                    "price": pure_price_int,
                    "url": href,
                    "category": category,
                    "is_available": is_available,
                    "amount_kg": amount_kg,
                    "price_per_kg": price_per_kg,
                }
                products.append(product_detail_dictionary)

                # save to excel directly
                book.upsert(product_detail_dictionary)
                print(product_detail_dictionary)

            except Exception as e:
                print(f"⚠️ Skipping a product due to error: {traceback.format_exc()}")

        return products

    async def get_price_per_kg(self, product_dict) -> dict[str, float | str] | None:
        is_product_available = True
        try:

            if (product_dict["amount_kg"] not in ["nan", None, -1, "None"]) and (
                product_dict["amount_kg"] > 0
            ):
                # If product's kg is already found by its name just return
                return product_dict

            await self.page.goto(product_dict["url"], timeout=TIMEOUT)

            unit_kg_locators = await self.page.locator(
                "div.jsx-d9bfdb7eefd5a6bf.detail-value"
            ).all()

            for unit_kg_locator in unit_kg_locators:
                amount_kg_str = await unit_kg_locator.inner_text()

                amount_kg = 0
                # get kg from name of the product
                amount_kg_list: list = UnitExtractor().extract_amount_and_unit(
                    amount_kg_str
                )
                if len(amount_kg_list) > 0:
                    amount_kg = int(amount_kg_list[0][0])

                if amount_kg > 0:
                    print(amount_kg_str)
                    product_dict["price_per_kg"] = (
                        int(product_dict["price"]) / amount_kg
                    )
                    return product_dict

            return product_dict

        except Exception as e:
            print(f"❌ Error parsing price per kg: {traceback.format_exc()}")
            return None

    async def get_all_prices(self):

        finalProductsList = []

        raw_products = (
            await self.extract_products_from_specific_fertilizer_category_page()
        )
        for i in range(len(raw_products)):
            print(f"""{i}/{len(raw_products)}""")
            rawProduct = raw_products[i]
            finalProduct = await self.get_price_per_kg(rawProduct)
            finalProductsList.append(finalProduct)

        return finalProductsList

    async def auto_scroll_to_bottom(
        self, wait_time: int = 2000, scroll_pause: int = 1000
    ):
        print("🔽 Starting auto-scroll...")

        prev_count = 0
        same_count_tries = 0

        while True:
            # Count the number of product cards
            product_cards = await self.page.locator(
                "div.ProductCards_cards__MYvdn a"
            ).all()
            current_count = len(product_cards)
            print(f"📦 Product count: {current_count}")

            if current_count == prev_count:
                same_count_tries += 1
                if same_count_tries >= 2:
                    print("✅ No new products loaded. Stopping scroll.")
                    break
            else:
                same_count_tries = 0

            prev_count = current_count

            # Scroll to the bottom
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(scroll_pause)
