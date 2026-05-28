# ─────────────────────────────────────────────────────────────
#  actions/gpt_action.py  —  All OpenAI / GPT-4o-mini calls
# ─────────────────────────────────────────────────────────────

from openai import OpenAI
from config.settings import OPENAI_API_KEY, GPT_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def ask_gpt(
    question_text: str,
    choices: list[str],
    screenshot_b64: str | None,
    q_type: str = "multiple_choice"
) -> str:
    """
    Send question + choices + screenshot to GPT-4o-mini.

    Returns:
      - For MCQ        : single letter  e.g. 'B'
      - For multi_select: letters       e.g. 'A, C'
      - For text_input : raw value      e.g. '32'
      - For dropdown   : letter         e.g. 'A'
    """
    # ── Build instruction based on question type ───────────────
    if q_type in ("multiple_choice", "dropdown"):
        choices_block = "\n\nAnswer choices:\n" + "\n".join(
            f"  {chr(65+i)}) {c}" for i, c in enumerate(choices)
        )
        instruction = (
            "Reply with ONLY the single letter of the correct answer (A, B, C, or D). "
            "No punctuation. No explanation. Just the letter."
        )

    elif q_type == "multi_select":
        choices_block = "\n\nAnswer choices (select ALL that apply):\n" + "\n".join(
            f"  {chr(65+i)}) {c}" for i, c in enumerate(choices)
        )
        instruction = (
            "Reply with ONLY the letters of ALL correct answers separated by commas. "
            "Example: 'A, C'  or  'B, D'. No explanation."
        )

    else:  # text_input / screenshot_only
        choices_block = ""
        instruction = (
            "This is a fill-in-the-blank or short-answer question. "
            "Reply with ONLY the exact value that belongs in the blank — "
            "just a number, word, or short phrase. "
            "NO units, NO full sentences, NO explanation. "
            "Good examples: '32'   'photosynthesis'   'George Washington'   '3/4'"
        )

    # ── Build message content ──────────────────────────────────
    user_content: list = []

    if screenshot_b64:
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{screenshot_b64}",
                "detail": "high",
            },
        })

    user_content.append({
        "type": "text",
        "text": f"Question:\n{question_text}{choices_block}\n\n{instruction}",
    })

    # ── Call API ───────────────────────────────────────────────
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert tutor answering school test questions with 100% accuracy. "
                    "For multiple choice: reply with only the letter (A/B/C/D). "
                    "For multi-select: reply with letters separated by commas. "
                    "For fill-in-blank: reply with only the raw value — number or word(s). "
                    "Never include explanations, labels, or units in your reply."
                ),
            },
            {"role": "user", "content": user_content},
        ],
        max_tokens=60,
        temperature=0,
    )

    return response.choices[0].message.content.strip()
