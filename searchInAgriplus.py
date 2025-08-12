from playwright.async_api import Page
import asyncio, re, traceback
from playwright.async_api import Page
import asyncio, re
from typing import List, Dict, Optional, Tuple, Union
import re
from typing import List, Dict
import traceback
from priceBook import PriceBook
from persianNumberNormalizer import PersianNumberNormalizer

PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
TIMEOUT = 4500000


class SearchInAgriplus:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://agriplus.ir/"

    async def run(self):
        try:
            await self.page.goto(self.url, timeout=TIMEOUT)
            # Adjust the selector based on the site's search input

            await asyncio.sleep(60)  # keeps the browser open for 60 seconds

        except Exception as e:
            print(f"Error searching agriplus: {e}")

    async def getListOfFertilizerCategories(self) -> list[dict]:
        list_url = "https://agriplus.ir/"

        await self.page.goto(list_url, timeout=TIMEOUT)

        firstLocator = self.page.locator(
            "li.menu-item.menu-item-type-taxonomy.menu-item-object-product_cat.menu-item-has-children.menu-item-30720.menu-item-design-default.has-dropdown"
        )

        selector = "ul.sub-menu.nav-dropdown.nav-dropdown-simple li"

        categories = firstLocator.locator(selector)

        categories_counts = await categories.count()

        print(categories_counts)

        result = []

        allcat = await categories.all()

        for link in allcat:
            link_locator = link.locator("a")
            name = await link_locator.inner_text()
            print(name)
            url = await link_locator.get_attribute("href")

            result.append(
                {
                    "category": name.strip(),
                    "url": url + "?per_page=400/",
                }
            )

            print(
                f"""
                  category:{name.strip()}
                  Url:{url}?per_page=400/
"""
            )

        return result

    async def extract_products_from_specific_fertilizer_category_page(
        self, product_dic
    ) -> list[dict]:

        await self.page.goto(product_dic["url"], timeout=TIMEOUT)
        await self.auto_scroll_to_bottom(scroll_pause=5000)
        print("here we're in the specific fertilizer category page")

        # Assumes you're already on a fertilizer page
        product_blocks = await self.page.locator("div.product-small.box").all()

        products = []

        for block in product_blocks:
            try:
                # Get the <a> with class "product-name"
                name_el = block.locator("h2.title-wrapper")
                name = await name_el.inner_text()
                href = await name_el.locator("a").get_attribute("href")

                # Get the price
                # Get the price element from the block
                price_el = block.locator("span.woocommerce-Price-amount.amount >> bdi")

                # Check if it exists
                if await price_el.count() > 0:
                    price = PersianNumberNormalizer().convert_numbers(
                        await price_el.first.inner_text()
                    )
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
                print(f"⚠️ Skipping a product due to error: {traceback.format_exc()}")

        return products

    async def get_price_per_kg(self, product_dic) -> dict[str, float | str] | None:
        is_product_available = True
        try:
            await self.page.goto(product_dic["url"], timeout=TIMEOUT)

            # Find the locator for the span inside the 'out of stock' paragraph
            out_of_stock_span = self.page.locator(
                "p.price.product-page-price.price-not-in-stock"
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
                return product_dic

            full_text_price = product_dic["price"]
            digits_only = re.sub(r"[^\d]", "", full_text_price)  # → "1775000"
            price = int(digits_only) / 10

            unit_kg_locator = self.page.locator("span.ux-swatch__text").first
            print(unit_kg_locator)

            # 1) get the visible text
            if unit_kg_locator is not None:
                unit_kg_text = await unit_kg_locator.inner_text()  # now it's a str
            else:
                return product_dic
            # 2) normalise Persian/Arabic digits → Latin digits
            unit_kg_text = unit_kg_text.translate(PERSIAN_TO_LATIN)

            # raw_price sample: "قیمت : ۹۹,۰۰۰ تومان"
            # 1) keep only the first group of digits with comma separators
            m = re.search(r"([\d,]+)", unit_kg_text.translate(PERSIAN_TO_LATIN))
            kg = int(m.group(1).replace(",", "")) if m else None

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
