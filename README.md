# Career Opportunity Radar
Career Opportunity Radar is a local-first Python tool that monitors selected company career pages, discovers broader public job listings, scores relevant roles, and produces a small daily digest of high-signal job opportunities.
It is built for targeted review, not mass application spam. It does not auto-apply, send messages, scrape LinkedIn, bypass login walls, or scrape private accounts. It reads public ATS/company job pages and conservative public job APIs, stores a local archive, and gives you a concise workflow for deciding what is worth opening.

Built as a practical example of local-first automation, workflow design, and AI-assisted software development for technical sales/job-search operations.

**Jobs / Radar dashboard**
<img width="1756" height="1442" alt="radar-screenshot-20260519-184355" src="https://github.com/user-attachments/assets/54a0e580-eec8-4162-869b-2b38169ec56e" />

**Expanded job card with notes, applied date, and hide controls**
<img width="1750" height="1184" alt="radar-screenshot-20260519-184413" src="https://github.com/user-attachments/assets/9866a1ca-a745-4ba8-aa43-064a8a1c546e" />

**Profile tab for editable search parameters**
<img width="1842" height="1430" alt="radar-screenshot-20260519-184745" src="https://github.com/user-attachments/assets/bfa082d4-77a4-404d-9bc0-20ca890baf9c" />

## Why I Built It
Most job boards are noisy. I wanted a practical system that could watch a curated company list, preserve job history, surface strong matches, and make it easy to review opportunities from a browser or Markdown digest.

The project is intentionally simple: Python standard library, local JSON files, transparent scoring rules, and optional n8n scheduling.

## What It Does

- Scans public career pages and ATS job-board endpoints.
- Supports Lever, Greenhouse, Ashby, Workable, and conservative generic page parsing.
- Discovers jobs beyond the watchlist through explicitly configured public discovery sources.
- Stores normalized job records locally.
- Dedupes discovered and curated jobs by URL first, then by company/title.
- Pulls job descriptions when available and extracts readable page text as a fallback.
- Scores jobs with transparent keyword/rule-based logic and practical-fit labels.
- Writes a Markdown digest with clickable company/ATS links.
- Serves a local web dashboard for reviewing top opportunities from both curated companies and broader discovery sources.
- Lets you mark jobs as applied from the dashboard or Markdown workflow.
- Lets you add per-job notes, hide jobs that are not a fit, and track applied dates locally.
- Keeps job links direct to the original ATS or company application page.
- Can be launched from Linux desktop shortcuts for local use.

## Recent Updates

- Profile tab for editing local search parameters and a private candidate profile summary.
- Editable `data/search_profile.md` sample profile.
- Private `data/candidate_profile.md` candidate summary with a safe committed `data/candidate_profile.example.md` template.
- Expandable job descriptions for a cleaner Jobs / Radar dashboard.
- Discovery sources in `data/discovery_sources.json`.
- Source labels in the digest and local dashboard.
- Local-first Denver/construction/design-sales scoring that pushes remote SaaS stretch roles below realistic local fits.

## How It Works

1. `data/companies.json` defines the curated public company watchlist and ATS configuration.
2. `data/discovery_sources.json` defines broader public discovery sources.
3. `data/search_profile.md` stores editable search parameters for the local Profile tab.
4. `data/candidate_profile.md` stores the local private Candidate Profile / Resume Summary; `data/candidate_profile.example.md` is the safe public template.
5. Fetchers collect public job postings and descriptions.
6. `storage.py` merges jobs into `data/jobs_archive.json`, deduping by URL first and then company/title.
7. `scorers/rules.py` assigns a fit score and match tags.
8. `digest.py` writes `output/daily_digest.md`.
9. `web_ui.py` serves a local dashboard at `http://127.0.0.1:8787`.

The archive and output files are intentionally ignored by Git because they are local run state.

## Setup

Requires Python 3. No third-party Python packages are required.

```bash
git clone https://github.com/andybahtwin-maker/Career-Opportunity-Radar.git
cd Career-Opportunity-Radar
python3 main.py test
```

Review and edit the public company watchlist:

```bash
data/companies.json
```

Review and edit broader public discovery sources:

```bash
data/discovery_sources.json
```

Initialize your local archive by running a scan:

```bash
python3 main.py --json
```

This creates ignored local run-state files such as `data/jobs_archive.json` and `output/daily_digest.md`.

