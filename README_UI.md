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
- Profile: edits search parameters stored in `data/search_profile.md`.

The Profile tab is informational in this version. Scoring still uses `scorers/rules.py`.

`data/search_profile.md` is committed as a generic public sample. Do not add private resume content to it before publishing.

The job cards link directly to the original ATS or company job posting. No applications are submitted automatically.

Optional Linux desktop launchers can be created to open the dashboard or start the server first. Keep those launcher files local unless their paths are generalized for your machine.

Stop the dashboard with `Ctrl+C` in the terminal where it is running.
