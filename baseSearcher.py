from abc import ABC, abstractmethod
from playwright.async_api import Page

class BaseSearcher(ABC):
    def __init__(self, page: Page, url: str):
        self.page = page
        self.url = url

    async def go_to_site(self):
        await self.page.goto(self.url, timeout=30000)

    async def take_screenshot(self, filename: str):
        await self.page.screenshot(path=filename)

    async def try_common_search_boxes(self, query: str) -> bool:
        selectors = ['input[name="q"]', 'input[type="search"]']
        for sel in selectors:
            try:
                box = await self.page.wait_for_selector(sel, timeout=3000)
                await box.fill(query)
                await box.press("Enter")
                return True
            except:
                continue
        return False

    @abstractmethod
    async def run(self, query: str):
        pass
