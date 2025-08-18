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
import pandas as pd

TIMEOUT = 4500000
TIMEOUT_FOR_FINDING_NEXTPAGE_KEY = 155000
TIMOUT_FOR_PAGE_MENU_LOAD = 10_000

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
book = PriceBook()

# Regex-friendly keys including fuzzy/combined ones
UNIT_PATTERN = "|".join(
    sorted([re.escape(k) for k in UNIT_KEYWORDS], key=len, reverse=True)
)
# Persian/Arabic digits to Latin
PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٫", "0123456789.")


class SearchInDigikala:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://Digikala.com/"

    async def run(self):
        try:
            await self.page.goto(self.url, timeout=TIMEOUT)
            # Adjust the selector based on the site's search input

            await asyncio.sleep(60)  # keeps the browser open for 60 seconds

        except Exception as e:
            print(f"Error searching Sepahankesht: {e}")

    async def getListOfFertilizerCategories(self) -> list[dict]:
        list_url = "https://digikala.com/"

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
                "https://www.digikala.com/search/category-soils-and-fertilizers/?page=1"
            )

        elif (product_dic["url"]) == None:
            product_dic["url"] = (
                "https://www.digikala.com/search/category-soils-and-fertilizers/?page=1"
            )

        # Search in subsequential
        book = PriceBook()
        await self.page.goto(product_dic["url"], timeout=TIMEOUT)
        product_dic["product_menu_url"] = product_dic["url"]

        print("here we're in the specific fertilizer category page")

        while True:
            # If this page already is exist in the progress file so go to the next page
            if await book.isThisBlocksPageCheckedBefore(product_dic, False):
                print("This page is checked before!")

                new_page_link = await self.got_to_the_next_page(
                    product_dic["product_menu_url"]
                )

                if new_page_link == None:
                    print("Finished all the pages!")
                    return
                else:
                    # It went to the next page
                    product_dic["product_menu_url"] = new_page_link
                    continue

            product_blocks = await self.page.locator(
                "div.product-list_ProductList__item__LiiNI"
            ).first.wait_for(state="visible", timeout=TIMOUT_FOR_PAGE_MENU_LOAD)

            # Assumes you're already on a fertilizer page
            product_blocks = await self.page.locator(
                "div.product-list_ProductList__item__LiiNI"
            ).all()

            products = []

            for block in product_blocks:
                try:
                    # Get the <a> with class "product-name"
                    # name_el = block.locator("h3.wd-entities-title")
                    print(f"block{product_blocks.index(block)}")

                    product_name = await block.locator(
                        "h3.ellipsis-2.text-body2-strong.text-neutral-700.styles_VerticalProductCard__productTitle__6zjjN"
                    ).inner_text()
                    product_dic["name"] = product_name

                    href_locator = block.locator("a").first

                    # Extract href
                    href = "https://digikala.com" + await href_locator.get_attribute(
                        "href"
                    )
                    product_dic["url"] = href
                    print(product_name, href)

                    # Get the price
                    # Get the price element from the block
                    pure_price_int = None
                    flex_div = block.locator(
                        "div.pt-1.flex.flex-col.items-stretch.justify-between"
                    )
                    price_div = flex_div.locator(
                        "div.flex.items-center.justify-end.gap-1.text-neutral-700.text-neutral-400.text-h5.grow"
                    )

                    try:

                        product_price = await price_div.locator(
                            "span[data-testid='price-final']"
                        ).inner_text()
                        product_price = product_price.replace(",", "")

                        digits_only = re.sub(r"[^\d]", "", product_price)  # → "1775000"
                        pure_price_int = int(digits_only)
                    except Exception as e:
                        traceback.print_exc()
                    product_dic["is_available"] = True
                    product_dic["price"] = pure_price_int

                    # 1) get the visible text
                    kg, unit = await UnitExtractor().extract_amount_and_unit(
                        product_name
                    )
                    if kg is not None and int(kg) > 0:
                        product_dic["amount_kg"] = kg
                        product_dic["price_per_kg"] = pure_price_int / int(kg)
                    else:
                        product_dic["price_per_kg"] = "nan"
                        product_dic["amount_kg"] = "nan"
                        kg = None

                    products.append(product_dic)
                    book.upsert(product_dic)

                    # Save the progress of this page in the
                    book.log_progress(product_dic, False)

                    print(
                        f"""
                        name: {product_name.strip()}
                        price: {pure_price_int}
                        url: {href}
                        category: {product_dic["category"]}
                        kg: {product_dic["amount_kg"]}
                        price/kg: {product_dic["price_per_kg"]}
                        """
                    )
                except Exception as e:
                    print(
                        f"⚠️ Skipping a product due to error: {traceback.format_exc()}"
                    )

            product_dic["product_menu_url"] = await self.got_to_the_next_page(
                product_dic["product_menu_url"]
            )
            print("Going to the next page!")

            if product_dic["product_menu_url"] == None:
                print("No page is remaind")
                # No page is remaind
                break

        return products

    async def get_price_per_kg(
        self, product_dic: dict
    ) -> dict[str, float | str] | None:
        is_product_available = True

        try:
            await self.page.goto(product_dic["url"], timeout=TIMEOUT)

            if product_dic["price"]:
                full_text_price = product_dic["price"]

            digits_only = re.sub(r"[^\d]", "", str(full_text_price))
            price = int(digits_only)

            # Get amount of KG
            kg = None
            unit_kg_text = None

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
                    product_dic["price_per_kg"] = int(product_dic["price"]) / amount_kg
                    print(amount_kg)

            # try:
            #     unit_kg_text = await unit_kg_locator.inner_text()  # now it's a str
            #     kg, unit = await UnitExtractor().extract_amount_and_unit(unit_kg_text)
            # except Exception as e:
            #     print(traceback.format_exc())

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
            product_dic["price_per_kg"] = price_per_kg
            product_dic["price"] = price
            product_dic["amount_kg"] = kg
            product_dic["is_available"] = is_product_available
            book.log_progress(product_dic, True)
            return product_dic

        except Exception as e:
            print(f"❌ Error parsing price per kg: {traceback.format_exc()}")
            return product_dic

    async def get_all_prices(self):
        finalList = []
        rawProducts = (
            await self.extract_products_from_specific_fertilizer_category_page(
                {"category": "nan"}
            )
        )
        logdf = pd.DataFrame({})
        logdf = book.get_log_progress(
            product_dic={"url": "https://www.digikala.com/"},
            isLoggingInPerKg=False,
        )

        for idx, row in logdf.iterrows():
            rawProduct = row.to_dict()

            if rawProduct[
                "price_per_kg"
            ] > 0 or await book.isThisBlocksPageCheckedBefore(rawProduct, True):
                # If the perkg price exists skip
                print(
                    "skipping.",
                    rawProduct["price_per_kg"] > 0,
                    await book.isThisBlocksPageCheckedBefore(rawProduct, True),
                )
                continue

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

    async def got_to_the_next_page(self, current_link):

        # go to the next page if is exist
        next_page_locator = self.page.locator(
            "span.ml-2.text-body2-strong.hidden.md\\:inline-block"
        ).last

        next_page_link = None
        if await next_page_locator.inner_text() != "بعدی":
            return None
        try:
            next_page_number = int((current_link.split("="))[-1]) + 1
            next_page_link = (
                "https://www.digikala.com/search/category-soils-and-fertilizers/?page="
                + str(next_page_number)
            )
        except Exception as e:
            print(f"No next page found!{traceback.format_exc()}")

        if next_page_link is not None:
            print(next_page_link)
            await self.page.goto(next_page_link, timeout=TIMEOUT)
            return next_page_link

        else:
            return None
