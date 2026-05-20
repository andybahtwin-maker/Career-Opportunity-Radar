from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from config import DIGEST_MAX_JOBS, DIGEST_MIN_SCORE, JOBS_ARCHIVE_FILE, SEARCH_PROFILE_FILE
from digest import digest_eligible, match_reasons, source_label, top_digest_jobs
from main import run_radar_pipeline
from storage import add_description_fields, job_matches_reference, load_archive, save_archive, update_archive_job
from utils import posting_age_days, today_iso


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
            show_hidden = "show_hidden=1" in parsed.query
            self.write_html(render_jobs_page(show_hidden=show_hidden))
            return
        if parsed.path == "/profile":
            saved = "saved=1" in parsed.query
            self.write_html(render_profile_page(saved=saved))
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/toggle-applied":
            form = read_form(self)
            job_id = first_value(form, "id")
            url = first_value(form, "url")
            toggle_applied(job_id=job_id, url=url)
            self.redirect(job_page_redirect(form))
            return

        if self.path == "/toggle-hidden":
            form = read_form(self)
            job_id = first_value(form, "id")
            url = first_value(form, "url")
            set_hidden(job_id=job_id, url=url, ignored=first_value(form, "ignored") != "0")
            self.redirect(job_page_redirect(form))
            return

        if self.path == "/save-notes":
            form = read_form(self)
            job_id = first_value(form, "id")
            url = first_value(form, "url")
            notes = first_value(form, "notes")
            update_archive_job(job_id=job_id, url=url, updates={"notes": notes})
            self.redirect(job_page_redirect(form))
            return

        if self.path == "/profile/save":
            form = read_form(self)
            save_search_profile(first_value(form, "search_parameters"))
            self.redirect("/profile?saved=1")
            return

        if self.path == "/profile/run-radar":
            form = read_form(self)
            save_search_profile(first_value(form, "search_parameters"))
            try:
                result = run_radar_pipeline()
            except Exception as exc:
                result = {"errors": [str(exc)], "warnings": [], "total_jobs_scanned": 0, "jobs_accepted": 0, "jobs_rejected": 0}
            self.write_html(render_profile_page(saved=True, run_result=result))
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


def job_page_redirect(form: dict[str, list[str]]) -> str:
    return "/jobs?show_hidden=1" if first_value(form, "show_hidden") == "1" else "/jobs"


def read_form(handler: BaseHTTPRequestHandler) -> dict[str, list[str]]:
    length = int(handler.headers.get("Content-Length") or 0)
    return parse_qs(handler.rfile.read(length).decode("utf-8"))


def toggle_applied(job_id: str = "", url: str = "") -> bool:
    jobs = load_archive()
    changed = False
    for job in jobs:
        if not job_matches_reference(job, job_id=job_id, url=url):
            continue
        if job.get("applied"):
            job["applied"] = False
            job["applied_date"] = ""
        else:
            job["applied"] = True
            if not str(job.get("applied_date") or "").strip():
                job["applied_date"] = today_iso()
        changed = True
        break
    if changed:
        save_archive(jobs)
    return changed


def set_hidden(job_id: str = "", url: str = "", ignored: bool = True) -> bool:
    return update_archive_job(job_id=job_id, url=url, updates={"ignored": ignored})


def load_search_profile() -> str:
    if not SEARCH_PROFILE_FILE.exists():
        save_search_profile(DEFAULT_SEARCH_PROFILE)
    return SEARCH_PROFILE_FILE.read_text(encoding="utf-8")


def save_search_profile(content: str) -> None:
    SEARCH_PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_PROFILE_FILE.write_text(content.rstrip() + "\n", encoding="utf-8")


