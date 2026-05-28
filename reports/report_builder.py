# ─────────────────────────────────────────────────────────────
#  reports/report_builder.py  —  Collect results, build HTML
# ─────────────────────────────────────────────────────────────

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class QuestionResult:
    number:      int
    q_type:      str
    question:    str          # first 200 chars of question text
    choices:     list[str]
    gpt_answer:  str
    status:      str          # "answered" | "skipped" | "error"
    screenshot:  Optional[bytes] = None   # kept for compat; not emailed


@dataclass
class TestReport:
    student_name:   str = "Student"
    test_name:      str = "Unit 1 Test"
    start_time:     datetime = field(default_factory=datetime.now)
    end_time:       Optional[datetime] = None
    questions:      list[QuestionResult] = field(default_factory=list)
    final_score:    str = "N/A"
    overall_status: str = "UNKNOWN"   # PASS / FAIL / COMPLETED

    def add(self, result: QuestionResult):
        self.questions.append(result)

    def finish(self, score: str = "N/A", status: str = "COMPLETED"):
        self.end_time       = datetime.now()
        self.final_score    = score
        self.overall_status = status

    def duration(self) -> str:
        if self.end_time:
            secs = int((self.end_time - self.start_time).total_seconds())
            return f"{secs // 60}m {secs % 60}s"
        return "N/A"

    # ── Build HTML email body ─────────────────────────────────

    def build_html(self) -> str:
        status_color = {
            "PASS"     : "#22c55e",
            "FAIL"     : "#ef4444",
            "COMPLETED": "#3b82f6",
            "UNKNOWN"  : "#6b7280",
        }.get(self.overall_status, "#6b7280")

        answered = sum(1 for q in self.questions if q.status == "answered")
        skipped  = sum(1 for q in self.questions if q.status == "skipped")
        errors   = sum(1 for q in self.questions if q.status == "error")
        total    = len(self.questions)

        # ── Question rows ─────────────────────────────────────
        rows_html = ""
        for q in self.questions:
            type_badge_color = {
                "multiple_choice" : "#6366f1",
                "multi_select"    : "#8b5cf6",
                "text_input"      : "#0ea5e9",
                "dropdown"        : "#f59e0b",
                "screenshot_only" : "#6b7280",
            }.get(q.q_type, "#6b7280")

            status_badge = {
                "answered": ('<span style="background:#22c55e;color:#fff;'
                             'padding:2px 8px;border-radius:12px;font-size:11px;">&#10003; Answered</span>'),
                "skipped" : ('<span style="background:#f59e0b;color:#fff;'
                             'padding:2px 8px;border-radius:12px;font-size:11px;">&#9888; Skipped</span>'),
                "error"   : ('<span style="background:#ef4444;color:#fff;'
                             'padding:2px 8px;border-radius:12px;font-size:11px;">&#10007; Error</span>'),
            }.get(q.status, "")

            choices_html = ""
            if q.choices:
                choices_html = "<br><small style='color:#6b7280;'>" + " &nbsp;|&nbsp; ".join(
                    f"<b>{chr(65+i)}</b>) {c[:40]}" for i, c in enumerate(q.choices)
                ) + "</small>"

            rows_html += f"""
            <tr style="border-bottom:1px solid #e5e7eb;">
              <td style="padding:10px 8px;text-align:center;font-weight:700;color:#374151;">
                Q{q.number}
              </td>
              <td style="padding:10px 8px;">
                <span style="background:{type_badge_color};color:#fff;padding:2px 7px;
                             border-radius:10px;font-size:11px;">{q.q_type}</span>
              </td>
              <td style="padding:10px 8px;color:#374151;font-size:13px;max-width:340px;">
                {q.question[:120]}{"..." if len(q.question) > 120 else ""}
                {choices_html}
              </td>
              <td style="padding:10px 8px;text-align:center;">
                <b style="color:#1d4ed8;">{q.gpt_answer}</b>
              </td>
              <td style="padding:10px 8px;text-align:center;">
                {status_badge}
              </td>
            </tr>"""

        # ── Full HTML ─────────────────────────────────────────
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>StepUp Automation Report</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:'Segoe UI',Arial,sans-serif;">

  <div style="max-width:760px;margin:30px auto;background:#fff;
              border-radius:12px;overflow:hidden;
              box-shadow:0 4px 24px rgba(0,0,0,0.08);">

    <!-- ── Header ── -->
    <div style="background:#1e1b4b;padding:28px 32px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <h1 style="margin:0;color:#fff;font-size:22px;letter-spacing:0.5px;">
            &#128203; StepUp Automation Report
          </h1>
          <p style="margin:6px 0 0;color:#a5b4fc;font-size:14px;">
            {self.test_name} &nbsp;&middot;&nbsp; {self.student_name}
          </p>
        </div>
        <div style="background:{status_color};color:#fff;padding:10px 20px;
                    border-radius:8px;font-size:20px;font-weight:700;">
          {self.overall_status}
        </div>
      </div>
    </div>

    <!-- ── Score highlight banner ── -->
    <div style="background:#f0f9ff;border-bottom:3px solid #0ea5e9;
                padding:18px 32px;display:flex;align-items:center;gap:24px;">
      <div style="font-size:13px;color:#0369a1;font-weight:600;letter-spacing:0.5px;">
        STUDENT SCORE
      </div>
      <div style="font-size:32px;font-weight:800;color:#0c4a6e;letter-spacing:1px;">
        {self.final_score}
      </div>
    </div>

    <!-- ── Summary cards ── -->
    <div style="display:flex;gap:0;border-bottom:1px solid #e5e7eb;">
      {self._card("Score",    self.final_score, "#1d4ed8")}
      {self._card("Answered", str(answered),    "#22c55e")}
      {self._card("Skipped",  str(skipped),     "#f59e0b")}
      {self._card("Errors",   str(errors),      "#ef4444")}
      {self._card("Duration", self.duration(),  "#6366f1")}
    </div>

    <!-- ── Meta info ── -->
    <div style="padding:16px 32px;background:#f9fafb;border-bottom:1px solid #e5e7eb;
                font-size:13px;color:#6b7280;">
      <b>Started:</b> {self.start_time.strftime("%Y-%m-%d %H:%M:%S")} &nbsp;&middot;&nbsp;
      <b>Finished:</b> {self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else "N/A"} &nbsp;&middot;&nbsp;
      <b>Total Questions:</b> {total}
    </div>

    <!-- ── Question table ── -->
    <div style="padding:24px 32px;">
      <h2 style="margin:0 0 16px;font-size:16px;color:#1e1b4b;">Question Details</h2>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#f3f4f6;">
            <th style="padding:10px 8px;text-align:center;color:#374151;">#</th>
            <th style="padding:10px 8px;text-align:left;color:#374151;">Type</th>
            <th style="padding:10px 8px;text-align:left;color:#374151;">Question</th>
            <th style="padding:10px 8px;text-align:center;color:#374151;">GPT Answer</th>
            <th style="padding:10px 8px;text-align:center;color:#374151;">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>

    <!-- ── Footer ── -->
    <div style="padding:16px 32px;background:#1e1b4b;text-align:center;">
      <p style="margin:0;color:#a5b4fc;font-size:12px;">
        Generated by StepUp Automation Suite &nbsp;&middot;&nbsp;
        {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
      </p>
    </div>

  </div>
</body>
</html>"""
        return html

    def _card(self, label: str, value: str, color: str) -> str:
        return f"""
        <div style="flex:1;padding:16px;text-align:center;border-right:1px solid #e5e7eb;">
          <div style="font-size:11px;color:#6b7280;margin-bottom:4px;">{label}</div>
          <div style="font-size:22px;font-weight:700;color:{color};">{value}</div>
        </div>"""
