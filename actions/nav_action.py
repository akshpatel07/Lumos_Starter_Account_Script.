# ─────────────────────────────────────────────────────────────
#  actions/nav_action.py  —  Next button, End Test, Show Results
# ─────────────────────────────────────────────────────────────

import asyncio
from playwright.async_api import Page, TimeoutError as PWTimeout
from config.settings import XPATHS


class NavAction:
    def __init__(self, page: Page):
        self.page = page

    # ── Click Next ────────────────────────────────────────────

    async def click_next(self):
        """
        Click the #nexturl Next button, then dismiss any modal
        ('Yes' / 'Ok' / 'Next Question') that may appear when
        moving too quickly between questions.
        """
        # Primary: click #nexturl directly
        try:
            btn = self.page.locator("#nexturl")
            await btn.wait_for(state="visible", timeout=6_000)
            await btn.scroll_into_view_if_needed()
            await btn.click()
            print("  [Nav] Clicked Next (#nexturl)")
        except PWTimeout:
            # Fallback: direct querySelector via JS
            print("  [Nav] #nexturl not found via locator — trying JS ...")
            clicked = await self.page.evaluate(
                "() => { const b = document.querySelector('#nexturl'); if(b){b.click();return true;} return false; }"
            )
            if not clicked:
                print("  [Nav] JS also failed — pressing ArrowRight ...")
                await self.page.keyboard.press("ArrowRight")

        # Give any modal time to appear, then dismiss it
        await asyncio.sleep(1.5)
        await self._handle_post_next_modal()

        # Wait for page to settle
        try:
            await self.page.wait_for_load_state("networkidle", timeout=8_000)
        except PWTimeout:
            pass
        await asyncio.sleep(0.5)

    # ── Modal handler (called after clicking Next) ────────────

    async def _handle_post_next_modal(self) -> bool:
        """
        Dismiss any dialog that appears after clicking Next:
          • 'Yes'           — skip question confirmation
          • 'Next Question' — 'Take a Moment to Think' nudge
          • 'Ok' / 'Okay'  — generic alert
        Returns True if a modal was dismissed.
        """
        candidates = [
            ("//button[normalize-space()='Yes']",           "Skip -> Yes"),
            ("//button[normalize-space()='Next Question']", "Think -> Next Question"),
            ("//button[normalize-space()='Ok']",            "Alert -> Ok"),
            ("//button[normalize-space()='Okay']",          "Alert -> Okay"),
        ]
        for xpath, desc in candidates:
            try:
                btn = self.page.locator(f"xpath={xpath}").first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    print(f"    [Modal] Dismissed: {desc}")
                    await asyncio.sleep(0.8)
                    return True
            except Exception:
                continue
        return False

    # ── End test flow ─────────────────────────────────────────

    async def finish_test(self):
        """
        Full end-of-test sequence (matches Playwright recording):
          1. Click 'Result' link  OR  #exit End Test button
          2. If 'Review Unanswered' dialog appears → click Show Results directly
          3. Click 'Show Results' (#endTestConfirm) button
        """
        print("\n[*] Finishing test ...")

        # ── Step 1: Trigger end-test ───────────────────────────
        triggered = False
        for selector, desc in [
            ("a:has-text('Result')",        "Result link"),
            ("#exit",                        "End Test (#exit)"),
            ("xpath=//*[@id='exit']",        "End Test (XPath)"),
            ("button:has-text('End Test')",  "End Test button"),
        ]:
            try:
                el = self.page.locator(selector).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    print(f"  [*] Clicked: {desc}")
                    await asyncio.sleep(1.5)
                    triggered = True
                    break
            except Exception:
                continue

        if not triggered:
            print("  [!] Could not find End Test trigger — proceeding anyway.")

        # ── Step 2: If 'Review Unanswered' appears, skip it ───
        try:
            review = self.page.locator("#reviewTestConfirm")
            if await review.count() > 0 and await review.is_visible():
                print("  [*] 'Review Unanswered' appeared — clicking Show Results instead ...")
                await self.page.locator("#endTestConfirm").click()
                await asyncio.sleep(1)
                return
        except Exception:
            pass

        # ── Step 3: Click Show Results ─────────────────────────
        for selector, desc in [
            ("#endTestConfirm",                       "Show Results (#endTestConfirm)"),
            ("button:has-text('Show Results')",        "Show Results button"),
            ("xpath=//*[@id='endTestConfirm']",        "Show Results (XPath)"),
        ]:
            try:
                btn = self.page.locator(selector).first
                await btn.wait_for(state="visible", timeout=8_000)
                await btn.click()
                print(f"  [OK] {desc} clicked.")
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=15_000)
                except PWTimeout:
                    pass
                return
            except Exception:
                continue

        print("  [!] Show Results not found — may have auto-navigated.")
