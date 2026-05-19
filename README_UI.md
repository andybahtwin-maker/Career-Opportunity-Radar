# Local Web UI

Launch the local dashboard:

```bash
cd /path/to/career_opportunity_radar && python3 main.py serve
```

Open:

```text
http://127.0.0.1:8787
```

The server binds only to `127.0.0.1` for local personal use. It does not require npm, React, a database, cloud hosting, or any non-standard Python dependency.

The dashboard reads jobs from `data/jobs_archive.json`. Each job card has an Applied toggle. Clicking the toggle immediately updates that job's `applied` value in `data/jobs_archive.json`, then reloads the dashboard.

Stop the dashboard with `Ctrl+C` in the terminal where it is running.
