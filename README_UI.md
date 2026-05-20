# Local Web UI

Launch the local dashboard:

```bash
cd /path/to/career_opportunity_radar && python3 main.py serve
```

Open the Jobs / Radar tab:

```text
http://127.0.0.1:8787/jobs
```

Open the Profile tab:

```text
http://127.0.0.1:8787/profile
```

The server binds only to `127.0.0.1` for local personal use. It does not require npm, React, a database, cloud hosting, or any non-standard Python dependency.

The dashboard has two tabs:

- Jobs / Radar: reads jobs from `data/jobs_archive.json`. Each job card has an Applied toggle. Clicking the toggle immediately updates that job's `applied` value in `data/jobs_archive.json`, then reloads the dashboard.
- Profile: edits search parameters stored in `data/search_profile.md`, includes a `Run Radar Now` button, and notes that broader discovery sources are configured in `data/discovery_sources.json`.

Job descriptions are collapsed by default to keep the radar easy to scan. Use the Show more / Show less control on each card to expand or collapse the full excerpt inline without leaving the page.

The Profile tab documents search intent used by the local scoring/filtering rules. Scoring still uses `scorers/rules.py`; discovery source keywords live in `data/discovery_sources.json`.

The `Run Radar Now` button saves the current search parameters, reruns the local radar pipeline, refreshes `data/jobs_archive.json`, regenerates `output/daily_digest.md`, and shows a status message on the Profile tab.

`data/search_profile.md` is committed as a generic public sample. Do not add private resume content to it before publishing.

The job cards label whether each role came from the curated company watchlist or a broader discovery source, and they link directly to the original ATS, company, or public job-board posting. Each card also includes local notes, hide/unhide controls, and applied-date tracking. No applications are submitted automatically. The UI uses only local Python, HTML, CSS, and lightweight vanilla JavaScript.

The notes, hidden state, applied flag, and applied date are all saved in `data/jobs_archive.json`. That file is ignored by Git and is treated as local run state.

Broader discovery can be run separately:

```bash
python3 main.py discover
```

The normal JSON automation command runs both curated company monitoring and configured public discovery sources:

```bash
python3 main.py --json
```

LinkedIn is intentionally not scraped. Discovery sources should be public pages, feeds, or JSON endpoints that work without authentication and without bypassing login walls or anti-bot systems.

Optional Linux desktop launchers can be created to open the dashboard or start the server first. Keep those launcher files local unless their paths are generalized for your machine.

Stop the dashboard with `Ctrl+C` in the terminal where it is running.
