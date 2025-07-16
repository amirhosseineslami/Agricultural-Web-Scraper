from playwright.async_api import Page
import asyncio, re, traceback
from playwright.async_api import Page
import asyncio, re
from typing import List, Dict, Optional, Tuple, Union
import re
from typing import List, Dict
import traceback
from priceBook import PriceBook

PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
BLACK_LIST_PRODUCTS = [
    ""
]
TIMEOUT = 4500000

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
            name = await (await link.query_selector("h3.wd-entities-title")).inner_text()
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

            result.append({
                "category": name.strip(),
                "count": count,
                "url": url+"?per_page=400/"
            })
            
            print(f"""
                  category:{name.strip()}
                  Url:{url}?per_page=400/
                  Count:{count}
""")

        return result

    async def extract_products_from_specific_fertilizer_category_page(self,url:str="https://torob.com/browse/440/%D8%AE%D8%A7%DA%A9-%DA%A9%D9%88%D8%AF-%D9%88-%D8%B3%D9%85%D9%88%D9%85-fertilizer/"
                                                                      ,category:str|None = "nan") -> list[dict]:

        await self.page.goto(url,timeout=TIMEOUT)
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

                product_name =await block.locator("h2.ProductCard_desktop_product-name__JwqeK").inner_text()

                # filter just fertilizers
                if product_name in BLACK_LIST_PRODUCTS:
                    continue

                product_price = await block.locator("div.ProductCard_desktop_product-price-text__y20OV").inner_text()

                digits_only = re.sub(r"[^\d]", "", product_price)   # → "1775000"
                price = int(digits_only)

                is_available = False
                if price > 0: is_available = True
                


                # # Get the <a> with class "product-name"
                # name_el = await block.query_selector("h2.ProductCard_desktop_product-name__JwqeK")
                # name = await name_el.inner_text()
                # href = await (await name_el.query_selector("a")).get_attribute("href")

                # # Get the price
                # price_el = await block.query_selector("span.woocommerce-Price-amount")
                # price = await price_el.inner_text() if price_el else "N/A"


                product_detail_dictionary = {
                    "name": product_name,
                    "price": product_price,
                    "url": href,
                    "category":category,
                    "is_available": is_available,
                    "amount_kg":"nan",
                    "price_per_kg":"nan"
                }
                products.append(product_detail_dictionary)

                # save to excel directly
                book.upsert(product_detail_dictionary)
                print(product_detail_dictionary)

                
            except Exception as e:
                print(f"⚠️ Skipping a product due to error: {traceback.format_exc()}")

        

        return products


    async def get_price_per_kg(self,productUrl,product_price,product_name) -> dict[str,float|str] | None:
        is_product_available = True
        try:
            await self.page.goto(productUrl,timeout=TIMEOUT)


            unit_kg_locator = await self.page.query_selector("td.woocommerce-product-attributes-item__value")


            print(unit_kg_locator)

            # 1) get the visible text
            unit_kg_text = await unit_kg_locator.inner_text()            # now it's a str

            # 2) normalise Persian/Arabic digits → Latin digits
            unit_kg_text = unit_kg_text.translate(PERSIAN_TO_LATIN)

            # raw_price sample: "قیمت : ۹۹,۰۰۰ تومان"
            # 1) keep only the first group of digits with comma separators
            m = re.search(r"([\d,]+)", unit_kg_text.translate(PERSIAN_TO_LATIN))
            kg = int(m.group(1).replace(",", "")) if m else None

            price_per_kg = 0

            # Final calculation
            if (kg > 0) : price_per_kg = product_price / kg
            else: price_per_kg = "nan"

            # If Price wasn't logical

            if(product_price <= 0):
                product_price = "nan"
                price_per_kg = "nan"

            print(f"""
    name: {product_name}
    price: {product_price}
    price_per_kg: {price_per_kg}
url: {productUrl}
amount_kg:{kg},
"is_available":{is_product_available}
    """)
            return {
                "name":product_name,
                "price":product_price,
                "price_per_kg":price_per_kg,
                    "category":"nan",
                    "url":productUrl,
                    "amount_kg":kg,
                    "is_available":is_product_available
                    }

        except Exception as e:
            print(f"❌ Error parsing price per kg: {traceback.format_exc()}")
            return None


    async def get_all_prices(self):
        return await self.extract_products_from_specific_fertilizer_category_page()
    
        
    async def auto_scroll_to_bottom(self, wait_time: int = 2000, scroll_pause: int = 1000):
        print("🔽 Starting auto-scroll...")
        
        prev_count = 0
        same_count_tries = 0

        while True:
            # Count the number of product cards
            product_cards = await self.page.locator("div.ProductCards_cards__MYvdn a").all()
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
