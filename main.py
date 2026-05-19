#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from config import COMPANIES_FILE, DAILY_DIGEST_FILE, DIGEST_MIN_SCORE, JOBS_ARCHIVE_FILE
from digest import digest_eligible, match_reasons, top_digest_jobs, write_digest
from fetchers import FETCHERS
from scorers import score_job
from storage import (
    add_description_fields,
    enrich_job_descriptions,
    job_identity,
    load_archive,
    load_companies,
    merge_jobs,
    normalized_title_company,
    save_archive,
    sync_applied_from_digest,
)
from utils import stable_job_id, today_iso
from validation import validate_companies


def run_scan() -> dict:
    companies = [company for company in load_companies() if company.get("enabled", True)]
    archive = load_archive()
    fetched_jobs = []
    errors = []

    for company in companies:
        ats_type = company.get("ats_type", "generic").lower()
        fetcher = FETCHERS.get(ats_type)
        if not fetcher:
            errors.append(f"{company.get('company_name')}: unsupported ATS type {ats_type}")
            continue
        jobs, fetch_errors = fetcher(company)
        for job in jobs:
            job["company_category"] = company.get("category", "")
            job["company_priority"] = company.get("priority", 0)
        fetched_jobs.extend(jobs)
        errors.extend(fetch_errors)

    _, description_warnings = enrich_job_descriptions(fetched_jobs)
    errors.extend(description_warnings)

    merged, new_count = merge_jobs(archive, fetched_jobs)
    save_archive(merged)

    fetched_ids = {job_identity(job) for job in fetched_jobs}
    fetched_title_company = {normalized_title_company(job) for job in fetched_jobs}
    accepted_jobs = [
        job
        for job in merged
        if not job.get("ignored")
        and not job.get("applied")
        and (
            job.get("id") in fetched_ids
            or normalized_title_company(job) in fetched_title_company
        )
        and job.get("fit_score", 0) >= DIGEST_MIN_SCORE
        and digest_eligible(job)
    ]

    return {
        "companies_checked": len(companies),
        "jobs_fetched": len(fetched_jobs),
        "jobs_accepted": len(accepted_jobs),
        "jobs_rejected": max(len(fetched_jobs) - len(accepted_jobs), 0),
        "new_jobs_added": new_count,
        "archive_size": len(merged),
        "warnings": errors,
    }


def scan() -> int:
    result = run_scan()
    print(f"Companies checked: {result['companies_checked']}")
    print(f"Jobs fetched: {result['jobs_fetched']}")
    print(f"New jobs added: {result['new_jobs_added']}")
    print(f"Archive size: {result['archive_size']}")
    print(f"Wrote: {JOBS_ARCHIVE_FILE}")
    if result["warnings"]:
        print("Fetch warnings:")
        for error in result["warnings"][:20]:
            print(f"  - {error}")
    return 0


def json_run() -> int:
    errors = []
    scan_result = {}
    digest_jobs = []

    try:
        scan_result = run_scan()
        write_digest()
        digest_jobs = top_digest_jobs()
    except Exception as exc:
        errors.append(str(exc))

    payload = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_jobs_scanned": scan_result.get("jobs_fetched", 0),
        "jobs_accepted": scan_result.get("jobs_accepted", 0),
        "jobs_rejected": scan_result.get("jobs_rejected", 0),
        "top_opportunities": [json_job(job) for job in digest_jobs],
        "warnings": scan_result.get("warnings", []),
        "errors": errors,
        "output_files": {
            "jobs_archive": str(JOBS_ARCHIVE_FILE),
            "daily_digest": str(DAILY_DIGEST_FILE),
        },
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if errors else 0


def json_job(job: dict) -> dict:
    return {
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "url": job.get("url", ""),
        "description_excerpt": job.get("description_excerpt", ""),
        "description_word_count": job.get("description_word_count", 0),
        "has_description": bool(job.get("has_description")),
        "score": job.get("fit_score", 0),
        "category": job.get("company_category") or "Not categorized",
        "why_it_matched": match_reasons(job) or ["matched scoring rules"],
    }


def validate() -> int:
    companies = [company for company in load_companies() if company.get("enabled", True)]
    results = validate_companies(companies)
    working = [item for item in results if item["status"] == "working"]
    broken = [item for item in results if item["status"] in {"broken_or_stale_config", "blocked_or_rate_limited", "fetch_failed"}]

    print(f"Companies validated: {len(results)}")
    print(f"Working companies: {len(working)}")
    print(f"Broken/blocked companies: {len(broken)}")
    print("")
    for item in results:
        status = item["http_status"] if item["http_status"] is not None else "no_status"
        print(
            f"{item['status']:<28} {status!s:<9} "
            f"{item['jobs_found']:>3} jobs  {item['company_name']} ({item['ats_type']})"
        )
        if item["errors"] and item["status"] != "working":
            print(f"    {item['errors'][0]}")
    return 0


