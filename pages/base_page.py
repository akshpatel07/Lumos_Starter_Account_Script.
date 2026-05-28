# ─────────────────────────────────────────────────────────────
#  pages/base_page.py  —  Shared browser utilities
# ─────────────────────────────────────────────────────────────

import base64
from playwright.async_api import Page, TimeoutError as PWTimeout
from config.settings import DEFAULT_TIMEOUT


class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.page.set_default_timeout(DEFAULT_TIMEOUT)

    # ── Waits ─────────────────────────────────────────────────

    async def wait_for_network(self, timeout: int = 8_000):
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
        except PWTimeout:
            pass

    async def wait_for_element(self, xpath: str, timeout: int = DEFAULT_TIMEOUT):
        await self.page.locator(xpath).wait_for(state="visible", timeout=timeout)

    # ── Screenshot ────────────────────────────────────────────

    async def screenshot_element_b64(self, xpath: str) -> str | None:
        """Screenshot a specific element and return as base64 PNG."""
        try:
            el = self.page.locator(xpath).first
            img = await el.screenshot(type="png")
            return base64.b64encode(img).decode()
        except Exception:
            return await self.screenshot_page_b64()

    async def screenshot_page_b64(self) -> str | None:
        """Screenshot the full visible viewport as base64 PNG."""
        try:
            img = await self.page.screenshot(type="png", full_page=False)
            return base64.b64encode(img).decode()
        except Exception:
            return None

    async def screenshot_page_bytes(self) -> bytes | None:
        """Screenshot the full visible viewport as raw bytes."""
        try:
            return await self.page.screenshot(type="png", full_page=False)
        except Exception:
            return None

    # ── Safe click ────────────────────────────────────────────

    async def safe_click(self, xpath: str, timeout: int = 5_000) -> bool:
        """Click element if visible. Returns True if clicked."""
        try:
            el = self.page.locator(xpath).first
            await el.wait_for(state="visible", timeout=timeout)
            await el.click()
            return True
        except PWTimeout:
            return False

    # ── Safe get text ─────────────────────────────────────────

    async def get_text(self, xpath: str) -> str:
        try:
            return (await self.page.locator(xpath).first.inner_text()).strip()
        except Exception:
            return ""

    # ── Current URL ───────────────────────────────────────────

    def current_url(self) -> str:
        return self.page.url
