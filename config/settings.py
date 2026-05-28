# ─────────────────────────────────────────────────────────────
#  config/settings.py  —  ALL project settings in one place
#  Edit this file before running.
# ─────────────────────────────────────────────────────────────

import os

# ── Site ──────────────────────────────────────────────────────
SITE_URL = (
    "https://www.lumoslearning.com/llwp/stepup-starter-for-schools.html?schoolid=439546&code=D050"
)

# ── OpenAI ────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "API_KEY")
GPT_MODEL      = "gpt-4o-mini"

# ── Browser ───────────────────────────────────────────────────
HEADLESS       = False          # True = no browser window
SLOW_MO        = 200            # ms between actions (human-like)
VIEWPORT       = {"width": 1280, "height": 900}
DEFAULT_TIMEOUT = 20_000        # ms

# ── Email Report ──────────────────────────────────────────────
EMAIL_ENABLED  = True           # Set False to skip email

SMTP_HOST      = "smtp.gmail.com"        # e.g. smtp.gmail.com / smtp.office365.com
SMTP_PORT      = 587                     # 587 for TLS, 465 for SSL
SMTP_USER      = "automationtesting.lumos@gmail.com"  # sender email
SMTP_PASSWORD  = "ajxvmfxqvubczddj"     # Gmail: use App Password
EMAIL_FROM     = ""
EMAIL_TO       = ["akshbpatel.lumos@gmail.com"] # list of recipients

EMAIL_SUBJECT  = "Automation Report: Starter accounts — {status} | Score: {score}"

# ── XPaths (hardcoded from XPath Inspector Pro) ───────────────
# Update these using xpath_extractor.py whenever the site changes

XPATHS = {
    # ── Navigation ──────────────────────────────────────────
    "close_popup"        : "//span[@class='glyphicon glyphicon-remove']",
    "notification_link"  : "//li[@class='hidden-xs']/a[@class='notifications-link']",
    "logout_link"        : "//a[normalize-space()='Logout']",

    # ── Test start ───────────────────────────────────────────
    "unit1_start_btn"    : "//tr[contains(.,'Unit 1')]//button",

    # ── Question page ────────────────────────────────────────
    "question_body"      : "//*[@id='questionBody']",
    "question_number"    : "//*[@id='qnoDiv']",

    # ── Answer types ─────────────────────────────────────────
    "choice_labels"      : "//label[@class='answerEliminator']",    # MCQ labels
    "radio_inputs"       : "//input[@class='radio12']",             # MCQ radios
    "checkbox_inputs"    : "//input[@type='checkbox']",             # Multi-select
    "text_inputs"        : "//input[@class='editor12'] | //textarea[@class='editor12']",
    "select_inputs"      : "//*[@id='questionBody']//select",

    # ── Navigation buttons ───────────────────────────────────
    "end_test_btn"       : "//*[@id='exit']",
    "show_results_btn"   : "//*[@id='endTestConfirm']",
    "review_unans_btn"   : "//*[@id='reviewTestConfirm']",
}

# ── Question hardcodes (Q1–Q10) ───────────────────────────────
# Format: { question_number: { "type": "mcq|text|multi", "xpath_answer_N": "xpath" } }
# Useful when a specific question has unusual DOM. Leave empty to use auto-detection.
QUESTION_OVERRIDES = {
    # Example:
    # 1: { "type": "text", "input_xpath": "//input[@class='editor12']" },
    # 2: { "type": "mcq",  "label_xpath": "//label[@class='answerEliminator']" },
}
