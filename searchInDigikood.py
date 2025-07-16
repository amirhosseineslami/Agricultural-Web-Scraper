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
TIMEOUT = 4500000

class SearchInDigikood:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://digikood.com/"
        

    async def run(self):
        try:
            await self.page.goto(self.url, timeout=TIMEOUT)
            # Adjust the selector based on the site's search input

            
            await asyncio.sleep(60)  # keeps the browser open for 60 seconds


        except Exception as e:
            print(f"Error searching Digikood: {e}")

    async def getListOfFertilizerCategories(self) -> list[dict]:
        list_url = "https://Digikood.com/"

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

    async def extract_products_from_specific_fertilizer_category_page(self,url:str,category:str) -> list[dict]:

        await self.page.goto(url,timeout=TIMEOUT)
        print("here we're in the specific fertilizer category page")
        await self.page.goto(url,timeout=TIMEOUT)

        # Assumes you're already on a fertilizer page like: https://www.digikood.com/product-category/%DA%A9%D9%88%D8%AF-%D9%87%D8%A7%DB%8C-%DA%AF%D9%88%DA%AF%D8%B1%D8%AF%DB%8C/?per_page=3000
        product_blocks = await self.page.query_selector_all("div.product-element-bottom")

        products = []

        for block in product_blocks:
            try:
                # Get the <a> with class "product-name"
                name_el = await block.query_selector("h3.wd-entities-title")
                name = await name_el.inner_text()
                href = await (await name_el.query_selector("a")).get_attribute("href")

                # Get the price
                price_el = await block.query_selector("span.woocommerce-Price-amount")
                price = await price_el.inner_text() if price_el else "N/A"

                products.append({
                    "name": name.strip(),
                    "price": price.strip(),
                    "url": href,
                    "category":category
                })
                print(f"""
name: {name.strip()}
price: {price.strip()}
url: {href}
category: {category}
                      """)
            except Exception as e:
                print(f"⚠️ Skipping a product due to error: {traceback}")

        

        return products


    async def get_price_per_kg(self,productUrl,category,product_name) -> dict[str,float|str] | None:
        try:
            await self.page.goto(productUrl,timeout=TIMEOUT)

            # product_name = await self.page.query_selector("div.pb-center-column.col-xs-12.col-sm-12.col-md-7.col-lg-6")
            # # Now query the h1 within that container
            # h1_element = await product_name.query_selector('h1[itemprop="name"]')
            # if h1_element:
            #     name_text = await h1_element.inner_text()
            #     print(f"Product Name: {name_text.strip()}")
            # else:
            #     print("❌ h1 tag not found inside the container")


            # Select <p class="unit-price"> which includes both price and weight
            priceClass = self.page.locator("p.price")
            unit_price_paragraph = priceClass.locator("span.woocommerce-Price-amount bdi").first
            if not unit_price_paragraph:
                print("⚠️ No unit-price block found.")
                price = 0
            

            full_text = await(unit_price_paragraph).inner_text()
            digits_only = re.sub(r"[^\d]", "", full_text)   # → "1775000"
            price = int(digits_only)

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

            # Final calculation
            if (kg > 0) : price_per_kg = price / kg

            # If Price wasn't logical

            if(price <= 0):
                price = "nan"
                price_per_kg = "nan"

            print(f"""
    name: {product_name}
    total price: {price}
    price/kg: {price_per_kg}
url: {productUrl}
    """)
            return {
                "name":product_name,
                "price":price,
                "price_per_kg":price_per_kg,
                    "category":category,
                    "url":productUrl}

        except Exception as e:
            print(f"❌ Error parsing price per kg: {traceback.format_exc()}")
            return None

    async def get_all_prices(self):
        book = PriceBook()
        finalList = []

        listOfSorts = await self.getListOfFertilizerCategories()
        for sort in listOfSorts:
            rawProducts = await self.extract_products_from_specific_fertilizer_category_page(sort["url"],sort["category"])

            for rawProduct in rawProducts:
                fullData = await self.get_price_per_kg(rawProduct["url"],rawProduct["category"],rawProduct["name"])
                finalList.append(fullData)
                try:
                    book.upsert(fullData)
                except Exception as e:
                    print(traceback.format_exc())

        return finalList