## GitHub Setup

This repository is intended to keep source code, public company configuration, generic search parameters, and the safe candidate-profile template in Git while excluding private candidate content and local run state.

Before publishing your own fork or copy, confirm `.gitignore` excludes:

- `data/jobs_archive.json`
- `data/candidate_profile.md`
- `output/`
- `.env`
- backups
- Python cache files

Then configure your local Git identity and remote as usual:

```bash
git config user.name "Your Name"
git config user.email "you@example.com"
git remote add origin <your-repo-url>
```

## Commands

Run a scan, update the archive, write the digest, and print n8n-friendly JSON:

```bash
python3 main.py --json
```

This runs the curated company watchlist and the configured discovery sources.

Run only broader public discovery sources:

```bash
python3 main.py discover
```

Write the Markdown digest from the current archive:

```bash
python3 main.py digest
```

Start the local dashboard:

```bash
python3 main.py serve
```

Then open:

```text
http://127.0.0.1:8787
```

Other useful commands:

```bash
python3 main.py scan
python3 main.py discover
python3 main.py list
python3 main.py validate
python3 main.py sync-applied
python3 main.py enrich
```

## Local Dashboard

The local dashboard has two tabs:

- Jobs / Radar: top digest jobs as cards with company, title, location, score, category, source label, posting age, match reasons, collapsed/expandable description excerpts, and a direct link to the job posting.
- Profile: editable Search Parameters in `data/search_profile.md`, a private Candidate Profile / Resume Summary in `data/candidate_profile.md`, a `Run Radar Now` button, and a note that broader discovery is configured in `data/discovery_sources.json`.

The Applied toggle writes immediately to `data/jobs_archive.json`. Applied jobs are visually muted and remain preserved in the archive.

Each job card also includes local notes, a Hide / Unhide control, and applied-date tracking. Those fields are stored in `data/jobs_archive.json` and survive future scans and discovery runs.

Job descriptions start collapsed for easier scanning. A lightweight inline vanilla JavaScript toggle expands or collapses the full excerpt without reloading the page.

The Profile tab separates search intent from candidate evidence. Search Parameters describe target roles and domains and control discovery query expansion, hard filtering, and scoring. Candidate Profile / Resume Summary describes background, constraints, and proof points for the local dashboard. Search Parameters are the human-readable targeting strategy; scoring rules and practical-fit labels live in `scorers/rules.py`, `realism.py`, and `targeting.py`. Discovery source endpoints live in `data/discovery_sources.json`.

The server binds to `127.0.0.1` only. It is intended for local personal use, not internet exposure.

Jobs tab:

```text
http://127.0.0.1:8787/jobs
```

Profile tab:

```text
http://127.0.0.1:8787/profile
```

## Desktop Launcher

For Linux desktop environments such as Linux Mint, optional `.desktop` launchers can open the dashboard or start the local server first. Keep those launchers local unless you intentionally generalize them for your own machine, because desktop files often contain absolute paths.

## Markdown Digest

`python3 main.py digest` writes:

```text
output/daily_digest.md
```

Each job includes:

- score and category
- source label
- why it matched
- applied state and applied date
- a direct Markdown link to the company/ATS posting
- raw URL for automation/sync
- applied checkbox
- short description excerpt

After manually checking applied boxes in the digest, run:

```bash
python3 main.py sync-applied
```

This sync is conservative: checked boxes mark archive jobs as applied, but unchecked boxes do not clear existing applied status.
Ignored jobs stay in the local archive but do not appear in the normal digest.

## n8n Scheduled Automation

This project can be scheduled from an n8n Execute Command node:

```bash
cd /path/to/career_opportunity_radar && /usr/bin/python3 main.py --json
```

The command prints one JSON object with run metadata, warnings, errors, and `top_opportunities`. n8n can use that JSON for notifications, logging, or routing.

## No Auto-Apply Spam

Career Opportunity Radar is a review aid. It does not submit applications, generate cover letters, message recruiters, or perform automated browser actions. Every application decision remains manual.

## Configuration

Career Opportunity Radar has two source types:

- Curated company monitoring: specific companies in `data/companies.json`.
- Broader discovery: public job sources in `data/discovery_sources.json`.

Each company entry looks like:

