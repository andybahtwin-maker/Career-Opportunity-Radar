from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from config import DIGEST_MAX_JOBS, DIGEST_MIN_SCORE, JOBS_ARCHIVE_FILE
from digest import digest_eligible, match_reasons, top_digest_jobs
from storage import add_description_fields, load_archive, save_archive
from utils import posting_age_days


HOST = "127.0.0.1"
PORT = 8787


def run_server(host: str = HOST, port: int = PORT) -> None:
    server = ThreadingHTTPServer((host, port), JobDashboardHandler)
    print(f"Serving local job dashboard at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


class JobDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404)
            return
        body = render_dashboard().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/toggle-applied":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        job_id = first_value(form, "id")
        url = first_value(form, "url")
        toggle_applied(job_id=job_id, url=url)
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def first_value(form: dict[str, list[str]], key: str) -> str:
    values = form.get(key) or []
    return values[0] if values else ""


def toggle_applied(job_id: str = "", url: str = "") -> bool:
    jobs = load_archive()
    changed = False
    for job in jobs:
        if (job_id and job.get("id") == job_id) or (url and job.get("url") == url):
            job["applied"] = not bool(job.get("applied"))
            changed = True
            break
    if changed:
        save_archive(jobs)
    return changed


def dashboard_jobs() -> list[dict]:
    jobs = top_digest_jobs()
    seen = {job_key(job) for job in jobs}
    applied_jobs = []

    for job in load_archive():
        add_description_fields(job)
        if (
            job.get("applied")
            and not job.get("ignored")
            and job.get("fit_score", 0) >= DIGEST_MIN_SCORE
            and digest_eligible(job)
            and job_key(job) not in seen
        ):
            applied_jobs.append(job)
            seen.add(job_key(job))

    applied_jobs.sort(key=lambda item: item.get("fit_score", 0), reverse=True)
    return jobs + applied_jobs[:DIGEST_MAX_JOBS]


def job_key(job: dict) -> str:
    return str(job.get("id") or job.get("url") or f"{job.get('company')}|{job.get('title')}")


def render_dashboard() -> str:
    jobs = dashboard_jobs()
    cards = "\n".join(render_job_card(job) for job in jobs)
    if not cards:
        cards = '<section class="empty">No high-signal jobs found. Run <code>python3 main.py --json</code> to scan.</section>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Career Opportunity Radar</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --card: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --border: #d9dee7;
      --accent: #1f6feb;
      --applied: #eef4ef;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    main {{
      max-width: 900px;
      margin: 0 auto;
      padding: 28px 18px 48px;
    }}
    header {{
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    .subhead {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 18px;
      margin: 14px 0;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}
    .card.applied {{
      background: var(--applied);
      opacity: 0.78;
    }}
    .topline {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: flex-start;
      margin-bottom: 10px;
    }}
    h2 {{
      margin: 0;
      font-size: 20px;
      letter-spacing: 0;
    }}
    .company {{
      margin-top: 3px;
      color: var(--muted);
      font-weight: 600;
    }}
    .score {{
      flex: 0 0 auto;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 5px 9px;
      font-weight: 700;
      background: #fafbfc;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 12px 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .pill {{
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 3px 8px;
      background: #fafbfc;
    }}
    .why {{
      margin: 10px 0;
      color: #344054;
      font-size: 14px;
    }}
    .description {{
      margin: 12px 0 16px;
      color: #344054;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    a.button, button {{
      appearance: none;
      border: 1px solid var(--accent);
      border-radius: 6px;
      padding: 8px 12px;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
      text-decoration: none;
    }}
    a.button {{
      color: #fff;
      background: var(--accent);
    }}
    button {{
      color: var(--accent);
      background: #fff;
    }}
    .applied button {{
      color: #166534;
      border-color: #86b38b;
      background: #f7fff8;
    }}
    .empty {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 18px;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Career Opportunity Radar</h1>
      <p class="subhead">Local dashboard backed by {escape(str(JOBS_ARCHIVE_FILE))}</p>
    </header>
    {cards}
  </main>
</body>
</html>"""


def render_job_card(job: dict) -> str:
    add_description_fields(job)
    applied = bool(job.get("applied"))
    age = posting_age_days(job.get("date_posted"), job.get("first_seen"))
    age_text = "" if age is None else f'<span class="pill">{escape(str(age))} days old</span>'
    reasons = ", ".join(match_reasons(job)) or "matched scoring rules"
    applied_label = "Applied" if applied else "Not applied"
    applied_action = "Mark not applied" if applied else "Mark applied"
    url = str(job.get("url") or "")

    return f"""<section class="card {'applied' if applied else ''}">
  <div class="topline">
    <div>
      <h2>{escape(job.get("title"))}</h2>
      <div class="company">{escape(job.get("company"))}</div>
    </div>
    <div class="score">Score {escape(str(job.get("fit_score", 0)))}</div>
  </div>
  <div class="meta">
    <span class="pill">{escape(job.get("location") or "Location not listed")}</span>
    <span class="pill">{escape(job.get("company_category") or "Not categorized")}</span>
    <span class="pill">{escape(applied_label)}</span>
    {age_text}
  </div>
  <div class="why"><strong>Why it matched:</strong> {escape(reasons)}</div>
  <div class="description">{escape(job.get("description_excerpt") or "No description excerpt available.")}</div>
  <div class="actions">
    <a class="button" href="{escape(url)}" target="_blank" rel="noopener noreferrer">Open job posting</a>
    <form method="post" action="/toggle-applied">
      <input type="hidden" name="id" value="{escape(job.get("id"))}">
      <input type="hidden" name="url" value="{escape(url)}">
      <button type="submit">{escape(applied_action)}</button>
    </form>
  </div>
</section>"""


def escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)
