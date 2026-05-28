# ─────────────────────────────────────────────────────────────
#  pages/nav_page.py  —  Login, popup, notifications, logout,
#                         results scraper
# ─────────────────────────────────────────────────────────────

from playwright.async_api import Page, TimeoutError as PWTimeout
from pages.base_page import BasePage
from config.settings import SITE_URL, XPATHS
import asyncio


class NavPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    async def open(self):
        """Navigate to the StepUp starter page."""
        print("[*] Opening StepUp page ...")
        await asyncio.sleep(3)
        await self.page.goto(SITE_URL, timeout=40_000)
        await self.page.wait_for_load_state("domcontentloaded")
        print("[*] Page loaded.")

    async def close_popup_if_present(self):
        """Dismiss the welcome / cookie popup if it appears."""
        clicked = await self.safe_click(XPATHS["close_popup"], timeout=4_000)
        if clicked:
            print("[*] Popup dismissed.")

    async def go_to_notifications(self):
        """Click the notifications bell/link to reach the test list."""
        print("[*] Navigating to notifications ...")
        await self.page.locator(XPATHS["notification_link"]).click()
        await self.wait_for_network()

    async def start_unit1_test(self):
        """Click the Start button on Unit 1 row."""
        print("[*] Starting Unit 1 test ...")
        await self.page.locator(XPATHS["unit1_start_btn"]).first.click()
        await self.wait_for_network()

    async def logout(self):
        """Log out of the session."""
        clicked = await self.safe_click(XPATHS["logout_link"], timeout=5_000)
        if clicked:
            print("[OK] Logged out.")
        else:
            print("[!] Logout link not found.")

    async def scrape_results(self) -> dict:
        """
        Wait for the full-report results page and extract:
          SCORE      e.g. '4/13'
          PERCENTAGE e.g. '30.77%'
          QUESTIONS  e.g. '13'

        DOM structure (from live inspector):
          <div class="score-container">
            <div class="totalScoreBlock ...">
              <div ...>
                <h5 class="title-score">SCORE</h5>
                <h5 style="font-weight:700;">&nbsp;4/13</h5>
              </div>
              <div ...>
                <h5 class="title-score">PERCENTAGE</h5>
                <h5 style="font-weight:700;">30.77%</h5>
              </div>
            </div>
          </div>

        Returns dict with keys 'score', 'percentage', 'questions'.
        All values are 'N/A' if extraction fails.
        """
        print("[*] Waiting for results page ...")

        # Wait for fullreport.php to load (up to 20 s)
        try:
            await self.page.wait_for_url("**/fullreport.php**", timeout=20_000)
            print("[*] Results page loaded (fullreport.php).")
        except PWTimeout:
            print("[!] fullreport.php URL not detected — checking current page anyway.")

        # Wait for the score container to appear
        try:
            await self.page.locator(".score-container").wait_for(
                state="visible", timeout=12_000
            )
        except PWTimeout:
            print("[!] .score-container not visible — score extraction failed.")
            return {"score": "N/A", "percentage": "N/A", "questions": "N/A"}

        result = {}
        for label in ["SCORE", "PERCENTAGE", "QUESTIONS"]:
            try:
                # Locate h5 that immediately follows the title h5 with this label
                xpath = (
                    f"//h5[contains(@class,'title-score') and "
                    f"normalize-space()='{label}']/following-sibling::h5[1]"
                )
                text = await self.page.locator(f"xpath={xpath}").first.inner_text()
                # &nbsp; arrives as \xa0 — strip it out
                clean = text.replace("\xa0", "").strip()
                result[label.lower()] = clean
                print(f"  [Results] {label}: {clean}")
            except Exception as e:
                print(f"  [Results] Could not read {label}: {e}")
                result[label.lower()] = "N/A"

        return result