def dashboard_jobs(show_hidden: bool = False) -> tuple[list[dict], list[dict]]:
    jobs = top_digest_jobs()
    seen = {job_key(job) for job in jobs}
    applied_jobs = []
    hidden_jobs = []

    for job in load_archive():
        add_description_fields(job)
        key = job_key(job)
        if (
            job.get("ignored")
            and show_hidden
            and key not in seen
        ):
            hidden_jobs.append(job)
            seen.add(key)
            continue
        if (
            job.get("applied")
            and not job.get("ignored")
            and job.get("fit_score", 0) >= DIGEST_MIN_SCORE
            and digest_eligible(job)
            and key not in seen
        ):
            applied_jobs.append(job)
            seen.add(key)

    applied_jobs.sort(key=lambda item: item.get("fit_score", 0), reverse=True)
    hidden_jobs.sort(key=lambda item: item.get("fit_score", 0), reverse=True)
    return jobs + applied_jobs[:DIGEST_MAX_JOBS], hidden_jobs


def job_key(job: dict) -> str:
    return str(job.get("id") or job.get("url") or f"{job.get('company')}|{job.get('title')}")


def render_jobs_page(show_hidden: bool = False) -> str:
    jobs, hidden_jobs = dashboard_jobs(show_hidden=show_hidden)
    active_cards = "\n".join(render_job_card(job, show_hidden=show_hidden) for job in jobs)
    hidden_cards = "\n".join(render_job_card(job, hidden=True, show_hidden=show_hidden) for job in hidden_jobs)
    top_controls = (
        '<div class="page-actions"><a class="text-link" href="/jobs?show_hidden=1">Show hidden jobs</a></div>'
        if not show_hidden
        else '<div class="page-actions"><a class="text-link" href="/jobs">Hide hidden jobs</a></div>'
    )
    cards = active_cards
    if show_hidden:
        cards += f'<section class="section-label">Hidden jobs</section>{hidden_cards}'
    if not cards:
        cards = '<section class="empty">No high-signal jobs found. Run <code>python3 main.py --json</code> to scan.</section>'
    return render_page("jobs", top_controls + cards)


def render_profile_page(saved: bool = False, run_result: dict | None = None) -> str:
    notices = []
    if saved:
        notices.append('<div class="notice">Saved search parameters.</div>')
    if run_result is not None:
        errors = run_result.get("errors", [])
        warnings = run_result.get("warnings", [])
        if errors:
            error_text = html.escape(errors[0], quote=True)
            notices.append(
                '<div class="notice error">Radar run failed: '
                f"{error_text}"
                f" (errors: {len(errors)}, warnings: {len(warnings)})"
                "</div>"
            )
        else:
            notices.append(
                '<div class="notice success">'
                f"Radar run complete. Scanned {run_result.get('total_jobs_scanned', 0)} jobs, "
                f"accepted {run_result.get('jobs_accepted', 0)}, rejected {run_result.get('jobs_rejected', 0)}, "
                f"warnings {len(warnings)}, errors 0."
                ' <a href="/jobs">View Jobs / Radar</a>'
                "</div>"
            )
    notice = "".join(notices)
    content = f"""
<section class="profile-panel">
  {notice}
  <h2>Search Parameters</h2>
  <p class="help">Search parameters document the scoring and filtering intent used by the local rules. Discovery sources are configured separately in <code>data/discovery_sources.json</code>.</p>
  <form method="post" action="/profile/save" id="profile-form">
    <label for="search_parameters">Search Parameters</label>
    <textarea id="search_parameters" name="search_parameters" spellcheck="true">{escape(load_search_profile())}</textarea>
    <div class="actions">
      <button type="submit">Save</button>
      <button type="submit" formaction="/profile/run-radar" data-run-radar-button>Run Radar Now</button>
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
    .card.hidden {{
      opacity: 0.9;
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
    .notes {{
      margin: 12px 0 14px;
    }}
    .notes label {{
      margin-top: 0;
      margin-bottom: 6px;
    }}
    .notes textarea {{
      min-height: 90px;
      font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      padding: 10px;
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
    .page-actions {{
      margin: 10px 0 4px;
    }}
    .text-link {{
      color: var(--accent);
      font-weight: 650;
      text-decoration: none;
    }}
    .section-label {{
      margin: 22px 0 6px;
      font-size: 13px;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
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
    .notice.error {{
      border-color: #f0a9a9;
      background: #fff1f1;
      color: #9f1239;
    }}
    .notice.success {{
      border-color: #9ac89f;
      background: #eef8ef;
      color: #166534;
    }}
    .notice a {{
      color: inherit;
      font-weight: 700;
    }}
    button[disabled] {{
      opacity: 0.65;
      cursor: progress;
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
    document.addEventListener('submit', function (event) {{
      var button = event.submitter && event.submitter.matches('[data-run-radar-button]') ? event.submitter : null;
      if (!button) {{
        return;
      }}
      button.disabled = true;
      button.textContent = 'Running...';
    }});
  </script>
</body>
</html>"""


