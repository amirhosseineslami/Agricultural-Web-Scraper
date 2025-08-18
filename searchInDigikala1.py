from playwright.async_api import Page
import asyncio, re, traceback
from playwright.async_api import Page
import asyncio, re
from typing import List, Dict, Optional, Tuple, Union
import re, random
from typing import List, Dict
import traceback
from priceBook import PriceBook
from unitExtractor import UnitExtractor

import re

PERSIAN_TO_ENGLISH = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

# Persian decimal separator
PERSIAN_DECIMAL = "٫"

# Example pattern: match numbers (integer or decimal) followed by optional space and unit
pattern = re.compile(r"([\d\.]+)\s*(\w+)", re.UNICODE)

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


class SearchInDigikala:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://digikala.com/"

    async def run(self):
        try:
            await self.page.goto(self.url, timeout=TIMEOUT)
            # Adjust the selector based on the site's search input

            await asyncio.sleep(60)  # keeps the browser open for 60 seconds

        except Exception as e:
            print(f"Error searching digikala: {e}")

    async def getListOfFertilizerCategories(self) -> list[dict]:
        list_url = "https://digikala.com/"

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
        url: str = "https://www.digikala.com/search/category-soils-and-fertilizers/",
        category: str | None = "nan",
    ) -> list[dict]:

        await self.page.goto(url, timeout=TIMEOUT)
        print("here we're in the specific fertilizer category page")

        await self.aggressive_human_scroll()
        print("Now we're totaly in the bottom of the website!")

        product_blocks = await self.page.locator(
            "div.product-list_ProductList__item__LiiNI"
        ).all()

        products = []

        book = PriceBook()

        for block in product_blocks:
            try:
                href_locator = block.locator("a").first

                # Extract href
                href = "https://digikala.com" + await href_locator.get_attribute("href")
                print(href)

                product_name = await block.locator(
                    "h3.ellipsis-2.text-body2-strong.text-neutral-700.styles_VerticalProductCard__productTitle__6zjjN"
                ).inner_text()
                print(product_name)

                # filter just fertilizers
                if product_name in BLACK_LIST_PRODUCTS:
                    continue

                amount_kg = 0
                # get kg from name of the product
                amount_kg_list: list = await self.extract_amount(product_name)
                if len(amount_kg_list) > 0:
                    amount_kg = int(amount_kg_list[0][0])

                flex_div = block.locator(
                    "div.pt-1.flex.flex-col.items-stretch.justify-between"
                )
                price_div = flex_div.locator(
                    "div.flex.items-center.justify-end.gap-1.text-neutral-700.text-neutral-400.text-h5.grow"
                )

                product_price = await price_div.locator(
                    "span[data-testid='price-final']"
                ).inner_text()
                print(product_price)

                digits_only = re.sub(r"[^\d]", "", product_price)  # → "1775000"
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
            unit_kg_locator = self.page.locator(
                "p.flex.items-center.w-full.text-body-1.text-neutral-900.break-words"
            )

            try:
                await unit_kg_locator.first.wait_for(state="visible", timeout=3000)
            except TimeoutError:
                print("Unit per kg not found")

            for unit_kg_locator in await unit_kg_locator.all():
                amount_kg_str = await unit_kg_locator.inner_text()
                print(amount_kg_str)

                amount_kg = 0
                # get kg from name of the product
                amount_kg_list: list = await self.extract_amount(amount_kg_str)
                if len(amount_kg_list) > 0:
                    amount_kg = int(amount_kg_list[0][0])

                if amount_kg > 0:
                    product_dict["price_per_kg"] = (
                        int(product_dict["price"]) / amount_kg
                    )
                    print(amount_kg)
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

    async def aggressive_human_scroll(
        self,
        max_scrolls: int = 300000,
        base_increment: float = 0.2,  # starting fraction of viewport
        scroll_pause_min: int = 1000,
        scroll_pause_max: int = 2000,
        max_increment: float = 1.5,  # cap the maximum fraction
    ):
        """
        Human-like scroll that becomes more aggressive over time.
        """
        print("🔽 Starting aggressive human-like scrolling...")

        prev_count = 0
        same_count_tries = 0
        scrolls_done = 0

        while scrolls_done < max_scrolls:
            product_cards = await self.page.locator(
                "div.product-list_ProductList__item__LiiNI"
            ).all()
            current_count = len(product_cards)
            print(f"📦 Product count: {current_count}")

            # Stop if no new products loaded
            if current_count == prev_count:
                same_count_tries += 1
                if same_count_tries >= 900:
                    print("✅ No new products loaded. Stopping scroll.")
                    break
            else:
                same_count_tries = 0

            prev_count = current_count

            # Dynamically increase scroll increment based on scrolls done
            increment = min(base_increment * (1 + scrolls_done * 0.2), max_increment)
            increment *= random.uniform(0.85, 1.05)  # add slight randomness
            await self.page.evaluate(
                f"window.scrollBy(0, window.innerHeight * {increment})"
            )
            scrolls_done += 1

            # Randomized human-like pause
            pause_time = random.randint(scroll_pause_min, scroll_pause_max)
            await asyncio.sleep(pause_time / 1000)

        print(
            f"✅ Finished scrolling. Total scrolls: {scrolls_done}, Total products: {prev_count}"
        )

    async def extract_amount(self, text: str) -> list[tuple[str, str]]:
        matches = pattern.findall(text)
        result = []

        for number, unit in matches:
            # Convert Persian to English digits
            normalized_number = number.translate(PERSIAN_TO_ENGLISH)
            result.append((normalized_number, unit))

        return result
