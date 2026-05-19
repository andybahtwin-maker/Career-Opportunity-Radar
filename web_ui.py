from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from config import DIGEST_MAX_JOBS, DIGEST_MIN_SCORE, JOBS_ARCHIVE_FILE, SEARCH_PROFILE_FILE
from digest import digest_eligible, match_reasons, top_digest_jobs
from storage import add_description_fields, load_archive, save_archive
from utils import posting_age_days


HOST = "127.0.0.1"
PORT = 8787

DEFAULT_SEARCH_PROFILE = """# Search Parameters

These parameters describe the current public, generic search intent. They are editable from the local Profile tab and are informational only in this version; scoring still uses `scorers/rules.py`.

## Target roles

- Sales Engineer
- Solutions Consultant / Solution Consultant
- Account Executive / Strategic Account Executive / Enterprise Account Executive
- Customer Success / Construction Success
- Implementation Consultant / Implementation Specialist
- Technical Account Manager
- Technical sales roles

## Target domains

- Construction SaaS
- AEC technology
- Drone / reality capture
- Field operations
- Contractor workflow
- Mapping, visualization, and digital twin tools

## Location preference

- Remote
- United States
- Denver-friendly
- Hybrid roles where the location is compatible

## Positive signals

- Technical demos and presentations
- Customer-facing work
- Workflow and operations language
- Construction, AEC, contractor, or field operations language
- Remote or hybrid work
- Fresh postings

## Negative signals

- Software engineering
- Backend or DevOps
- Marketing
- Procurement
- Product operations
- SDR-only roles
- Commission-only roles
- Door-to-door or canvassing
- Own-vehicle-required language
"""


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
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/jobs"}:
            self.write_html(render_jobs_page())
            return
        if parsed.path == "/profile":
            saved = "saved=1" in parsed.query
            self.write_html(render_profile_page(saved=saved))
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/toggle-applied":
            length = int(self.headers.get("Content-Length") or 0)
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            job_id = first_value(form, "id")
            url = first_value(form, "url")
            toggle_applied(job_id=job_id, url=url)
            self.redirect("/jobs")
            return

        if self.path == "/profile/save":
            length = int(self.headers.get("Content-Length") or 0)
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            save_search_profile(first_value(form, "search_parameters"))
            self.redirect("/profile?saved=1")
            return

        self.send_error(404)

    def write_html(self, html_content: str) -> None:
        body = html_content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
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


def load_search_profile() -> str:
    if not SEARCH_PROFILE_FILE.exists():
        save_search_profile(DEFAULT_SEARCH_PROFILE)
    return SEARCH_PROFILE_FILE.read_text(encoding="utf-8")


def save_search_profile(content: str) -> None:
    SEARCH_PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_PROFILE_FILE.write_text(content.rstrip() + "\n", encoding="utf-8")


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


def render_jobs_page() -> str:
    jobs = dashboard_jobs()
    cards = "\n".join(render_job_card(job) for job in jobs)
    if not cards:
        cards = '<section class="empty">No high-signal jobs found. Run <code>python3 main.py --json</code> to scan.</section>'
    return render_page("jobs", cards)


def render_profile_page(saved: bool = False) -> str:
    notice = '<div class="notice">Saved search parameters.</div>' if saved else ""
    content = f"""
<section class="profile-panel">
  {notice}
  <h2>Search Parameters</h2>
  <p class="help">Informational only in this version. Scoring still uses <code>scorers/rules.py</code>.</p>
  <form method="post" action="/profile/save">
    <label for="search_parameters">Search Parameters</label>
    <textarea id="search_parameters" name="search_parameters" spellcheck="true">{escape(load_search_profile())}</textarea>
    <div class="actions">
      <button type="submit">Save</button>
    </div>
  </form>
</section>"""
    return render_page("profile", content)


def render_page(active_tab: str, content: str) -> str:
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
    .tabs {{
      display: flex;
      gap: 8px;
      margin-top: 18px;
      border-bottom: 1px solid var(--border);
    }}
    .tab {{
      display: inline-block;
      padding: 9px 12px;
      color: var(--muted);
      text-decoration: none;
      border: 1px solid transparent;
      border-bottom: 0;
      border-radius: 6px 6px 0 0;
      font-weight: 650;
    }}
    .tab.active {{
      color: var(--text);
      background: var(--card);
      border-color: var(--border);
      margin-bottom: -1px;
    }}
    .card, .profile-panel {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px 18px;
      margin: 12px 0;
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
      margin: 10px 0 14px;
      color: #344054;
    }}
    .description-preview, .description-full {{
      white-space: pre-wrap;
    }}
    .description-full[hidden], .description-preview[hidden] {{
      display: none;
    }}
    .link-button {{
      border: 0;
      padding: 4px 0;
      color: var(--accent);
      background: transparent;
      font-weight: 650;
      text-decoration: underline;
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
    label {{
      display: block;
      margin: 14px 0 8px;
      font-weight: 700;
    }}
    textarea {{
      width: 100%;
      min-height: 520px;
      resize: vertical;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      color: var(--text);
      font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background: #fbfcfd;
    }}
    .help {{
      color: var(--muted);
      margin: 8px 0 0;
    }}
    .notice {{
      border: 1px solid #9ac89f;
      background: #eef8ef;
      color: #166534;
      border-radius: 6px;
      padding: 8px 10px;
      margin-bottom: 12px;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Career Opportunity Radar</h1>
      <p class="subhead">Local dashboard backed by {escape(str(JOBS_ARCHIVE_FILE))}</p>
      <nav class="tabs" aria-label="Dashboard tabs">
        <a class="tab {'active' if active_tab == 'jobs' else ''}" href="/jobs">Jobs / Radar</a>
        <a class="tab {'active' if active_tab == 'profile' else ''}" href="/profile">Profile</a>
      </nav>
    </header>
    {content}
  </main>
  <script>
    document.addEventListener('click', function (event) {{
      var button = event.target.closest('[data-description-toggle]');
      if (!button) {{
        return;
      }}
      var description = button.closest('.description');
      var preview = description.querySelector('.description-preview');
      var full = description.querySelector('.description-full');
      var expanded = button.getAttribute('aria-expanded') === 'true';
      preview.hidden = !expanded;
      full.hidden = expanded;
      button.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      button.textContent = expanded ? 'Show more' : 'Show less';
    }});
  </script>
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
    description = str(job.get("description_excerpt") or "No description excerpt available.")
    preview = description_preview(description)
    toggle = ""
    if preview != description:
        toggle = '<button class="link-button" type="button" data-description-toggle aria-expanded="false">Show more</button>'

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
  <div class="description">
    <div class="description-preview">{escape(preview)}</div>
    <div class="description-full" hidden>{escape(description)}</div>
    {toggle}
  </div>
  <div class="actions">
    <a class="button" href="{escape(url)}" target="_blank" rel="noopener noreferrer">Open job posting</a>
    <form method="post" action="/toggle-applied">
      <input type="hidden" name="id" value="{escape(job.get("id"))}">
      <input type="hidden" name="url" value="{escape(url)}">
      <button type="submit">{escape(applied_action)}</button>
    </form>
  </div>
</section>"""


def description_preview(description: str, limit: int = 300) -> str:
    description = " ".join(description.split())
    if len(description) <= limit:
        return description
    trimmed = description[:limit].rsplit(" ", 1)[0].rstrip(".,;:")
    return f"{trimmed}..."


def escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)