def digest() -> int:
    content, jobs = write_digest()
    print(f"Wrote: {DAILY_DIGEST_FILE}")
    print(f"Digest jobs: {len(jobs)}")
    print("")
    print(content)
    return 0


def enrich() -> int:
    jobs = load_archive()
    enriched_count, warnings = enrich_job_descriptions(jobs)
    for job in jobs:
        add_description_fields(job)
        score, tags = score_job(job)
        job["fit_score"] = score
        job["tags"] = tags
    save_archive(sorted(jobs, key=lambda item: item.get("fit_score", 0), reverse=True))

    print(f"Archive jobs checked: {len(jobs)}")
    print(f"Descriptions enriched: {enriched_count}")
    print(f"Wrote: {JOBS_ARCHIVE_FILE}")
    if warnings:
        print("Enrichment warnings:")
        for warning in warnings[:20]:
            print(f"  - {warning}")
    return 0


def sync_applied() -> int:
    result = sync_applied_from_digest()
    print(f"Checked jobs found: {result['checked_jobs_found']}")
    print(f"Archive jobs updated: {result['archive_jobs_updated']}")
    print("Unmatched checked URLs:")
    if result["unmatched_checked_urls"]:
        for url in result["unmatched_checked_urls"]:
            print(f"  - {url or '(missing URL)'}")
    else:
        print("  - none")
    return 0


def serve() -> int:
    from web_ui import run_server

    run_server()
    return 0


def list_jobs() -> int:
    jobs = load_archive()
    if not jobs:
        print("No jobs in archive yet. Run: python main.py scan")
        return 0
    for job in sorted(jobs, key=lambda item: item.get("fit_score", 0), reverse=True):
        status = []
        if job.get("ignored"):
            status.append("ignored")
        if job.get("applied"):
            status.append("applied")
        suffix = f" [{' / '.join(status)}]" if status else ""
        print(f"{job.get('fit_score', 0):>3}  {job.get('company')} - {job.get('title')}{suffix}")
        print(f"     {job.get('location') or 'No location'} | {job.get('url')}")
    return 0


def test() -> int:
    sample_jobs = [
        {
            "company": "Propeller Aero",
            "title": "Account Executive, Construction",
            "location": "Remote - Denver",
            "remote": True,
            "url": "https://example.com/propeller-ae",
            "date_posted": today_iso(),
            "first_seen": today_iso(),
            "ats_source": "test",
            "raw_description": "Customer-facing role with technical demos, presentations, construction workflows, mapping, and field operations.",
        },
        {
            "company": "NoiseCo",
            "title": "Insurance Sales Representative",
            "location": "Denver",
            "remote": False,
            "url": "https://example.com/noise",
            "date_posted": today_iso(),
            "first_seen": today_iso(),
            "ats_source": "test",
            "raw_description": "Commission only door-to-door canvassing. Own vehicle required.",
        },
    ]
    for job in sample_jobs:
        job["id"] = stable_job_id(job["company"], job["title"], job["url"])
        score, tags = score_job(job)
        print(f"{job['company']} - {job['title']}")
        print(f"  score: {score}")
        print(f"  tags: {', '.join(tags)}")

    if sample_jobs[0]["title"] and score_job(sample_jobs[0])[0] <= score_job(sample_jobs[1])[0]:
        print("Test failed: high-fit sample did not outrank noise sample")
        return 1

    print("Test passed.")
    return 0


def usage() -> int:
    print("Usage:")
    print("  python main.py --json")
    print("  python main.py scan")
    print("  python main.py digest")
    print("  python main.py enrich")
    print("  python main.py sync-applied")
    print("  python main.py serve")
    print("  python main.py list")
    print("  python main.py test")
    print("  python main.py validate")
    print("")
    print(f"Companies: {COMPANIES_FILE}")
    print(f"Archive:   {JOBS_ARCHIVE_FILE}")
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return usage()
    command = argv[1].lower()
    if command == "--json":
        return json_run()
    if command == "scan":
        return scan()
    if command == "digest":
        return digest()
    if command == "enrich":
        return enrich()
    if command == "sync-applied":
        return sync_applied()
    if command == "serve":
        return serve()
    if command == "list":
        return list_jobs()
    if command == "test":
        return test()
    if command == "validate":
        return validate()
    return usage()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
