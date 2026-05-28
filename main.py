# ─────────────────────────────────────────────────────────────
#  main.py  —  Entry point — orchestrates the full workflow
# ─────────────────────────────────────────────────────────────

import sys
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

# ── Force UTF-8 output so Unicode chars work on Windows cp1252 ──
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Project imports ───────────────────────────────────────────
from config.settings      import HEADLESS, SLOW_MO, VIEWPORT
from pages.nav_page       import NavPage
from pages.question_page  import QuestionPage
from actions.gpt_action   import ask_gpt
from actions.answer_action import AnswerAction
from actions.nav_action   import NavAction
from reports.report_builder import TestReport, QuestionResult
from reports.email_sender   import send_report, save_html_report
from config.state_manager   import increment_code


async def run():
    report = TestReport(
        student_name="Student",
        test_name="Unit 1 Test",
        start_time=datetime.now(),
    )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO,
            args=["--start-maximized"],
        )
        context = await browser.new_context(no_viewport=True)  # --start-maximized sets the size
        page    = await context.new_page()

        # ── Initialise page objects & actions ─────────────────
        nav_page   = NavPage(page)
        q_page     = QuestionPage(page)
        answerer   = AnswerAction(page)
        navigator  = NavAction(page)

        try:
            # ── 1. Open site ───────────────────────────────────
            await nav_page.open()
            await nav_page.close_popup_if_present()

            # ── 2. Go to notifications → start test ───────────
            await nav_page.go_to_notifications()
            await nav_page.start_unit1_test()

            # ── 3. Answer all questions ────────────────────────
            q_num = 0
            while True:
                q_num += 1
                print(f"\n{'='*60}")
                print(f"  Question #{q_num}")
                print(f"{'='*60}")

                # Check if test ended (URL-based or results button visible)
                if await q_page.is_finished():
                    print("[*] Test finished — exiting loop.")
                    break

                # Wait for question body
                await q_page.wait_for_question()

                # Read current / total from counter
                current, total = await q_page.get_question_number()
                print(f"  [Counter] {current} / {total}")

                # Scrape
                q_text   = await q_page.get_question_text()
                choices  = await q_page.get_choices(q_num)
                q_type   = await q_page.detect_type(q_num)
                ss_b64   = await q_page.get_question_screenshot_b64()
                ss_bytes = await q_page.screenshot_page_bytes()

                preview = q_text[:160].replace('\n', ' ')
                print(f"  [Q]    {preview}{'...' if len(q_text) > 160 else ''}")
                print(f"  [Type] {q_type}")
                if choices:
                    for i, c in enumerate(choices):
                        print(f"         {chr(65+i)}) {c}")

                # Ask GPT
                status = "answered"
                gpt_answer = ""
                try:
                    gpt_answer = ask_gpt(q_text, choices, ss_b64, q_type)
                    print(f"  [GPT]  -> '{gpt_answer}'")
                except Exception as e:
                    print(f"  [GPT ERROR] {e}")
                    gpt_answer = "ERROR"
                    status = "error"

                # Answer DOM
                if status != "error":
                    try:
                        await answerer.answer_by_question_number(
                            q_num, q_type, gpt_answer, choices
                        )
                    except Exception as e:
                        print(f"  [ANSWER ERROR] {e}")
                        status = "error"

                # Record in report
                report.add(QuestionResult(
                    number     = q_num,
                    q_type     = q_type,
                    question   = q_text[:200],
                    choices    = choices,
                    gpt_answer = gpt_answer,
                    status     = status,
                    screenshot = ss_bytes,
                ))

                # Check if finished (URL changed after answering)
                if await q_page.is_finished():
                    print("[*] Test finished after answering.")
                    break

                # If this was the LAST question — go straight to finish, don't click Next
                if current > 0 and current >= total:
                    print(f"[*] Answered last question ({current}/{total}) — going to finish.")
                    break

                # Click Next (handles modals internally)
                await navigator.click_next()

            # ── 4. End test → Show Results ─────────────────────
            await navigator.finish_test()

            # ── 5. Scrape actual student score from results page ──
            results_data = await nav_page.scrape_results()
            actual_score = results_data.get("score",      "N/A")
            actual_pct   = results_data.get("percentage", "N/A")
            actual_qs    = results_data.get("questions",  "N/A")

            # Build score string  e.g. "4/13 (30.77%)"
            if actual_score != "N/A" and actual_pct != "N/A":
                score_str = f"{actual_score}  ({actual_pct})"
            elif actual_score != "N/A":
                score_str = actual_score
            else:
                score_str = "N/A"

            # ── 6. PASS if score extracted, FAIL otherwise ────
            score_extracted = actual_score not in ("N/A", "", "ERROR")
            status = "PASS" if score_extracted else "FAIL"

            report.finish(score=score_str, status=status)

            print(f"\n{'='*60}")
            print(f"  STUDENT SCORE : {actual_score}")
            print(f"  PERCENTAGE    : {actual_pct}")
            print(f"  QUESTIONS     : {actual_qs}")
            print(f"  RESULT        : {status}")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"\n[FATAL ERROR] {e}")
            report.finish(score="N/A", status="FAIL")
            raise

        finally:
            # ── 6. Logout ──────────────────────────────────────
            try:
                await nav_page.logout()
            except Exception:
                pass

            await asyncio.sleep(2)
            await browser.close()

            # ── 7. Save HTML report + send email ───────────────
            html_file = save_html_report(report)
            send_report(report)

            # ── 8. Increment D-code for the next run ────────────────
            increment_code()

            print(f"\n[OK] Automation complete.")
            print(f"    HTML Report : {html_file}")
            print(f"    Questions   : {len(report.questions)}")
            print(f"    Status      : {report.overall_status}")
            print(f"    Score       : {report.final_score}")


if __name__ == "__main__":
    asyncio.run(run())
