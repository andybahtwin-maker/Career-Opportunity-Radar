# n8n Runner Notes

## Terminal Command

Run the scanner locally with JSON output:

```bash
cd /path/to/career_opportunity_radar && python3 main.py --json
```

`--json` now runs both the curated company watchlist and the configured broader discovery sources in `data/discovery_sources.json`.

Safe local test command, no network required:

```bash
cd /path/to/career_opportunity_radar && python3 main.py test
```

## n8n Command

Use an n8n Execute Command node with:

```bash
cd /path/to/career_opportunity_radar && /usr/bin/python3 main.py --json
```

The command prints one JSON object to stdout. n8n can parse that stdout and use:

- `run_timestamp`
- `total_jobs_scanned`
- `jobs_accepted`
- `jobs_rejected`
- `top_opportunities`
- `warnings`
- `errors`
- `output_files`

The JSON payload also includes separate `company_watchlist` and `discovery` summary objects so scheduled runs can distinguish curated-company results from broader discovery results.

## Required Environment Variables

None.

This project uses only Python standard library modules and local JSON files. It does need outbound internet access when running `--json`, `scan`, or `validate` because it checks public career pages and ATS APIs. It also needs outbound internet access for discovery sources when running `--json` or `discover`.

## Input Files

- `data/companies.json`: editable public company watchlist.
- `data/discovery_sources.json`: editable public discovery sources. These should be public pages, feeds, or JSON endpoints only. LinkedIn is intentionally not scraped.
- `data/jobs_archive.json`: local job archive loaded before each scan.

## Output Files

- `data/jobs_archive.json`: updated normalized job archive.
- `output/daily_digest.md`: human-readable daily digest.
- stdout from `python3 main.py --json`: n8n-friendly run summary and top opportunities.

## Applied Checkbox Workflow

Each job in `output/daily_digest.md` includes an applied checkbox:

```markdown
- [ ] Applied
```

After you apply to a job, manually change the checkbox to:

```markdown
- [x] Applied
```

Then sync those checked boxes back to the archive:

```bash
cd /path/to/career_opportunity_radar && python3 main.py sync-applied
```

The sync is one-way and conservative: checked digest boxes set matching archive jobs to `applied=true`, matched by URL first. Unchecked boxes do not clear existing applied status. Future digest generations preserve applied jobs as applied in `data/jobs_archive.json`.

## Local Web UI

For browser-based local review, run:

```bash
cd /path/to/career_opportunity_radar && python3 main.py serve
```

Then open:

```text
http://127.0.0.1:8787
```

The dashboard is local-only and writes Applied toggle changes directly to `data/jobs_archive.json`. See `README_UI.md` for details.

## Troubleshooting

If n8n cannot find Python, use the full Python path:

```bash
/usr/bin/python3
```

If `total_jobs_scanned` is `0`, check `warnings` and run:

```bash
cd /path/to/career_opportunity_radar && python3 main.py validate
```

If warnings mention `403`, `429`, blocked, or rate-limited, the target careers site is probably rejecting automated requests. The scanner will continue with other companies.

If warnings mention `404` or stale boards, edit the affected company in:

```text
data/companies.json
```

If n8n receives non-JSON output, make sure it is running:

```bash
python3 main.py --json
```

The older commands `scan`, `digest`, `list`, `test`, and `validate` intentionally print human-readable text.
