import re
import asyncio
from playwright.async_api import Page

from config.settings import XPATHS, QUESTION_OVERRIDES


class AnswerAction:
    def __init__(self, page: Page):
        self.page = page

    # ─────────────────────────────────────────────────────────
    # PUBLIC METHODS
    # ─────────────────────────────────────────────────────────

    async def answer(
        self,
        q_num: int,
        q_type: str,
        gpt_answer: str,
        choices: list[str]
    ):
        """
        Generic answer router based on question type.
        Uses QUESTION_OVERRIDES if available.
        """

        print(
            f"[Answer] Q{q_num} | type={q_type} | gpt='{gpt_answer}'"
        )

        override = QUESTION_OVERRIDES.get(q_num, {})

        if q_type == "multiple_choice":
            await self._mcq(gpt_answer, choices, override)

        elif q_type == "multi_select":
            await self._multi_select(gpt_answer, choices, override)

        elif q_type == "text_input":
            await self._text_input(gpt_answer, override)

        elif q_type == "dropdown":
            await self._dropdown(gpt_answer, choices, override)

        else:
            print(
                f"[INFO] Q{q_num}: screenshot_only — no DOM interaction."
            )

        await asyncio.sleep(1)

    # ─────────────────────────────────────────────────────────
    # QUESTION-SPECIFIC LOGIC (Q1–Q10)
    # ─────────────────────────────────────────────────────────

    async def answer_by_question_number(
        self,
        q_num: int,
        q_type: str,
        gpt_answer: str,
        choices: list[str]
    ):
        """
        Hardcoded handling for Q1–Q10.
        Falls back to generic answer() for Q11+.
        """

        # Shared XPaths
        label_xpath = "//label[@class='answerEliminator']"
        radio_xpath = "//input[@class='radio12']"
        text_xpath = (
            "//input[@class='editor12'] | "
            "//textarea[@class='editor12']"
        )
        checkbox_xpath = "//input[@type='checkbox']"

        # ─────────────────────────────────────────────────────
        # TEXT INPUT QUESTIONS
        # ─────────────────────────────────────────────────────
        if q_num in [1, 4, 8] and q_type == "text_input":

            await self._fill_by_xpath(
                text_xpath,
                gpt_answer
            )

        # ─────────────────────────────────────────────────────
        # MULTI SELECT QUESTIONS
        # ─────────────────────────────────────────────────────
        elif q_num == 6 and q_type == "multi_select":

            await self._checkbox_by_xpath(
                checkbox_xpath,
                gpt_answer
            )

        elif q_num == 10:

            if q_type == "text_input":

                await self._fill_by_xpath(
                    text_xpath,
                    gpt_answer
                )

            elif q_type == "multi_select":

                await self._checkbox_by_xpath(
                    checkbox_xpath,
                    gpt_answer
                )

            else:

                await self._mcq_by_xpath(
                    label_xpath,
                    radio_xpath,
                    gpt_answer,
                    choices
                )

        # ─────────────────────────────────────────────────────
        # DEFAULT MCQ HANDLING FOR Q1–Q10
        # ─────────────────────────────────────────────────────
        elif q_num in range(1, 11):

            await self._mcq_by_xpath(
                label_xpath,
                radio_xpath,
                gpt_answer,
                choices
            )

        # ─────────────────────────────────────────────────────
        # FALLBACK FOR Q11+
        # ─────────────────────────────────────────────────────
        else:
            await self.answer(
                q_num,
                q_type,
                gpt_answer,
                choices
            )

        await asyncio.sleep(1)

    # ─────────────────────────────────────────────────────────
    # HELPER METHODS
    # ─────────────────────────────────────────────────────────

    def _letter_to_index(self, answer: str) -> int:
        """
        Convert answer letter (A/B/C/D) → index.
        """

        match = re.findall(r"[A-Da-d]", answer)

        if not match:
            return 0

        return ord(match[0].upper()) - ord("A")

    # ─────────────────────────────────────────────────────────
    # MCQ
    # ─────────────────────────────────────────────────────────

    async def _mcq(
        self,
        answer: str,
        choices: list,
        override: dict
    ):
        label_xpath = override.get(
            "label_xpath",
            XPATHS["choice_labels"]
        )

        radio_xpath = override.get(
            "radio_xpath",
            XPATHS["radio_inputs"]
        )

        await self._mcq_by_xpath(
            label_xpath,
            radio_xpath,
            answer,
            choices
        )

    async def _mcq_by_xpath(
        self,
        label_xpath: str,
        radio_xpath: str,
        answer: str,
        choices: list
    ):
        idx = self._letter_to_index(answer)

        labels = self.page.locator(label_xpath)
        radios = self.page.locator(radio_xpath)

        label_count = await labels.count()
        radio_count = await radios.count()

        print(
            f"→ MCQ | answer={answer.upper()} | "
            f"idx={idx} | "
            f"{label_count} labels | "
            f"{radio_count} radios"
        )

        # Click label first
        if 0 <= idx < label_count:
            await labels.nth(idx).click()
            return

        # Fallback to radio button
        if 0 <= idx < radio_count:
            await radios.nth(idx).click(force=True)
            return

        # Text matching fallback
        for i in range(label_count):

            text = (
                await labels.nth(i).inner_text()
            ).strip()

            if answer.lower() in text.lower():

                await labels.nth(i).click()
                return

        # Final fallback
        if label_count > 0:

            print(
                f"[WARN] Index {idx} out of range. "
                f"Clicking first option."
            )

            await labels.nth(0).click()

    # ─────────────────────────────────────────────────────────
    # MULTI SELECT
    # ─────────────────────────────────────────────────────────

    async def _multi_select(
        self,
        answer: str,
        choices: list,
        override: dict
    ):
        xpath = override.get(
            "checkbox_xpath",
            XPATHS["checkbox_inputs"]
        )

        await self._checkbox_by_xpath(xpath, answer)

    async def _checkbox_by_xpath(
        self,
        xpath: str,
        answer: str
    ):
        letters = re.findall(r"[A-Da-d]", answer.upper())

        boxes = self.page.locator(xpath)
        count = await boxes.count()

        for letter in letters:

            idx = ord(letter) - ord("A")

            if 0 <= idx < count:

                await boxes.nth(idx).click()

                print(f"→ Checked [{letter}]")

    # ─────────────────────────────────────────────────────────
    # TEXT INPUT
    # ─────────────────────────────────────────────────────────

    async def _text_input(
        self,
        answer: str,
        override: dict
    ):
        xpath = override.get(
            "input_xpath",
            XPATHS["text_inputs"]
        )

        await self._fill_by_xpath(xpath, answer)

    async def _fill_by_xpath(
        self,
        xpath: str,
        answer: str
    ):
        inputs = self.page.locator(xpath)
        count = await inputs.count()

        lines = [
            line.strip()
            for line in answer.split("\n")
            if line.strip()
        ] or [answer]

        filled = 0
        for i in range(count):

            inp = inputs.nth(i)

            if await inp.is_visible():

                value = (
                    lines[i]
                    if i < len(lines)
                    else lines[-1]
                )

                await inp.click(click_count=3)
                await inp.fill(value)

                print(
                    f"→ Filled box {i + 1}: '{value}'"
                )
                filled += 1

        if filled == 0:
            # Lumos renders some text answers inside CKEditor iframes
            # Title from Playwright recording: 'Rich Text Editor, editor1c'
            for iframe_sel in [
                'iframe[title="Rich Text Editor, editor1c"]',
                "iframe.cke_wysiwyg_frame",
            ]:
                try:
                    frame = self.page.frame_locator(iframe_sel).first
                    body  = frame.locator("body")
                    if await body.count() > 0:
                        await body.click()
                        await self.page.keyboard.press("Control+A")
                        await self.page.keyboard.type(answer or "", delay=30)
                        print(f"    -> Filled CKEditor iframe ({iframe_sel[:30]}): '{(answer or '')[:60]}'")
                        return
                except Exception as e:
                    print(f"    [WARN] iframe fill ({iframe_sel[:30]}) failed: {e}")

    # ─────────────────────────────────────────────────────────
    # DROPDOWN
    # ─────────────────────────────────────────────────────────

    async def _dropdown(
        self,
        answer: str,
        choices: list,
        override: dict
    ):
        xpath = override.get(
            "select_xpath",
            XPATHS["select_inputs"]
        )

        idx = self._letter_to_index(answer)

        selects = self.page.locator(xpath)
        count = await selects.count()

        for i in range(count):

            select = selects.nth(i)

            if await select.is_visible():

                options = await select.locator(
                    "option"
                ).all_inner_texts()

                if 0 <= idx < len(options):

                    await select.select_option(
                        index=idx
                    )

                    print(
                        f"→ Dropdown selected "
                        f"[{answer.upper()}]: "
                        f"'{options[idx]}'"
                    )