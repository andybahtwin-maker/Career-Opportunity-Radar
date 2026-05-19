# Career Opportunity Radar
Career Opportunity Radar is a local-first Python tool that monitors selected company career pages, scores relevant roles, and produces a small daily digest of high-signal job opportunities.

It is built for targeted review, not mass application spam. It does not auto-apply, send messages, or scrape private accounts. It reads public ATS/company job pages, stores a local archive, and gives you a concise workflow for deciding what is worth opening.


**Jobs / Radar dashboard**
<img width="1908" height="1536" alt="radar-screenshot-20260519-141950" src="https://github.com/user-attachments/assets/ac33a215-91a4-4a27-b63b-7997a979dd7e" />


**Profile tab for editable search parameters**
<img width="1918" height="1404" alt="radar-screenshot-20260519-142016" src="https://github.com/user-attachments/assets/38906b3a-b351-4bc7-a2d8-b6d7c0a0e09c" />






## Why I Built It

Most job boards are noisy. I wanted a practical system that could watch a curated company list, preserve job history, surface strong matches, and make it easy to review opportunities from a browser or Markdown digest.

The project is intentionally simple: Python standard library, local JSON files, transparent scoring rules, and optional n8n scheduling.

## What It Does

- Scans public career pages and ATS job-board endpoints.
- Supports Lever, Greenhouse, Ashby, Workable, and conservative generic page parsing.
- Stores normalized job records locally.
- Pulls job descriptions when available and extracts readable page text as a fallback.
- Scores jobs with transparent keyword/rule-based logic.
- Writes a Markdown digest with clickable company/ATS links.
- Serves a local web dashboard for reviewing top opportunities.
- Lets you mark jobs as applied from the dashboard or Markdown workflow.
- Keeps job links direct to the original ATS or company application page.
- Can be launched from Linux desktop shortcuts for local use.

## Recent Updates

- Profile tab for editing local search parameters.
- Editable `data/search_profile.md` sample profile.
- Expandable job descriptions for a cleaner Jobs / Radar dashboard.

## How It Works

1. `data/companies.json` defines the public company watchlist and ATS configuration.
2. `data/search_profile.md` stores editable, generic search parameters for the local Profile tab.
3. Fetchers collect public job postings and descriptions.
4. `storage.py` merges jobs into `data/jobs_archive.json`.
5. `scorers/rules.py` assigns a fit score and match tags.
6. `digest.py` writes `output/daily_digest.md`.
7. `web_ui.py` serves a local dashboard at `http://127.0.0.1:8787`.

The archive and output files are intentionally ignored by Git because they are local run state.

## Setup

Requires Python 3. No third-party Python packages are required.

```bash
git clone <your-repo-url>
cd career_opportunity_radar
python3 main.py test
```

Review and edit the public company watchlist:

```bash
data/companies.json
```

Initialize your local archive by running a scan:

```bash
python3 main.py --json
```

This creates ignored local run-state files such as `data/jobs_archive.json` and `output/daily_digest.md`.

## GitHub Setup

This repository is intended to keep source code, public company configuration, and generic sample search parameters in Git while excluding local run state.

Before publishing your own fork or copy, confirm `.gitignore` excludes:

- `data/jobs_archive.json`
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
python3 main.py list
python3 main.py validate
python3 main.py sync-applied
python3 main.py enrich
```

## Local Dashboard

The local dashboard has two tabs:

- Jobs / Radar: top digest jobs as cards with company, title, location, score, category, posting age, match reasons, collapsed/expandable description excerpts, and a direct link to the job posting.
- Profile: editable local search parameters stored in `data/search_profile.md`.

The Applied toggle writes immediately to `data/jobs_archive.json`. Applied jobs are visually muted and remain preserved in the archive.

Job descriptions start collapsed for easier scanning. A lightweight inline vanilla JavaScript toggle expands or collapses the full excerpt without reloading the page.

The Profile tab is informational in the current version. Scoring still uses the static rules in `scorers/rules.py`.

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
- why it matched
- a direct Markdown link to the company/ATS posting
- raw URL for automation/sync
- applied checkbox
- short description excerpt

After manually checking applied boxes in the digest, run:

```bash
python3 main.py sync-applied
```

This sync is conservative: checked boxes mark archive jobs as applied, but unchecked boxes do not clear existing applied status.

## n8n Scheduled Automation

This project can be scheduled from an n8n Execute Command node:

```bash
cd /path/to/career_opportunity_radar && /usr/bin/python3 main.py --json
```

The command prints one JSON object with run metadata, warnings, errors, and `top_opportunities`. n8n can use that JSON for notifications, logging, or routing.

## No Auto-Apply Spam

Career Opportunity Radar is a review aid. It does not submit applications, generate cover letters, message recruiters, or perform automated browser actions. Every application decision remains manual.

## Configuration

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

## Scoring

Scoring is rule-based and transparent. Positive signals include target role families, construction/AEC terms, reality-capture terms, customer-facing language, remote/Denver-friendly locations, and fresh postings. Negative signals suppress common mismatches such as SDR, commission-only, door-to-door, insurance sales, and unrelated technical roles.

Tune scoring in:

```text
scorers/rules.py
```

The editable profile text lives in:

```text
data/search_profile.md
```

The committed file contains generic/public sample parameters. Do not put private resume content in this file if you plan to publish the repository.

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
- `data/search_profile.md` is committed only as generic sample search parameters.
- Dashboard binds to `127.0.0.1`.
- Public repo should include code and public company configuration only.

## Roadmap / Planned Features

- Editable master resume stored locally and excluded from public Git history.
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
python3 main.py digest
```