```json
{
  "company_name": "Example Company",
  "category": "construction_saas",
  "priority": 8,
  "notes": "Public rationale for why this company is monitored",
  "careers_url": "https://jobs.lever.co/example",
  "ats_type": "lever",
  "ats_board": "example",
  "enabled": true
}
```

Supported `ats_type` values:

- `greenhouse`
- `lever`
- `ashby`
- `workable`
- `generic`

For API-backed ATS systems, `ats_board` is usually the public slug in the careers URL.

Each discovery source entry looks like:

```json
{
  "name": "Himalayas Remote Jobs API",
  "enabled": true,
  "source_type": "himalayas_api",
  "search_url_template": "https://himalayas.app/jobs/api/search?q={keyword}&country=US&sort=recent",
  "keywords": ["sales engineer", "solutions consultant"],
  "location_terms": ["US"],
  "max_results_per_keyword": 20,
  "notes": "Public JSON search endpoint. No authentication required."
}
```

Supported discovery `source_type` values:

- `himalayas_api`
- `remotejobs_api`

Discovery is intentionally conservative. Add only public pages, RSS feeds, or JSON endpoints that work without authentication. LinkedIn is intentionally not scraped, and sources that require login, private-account access, anti-bot bypasses, or browser automation should not be added.

Discovery jobs are normalized into the same archive shape as curated company jobs, deduped with the same merge path, scored with the same rules, and shown in the same dashboard and digest with explicit source labels. This lets the Jobs / Radar tab surface broader technical sales, solutions consulting, customer success, and implementation opportunities beyond the manually selected company list without changing the existing company-watchlist scanner.

## Scoring

Scoring is rule-based and transparent. The current ranking is local-first: realistic Denver metro, construction, building-materials, interiors, showroom, design-sales, contractor-facing, stable-pay, and customer-workflow signals outrank remote SaaS keyword matches. Negative signals suppress enterprise-only/strategic/title-inflated SaaS matches, remote-only generic SaaS, SDR/BDR-only work, commission-only, door-to-door, vehicle barriers, heavy travel, and unrelated technical roles.

Every rescored job carries a practical-fit label such as `Strong Local Fit`, `Strong Construction/Design Sales Fit`, `Realistic Local Sales Fit`, `Realistic Stretch`, `Remote Stretch`, `Semantic Match Only`, `Likely ATS Reject`, `Vehicle Barrier`, `Commission-Only Risk`, or `Not a Fit`. The Jobs / Radar cards, Markdown digest, and JSON top opportunities show those labels. Remote SaaS roles can remain visible as stretch candidates when their construction/customer-workflow context is credible, but they rank after realistic local fits.

Tune scoring in:

```text
scorers/rules.py
```

The editable local profile files are:

```text
data/search_profile.md
data/candidate_profile.md
```

`data/search_profile.md` contains the human-readable targeting strategy used by the local rule path. Keep private resume/profile content in ignored `data/candidate_profile.md`; the committed `data/candidate_profile.example.md` file is the safe public Candidate Profile / Resume Summary template.

## Screenshots

Expected screenshot placeholders:

```text
screenshots/dashboard.png
screenshots/profile.png
```

## Portfolio Angle

This project demonstrates Python automation, ATS/job-board scraping, structured scoring, local web UI, n8n orchestration, and practical AI/workflow thinking.

## Privacy And Local-First Design

- No cloud database.
- No third-party Python packages.
- No API keys required.
- Local archive and generated digest are ignored by Git.
- Discovery source configuration is public and conservative.
- `data/search_profile.md` is committed only as generic sample search parameters.
- `data/candidate_profile.md` is local/private and ignored by Git.
- `data/candidate_profile.example.md` is the committed safe template for a local Candidate Profile / Resume Summary.
- Dashboard binds to `127.0.0.1`.
- Public repo should include code and public company configuration only.
- Job notes, hide state, and applied dates live only in the ignored local archive file.

## Roadmap / Planned Features

- Smarter scoring that can optionally use Profile tab search parameters.
- Recruiter CRM for contacts, outreach status, and follow-ups.
- AI-assisted summaries for top jobs while keeping raw data local.
- Company notes and watchlist health indicators.
- Interview tracking with dates, stages, notes, and next actions.

## Validation

Run:

```bash
python3 -m py_compile main.py web_ui.py digest.py storage.py utils.py validation.py fetchers/*.py scorers/*.py
python3 main.py test
python3 main.py discover
python3 main.py --json
python3 main.py digest
```
