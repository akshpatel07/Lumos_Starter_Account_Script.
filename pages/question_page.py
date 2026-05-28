# ─────────────────────────────────────────────────────────────
#  pages/question_page.py  —  Scrape question, detect type,
#                              read choices, get question number
# ─────────────────────────────────────────────────────────────

import re
from playwright.async_api import Page, TimeoutError as PWTimeout
from pages.base_page import BasePage
from config.settings import XPATHS, QUESTION_OVERRIDES


class QuestionPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

    # ── Wait for question to be ready ─────────────────────────

    async def wait_for_question(self, timeout: int = 10_000):
        """Block until #questionBody is visible."""
        try:
            await self.page.locator(XPATHS["question_body"]).wait_for(
                state="visible", timeout=timeout
            )
        except PWTimeout:
            print("  [WARN] Question body not visible yet — continuing anyway.")

    # ── Question number ───────────────────────────────────────

    async def get_question_number(self) -> tuple[int, int]:
        """
        Read 'Question: X / Y' from the counter div.
        Returns (current, total) e.g. (3, 14).
        """
        try:
            text = await self.get_text(XPATHS["question_number"])
            m = re.search(r'(\d+)\s*/\s*(\d+)', text)
            if m:
                return int(m.group(1)), int(m.group(2))
        except Exception:
            pass
        return (0, 0)

    # ── Question text ─────────────────────────────────────────

    async def get_question_text(self) -> str:
        """Return all text inside #questionBody."""
        return await self.get_text(XPATHS["question_body"])

    # ── Screenshot ────────────────────────────────────────────

    async def get_question_screenshot_b64(self) -> str | None:
        """Screenshot the question panel for GPT vision."""
        return await self.screenshot_element_b64(XPATHS["question_body"])

    # ── Answer choices ────────────────────────────────────────

    async def get_choices(self, q_num: int = 0) -> list[str]:
        """
        Return clean list of MCQ choice texts.
        Strips leading 'A.  ', 'B.  ' prefix.
        Respects QUESTION_OVERRIDES if set for this question number.
        """
        xpath = XPATHS["choice_labels"]
        if q_num and q_num in QUESTION_OVERRIDES:
            override = QUESTION_OVERRIDES[q_num]
            xpath = override.get("label_xpath", xpath)

        labels = self.page.locator(xpath)
        count  = await labels.count()
        choices = []
        for i in range(count):
            raw   = (await labels.nth(i).inner_text()).strip()
            clean = re.sub(r'^[A-Da-d]\.\s+', '', raw).strip()
            choices.append(clean)
        return choices

    # ── Question type detection ───────────────────────────────

    async def detect_type(self, q_num: int = 0) -> str:
        """
        Returns one of:
          'multiple_choice'  — radio buttons (input.radio12)
          'multi_select'     — checkboxes
          'text_input'       — fill-in-blank (input.editor12)
          'dropdown'         — <select> elements
          'screenshot_only'  — drag-drop or unrecognised

        Respects QUESTION_OVERRIDES if set for this question number.
        """
        # Check hardcoded override first
        if q_num and q_num in QUESTION_OVERRIDES:
            forced = QUESTION_OVERRIDES[q_num].get("type")
            if forced:
                return forced

        # Auto-detect
        if await self.page.locator(XPATHS["radio_inputs"]).count() > 0:
            return "multiple_choice"
        if await self.page.locator(XPATHS["checkbox_inputs"]).count() > 0:
            return "multi_select"
        if await self.page.locator(XPATHS["text_inputs"]).count() > 0:
            return "text_input"
        if await self.page.locator(XPATHS["select_inputs"]).count() > 0:
            return "dropdown"
        return "screenshot_only"

    # ── Is test finished? ─────────────────────────────────────

    async def is_finished(self) -> bool:
        """Return True if we're past the last question."""
        url = self.page.url
        if any(x in url for x in ["validateans", "showresult", "/result"]):
            return True
        for key in ["show_results_btn", "review_unans_btn"]:
            try:
                if await self.page.locator(XPATHS[key]).is_visible():
                    return True
            except Exception:
                pass
        return False
