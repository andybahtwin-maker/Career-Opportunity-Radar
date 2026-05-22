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
- Profile: edits Search Parameters stored in `data/search_profile.md` and a private Candidate Profile / Resume Summary stored in `data/candidate_profile.md`, includes a `Run Radar Now` button, and notes that broader discovery sources are configured in `data/discovery_sources.json`.

Job descriptions are collapsed by default to keep the radar easy to scan. Use the Show more / Show less control on each card to expand or collapse the full excerpt inline without leaving the page.

The Profile tab separates search intent from candidate evidence. Search Parameters describe target roles and domains and control discovery query expansion, hard filtering, and scoring. Candidate Profile / Resume Summary describes background, constraints, and proof points. Search Parameters are the human-readable targeting strategy; rules and practical-fit classification live in `scorers/rules.py`, `realism.py`, and `targeting.py`. Discovery source endpoints live in `data/discovery_sources.json`.

The Jobs / Radar page groups practical fits so local and realistic roles surface before secondary physical-industry software, paid side-cash contractor work, and generic remote SaaS stretches. Practical-fit labels include `Strong Local Fit`, `Strong Construction/Design Sales Fit`, `Realistic Local Sales Fit`, `Realistic Local Design/Technical Fit`, `Strong Construction Tech Fit`, `Remote Physical-Industry Stretch`, `Side-Cash Contractor`, `Realistic Stretch`, `Remote Stretch`, `Semantic Match Only`, `Likely ATS Reject`, `Vehicle Barrier`, `Commission-Only Risk`, and `Not a Fit`.

Ranking prioritizes Denver metro and local/hybrid construction, interiors, showroom, design-sales, building-materials, contractor-facing, customer-workflow, stable-pay, and vehicle/reimbursement feasibility signals. Remote software roles tied to construction, AEC, homebuilding, field operations, contractor workflow, facilities, manufacturing, geospatial, or reality capture remain visible as secondary fits; generic remote SaaS or enterprise stretch roles are labeled and downgraded.

The `Run Radar Now` button saves the current Search Parameters and Candidate Profile, reruns the local radar pipeline, refreshes `data/jobs_archive.json`, regenerates `output/daily_digest.md`, and shows a status message on the Profile tab.

`data/search_profile.md` and `data/candidate_profile.md` are the local dashboard profile files. `data/candidate_profile.md` is local/private and ignored by Git. `data/candidate_profile.example.md` is the committed safe template for that private file. `data/search_profile.md` is committed as a generic public sample; do not add private resume content to it before publishing.

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