def render_job_card(job: dict, hidden: bool = False, show_hidden: bool = False) -> str:
    add_description_fields(job)
    applied = bool(job.get("applied"))
    hidden = bool(job.get("ignored")) or hidden
    age = posting_age_days(job.get("date_posted"), job.get("first_seen"))
    age_text = "" if age is None else f'<span class="pill">{escape(str(age))} days old</span>'
    applied_date = str(job.get("applied_date") or "")
    reasons = ", ".join(match_reasons(job)) or "matched scoring rules"
    applied_label = "Applied" if applied else "Not applied"
    applied_action = "Mark not applied" if applied else "Mark applied"
    hide_action = "Unhide" if hidden else "Hide"
    url = str(job.get("url") or "")
    description = str(job.get("description_excerpt") or "No description excerpt available.")
    notes = str(job.get("notes") or "")
    preview = description_preview(description)
    toggle = ""
    if preview != description:
        toggle = '<button class="link-button" type="button" data-description-toggle aria-expanded="false">Show more</button>'

    applied_date_text = f'<span class="pill">Applied on {escape(applied_date)}</span>' if applied and applied_date else ""

    return f"""<section class="card {'applied' if applied else ''} {'hidden' if hidden else ''}">
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
    <span class="pill">{escape(source_label(job))}</span>
    <span class="pill">{escape(applied_label)}</span>
    {age_text}
    {applied_date_text}
  </div>
  <div class="why"><strong>Why it matched:</strong> {escape(reasons)}</div>
  <div class="description">
    <div class="description-preview">{escape(preview)}</div>
    <div class="description-full" hidden>{escape(description)}</div>
    {toggle}
  </div>
    <div class="notes">
      <label for="notes-{escape(job_key(job))}">Notes</label>
      <form method="post" action="/save-notes">
        <input type="hidden" name="id" value="{escape(job.get("id"))}">
        <input type="hidden" name="url" value="{escape(url)}">
        <input type="hidden" name="show_hidden" value="{escape('1' if show_hidden else '')}">
        <textarea id="notes-{escape(job_key(job))}" name="notes" spellcheck="true">{escape(notes)}</textarea>
        <div class="actions">
          <button type="submit">Save Notes</button>
        </div>
      </form>
  </div>
  <div class="actions">
    <a class="button" href="{escape(url)}" target="_blank" rel="noopener noreferrer">Open job posting</a>
    <form method="post" action="/toggle-applied">
      <input type="hidden" name="id" value="{escape(job.get("id"))}">
      <input type="hidden" name="url" value="{escape(url)}">
      <input type="hidden" name="show_hidden" value="{escape('1' if show_hidden else '')}">
      <button type="submit">{escape(applied_action)}</button>
    </form>
    <form method="post" action="/toggle-hidden">
      <input type="hidden" name="id" value="{escape(job.get("id"))}">
      <input type="hidden" name="url" value="{escape(url)}">
      <input type="hidden" name="ignored" value="{escape('0' if hidden else '1')}">
      <input type="hidden" name="show_hidden" value="{escape('1' if show_hidden else '')}">
      <button type="submit">{escape(hide_action)}</button>
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
