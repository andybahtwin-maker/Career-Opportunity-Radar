# Career Opportunity Radar

Career Opportunity Radar is a local-first Python tool that monitors selected company career pages, scores relevant roles, and produces a small daily digest of high-signal job opportunities.

It is built for targeted review, not mass application spam. It does not auto-apply, send messages, or scrape private accounts. It reads public ATS/company job pages, stores a local archive, and gives you a concise workflow for deciding what is worth opening.

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

## How It Works

1. `data/companies.json` defines the public company watchlist and ATS configuration.
2. Fetchers collect public job postings and descriptions.
3. `storage.py` merges jobs into `data/jobs_archive.json`.
4. `scorers/rules.py` assigns a fit score and match tags.
5. `digest.py` writes `output/daily_digest.md`.
6. `web_ui.py` serves a local dashboard at `http://127.0.0.1:8787`.

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

The dashboard shows top digest jobs as cards with company, title, location, score, category, posting age, match reasons, description excerpt, and a direct link to the job posting.

The Applied toggle writes immediately to `data/jobs_archive.json`. Applied jobs are visually muted and remain preserved in the archive.

The server binds to `127.0.0.1` only. It is intended for local personal use, not internet exposure.

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

## Screenshots

Dashboard screenshot placeholder:

```text
screenshots/dashboard.png
```

## Portfolio Angle

This project demonstrates Python automation, ATS/job-board scraping, structured scoring, local web UI, n8n orchestration, and practical AI/workflow thinking.

## Privacy And Local-First Design

- No cloud database.
- No third-party Python packages.
- No API keys required.
- Local archive and generated digest are ignored by Git.
- Dashboard binds to `127.0.0.1`.
- Public repo should include code and public company configuration only.

## Validation

Run:

```bash
python3 -m py_compile main.py web_ui.py digest.py storage.py
python3 main.py test
python3 main.py digest
```
