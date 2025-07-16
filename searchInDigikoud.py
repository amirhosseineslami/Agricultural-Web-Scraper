from playwright.async_api import Page
import asyncio, re
TIMEOUT = 3000_000
from priceBook import PriceBook
import traceback

class SearchInDigikoud:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://digikoud.com/"
        

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
            print(f"Error searching Digikoud: {e}")

    async def getListOfFertilizerCategories(self) -> list[dict]:
        list_url = "https://digikoud.com/12-%DA%A9%D9%88%D8%AF-%D9%87%D8%A7%DB%8C-%D8%B4%DB%8C%D9%85%DB%8C%D8%A7%DB%8C%DB%8C"

        await self.page.goto(list_url, timeout=60000)

        selector = ".list-block.list-group.bullet.tree.dynamized a"
        categories = await self.page.query_selector_all(selector)

        result = []

        for link in categories:
            name = await link.inner_text()
            url = await link.get_attribute("href")

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
                "url": url + "?n=45"
            })
            
            print(f"""
                  category:{name.strip()}
                  Url:{url}
                  Count:{count}
""")

        return result

    async def extract_products_from_specific_fertilizer_page(self,url:str,category:str) -> list[dict]:

        await self.page.goto(url,timeout=TIMEOUT)
        print("here we're in the specific fertilizer page")

        # Assumes you're already on a fertilizer page like: https://digikoud.com/21-کود-های-مرکب
        product_blocks = await self.page.query_selector_all(".product-meta")

        products = []

        for block in product_blocks:
            try:
                # Get the <a> with class "product-name"
                name_el = await block.query_selector("a.product-name")
                name = await name_el.inner_text()
                href = await name_el.get_attribute("href")

                # Get the price
                price_el = await block.query_selector(".price.product-price")
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
                print(f"⚠️ Skipping a product due to error: {e}")

        

        return products


    async def get_price_per_kg(self,productUrl,category) -> dict[str,float|str] | None:
        try:
            await self.page.goto(productUrl,timeout=TIMEOUT)

            product_name = await self.page.query_selector("div.pb-center-column.col-xs-12.col-sm-12.col-md-7.col-lg-6")
            # Now query the h1 within that container
            h1_element = await product_name.query_selector('h1[itemprop="name"]')
            if h1_element:
                name_text = await h1_element.inner_text()
                print(f"Product Name: {name_text.strip()}")
            else:
                print("❌ h1 tag not found inside the container")


            # Select <p class="unit-price"> which includes both price and weight
            unit_price_paragraph = await self.page.query_selector("p.unit-price")
            if not unit_price_paragraph:
                print("⚠️ No unit-price block found.")
                

            full_text = await unit_price_paragraph.inner_text()

            # Extract price: something like "3,399,000 ریال"
            price_match = re.search(r"([\d,]+)\s*ریال", full_text)
            if not price_match:
                print("⚠️ Could not find price.")
                
            price_text = price_match.group(1).replace(",", "")
            price = int(price_text)

            # Extract weight: something like "25 کیلو" or "50 کیلوگرمی"
            weight_match = re.search(r"(\d+)\s*کیلو", full_text)
            if not weight_match:
                print("⚠️ Could not find weight in KG.")
                # Extract weight: something like "0.5 لیتری"
                weight_match = re.search(r"(\d+)\s*لیتر", full_text)
                if not weight_match:
                    print("⚠️ Could not find weight in liter too.")
                    
                kg = int(weight_match.group(1))
            kg = int(weight_match.group(1))



            # Final calculation
            price_per_kg = price / kg
            print(f"""
    name: {name_text}
    total price: {price}
    price/kg: {price_per_kg}
url: {productUrl}
    """)
            return {
                "name":name_text,
                "price":price,
                "price_per_kg":price_per_kg,
                    "category":category,
                    "url":productUrl}

        except Exception as e:
            print(f"❌ Error parsing price per kg: {e}")
            print(f"""
    name: {name_text}
url: {productUrl}
    """)
            
            return {
    "name":name_text,
    "price":"nan",
    "price_per_kg":"nan",
        "category":category,
        "url":productUrl}

    async def get_all_prices(self):
        finalList = []
        book = PriceBook()


        listOfSorts = await self.getListOfFertilizerCategories()
        for sort in listOfSorts:
            rawProducts = await self.extract_products_from_specific_fertilizer_page(sort["url"],sort["category"])

            for rawProduct in rawProducts:
                fullData = await self.get_price_per_kg(rawProduct["url"],rawProduct["category"])
                finalList.append(fullData)
                try:
                    book.upsert(fullData)
                except Exception as e:
                    print(traceback.format_exc())

        return finalList