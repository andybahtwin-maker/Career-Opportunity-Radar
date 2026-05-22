#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from config import COMPANIES_FILE, DAILY_DIGEST_FILE, DIGEST_MIN_SCORE, DISCOVERY_SOURCES_FILE, JOBS_ARCHIVE_FILE
from digest import digest_eligible, match_reasons, top_digest_jobs, write_digest
from fetchers import FETCHERS
from fetchers.discovery import fetch_discovery_sources, load_discovery_sources
from realism import evaluate_job
from scorers import score_job
from targeting import discovery_keywords, is_hard_excluded, is_local_or_localizable, job_text, matching_required_positive_count, profile_hash
from storage import (
    add_description_fields,
    enrich_job_descriptions,
    job_identity,
    load_archive,
    load_companies,
    merge_jobs,
    normalized_title_company,
    rescore_jobs,
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
            job["source_kind"] = "company_watchlist"
            job["source_name"] = company.get("company_name", "")
            company_context = " ".join(
                str(company.get(key, ""))
                for key in ("category", "notes", "careers_url")
            )
            if not str(job.get("location") or "").strip() and any(
                term in company_context.lower()
                for term in ("denver", "colorado", "co.", "colorado-based", "colorado ")
            ):
                job["location"] = "Denver / Colorado"
            if company.get("notes"):
                job["raw_description"] = f"{job.get('raw_description', '')} {company.get('notes', '')}".strip()
        fetched_jobs.extend(jobs)
        errors.extend(fetch_errors)

    total_fetched = len(fetched_jobs)
    _, description_warnings = enrich_job_descriptions(fetched_jobs)
    errors.extend(description_warnings)
    fetched_jobs, filter_warnings = hard_filter_fetched_jobs(fetched_jobs, "company_watchlist")
    errors.extend(filter_warnings)

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
        "jobs_fetched": total_fetched,
        "jobs_accepted": len(accepted_jobs),
        "jobs_rejected": max(total_fetched - len(accepted_jobs), 0),
        "new_jobs_added": new_count,
        "archive_size": len(merged),
        "warnings": errors,
    }


def run_discovery() -> dict:
    sources = [source for source in load_discovery_sources() if source.get("enabled", True)]
    archive = load_archive()
    fetched_jobs, errors = fetch_discovery_sources(sources)
    total_fetched = len(fetched_jobs)

    _, description_warnings = enrich_job_descriptions(fetched_jobs)
    errors.extend(description_warnings)
    fetched_jobs, filter_warnings = hard_filter_fetched_jobs(fetched_jobs, "discovery")
    errors.extend(filter_warnings)

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
        "sources_checked": len(sources),
        "target_profile_hash": profile_hash(),
        "profile_query_keywords": discovery_keywords(),
        "jobs_fetched": total_fetched,
        "jobs_accepted": len(accepted_jobs),
        "jobs_rejected": max(total_fetched - len(accepted_jobs), 0),
        "new_jobs_added": new_count,
        "archive_size": len(merged),
        "warnings": errors,
    }


def hard_filter_fetched_jobs(jobs: list[dict], label: str) -> tuple[list[dict], list[str]]:
    kept = []
    rejected = {
        "hard_excluded": 0,
        "vehicle_barrier": 0,
        "commission_only_risk": 0,
        "not_local": 0,
        "weak_required_signals": 0,
        "low_realism": 0,
    }
    for job in jobs:
        realism = evaluate_job(job)
        if realism["vehicle_barrier"]:
            rejected["vehicle_barrier"] = rejected.get("vehicle_barrier", 0) + 1
            continue
        if realism["commission_only_risk"]:
            rejected["commission_only_risk"] = rejected.get("commission_only_risk", 0) + 1
            continue
        hard_excluded, _ = is_hard_excluded(job)
        if hard_excluded:
            rejected["hard_excluded"] += 1
            continue
        if realism["practical_fit"] in {"Semantic Match Only", "Likely ATS Reject", "Not a Fit"}:
            rejected["low_realism"] += 1
            continue
        local_fit_labels = {
            "Strong Construction/Design Sales Fit",
            "Strong Local Fit",
            "Realistic Local Sales Fit",
            "Realistic Local Design/Technical Fit",
            "Strong Construction Tech Fit",
            "Remote Physical-Industry Stretch",
            "Side-Cash Contractor",
        }
        if not is_local_or_localizable(job) and not realism["side_cash_signal"] and not realism["physical_industry_software_signal"]:
            rejected["not_local"] += 1
            continue
        if matching_required_positive_count(job_text(job)) < 1 and realism["practical_fit_label"] not in local_fit_labels:
            rejected["weak_required_signals"] += 1
            continue
        kept.append(job)
    warnings = [
        f"{label}: hard filter rejected {count} jobs for {reason.replace('_', ' ')}"
        for reason, count in rejected.items()
        if count
    ]
    return kept, warnings


def run_radar_pipeline() -> dict:
    errors = []
    scan_result: dict = {}
    discovery_result: dict = {}
    digest_jobs: list[dict] = []

    try:
        scan_result = run_scan()
    except Exception as exc:
        errors.append(f"company_watchlist: {exc}")

    try:
        discovery_result = run_discovery()
    except Exception as exc:
        errors.append(f"discovery: {exc}")

    try:
        write_digest()
        digest_jobs = top_digest_jobs()
    except Exception as exc:
        errors.append(f"digest: {exc}")

    warnings = scan_result.get("warnings", []) + discovery_result.get("warnings", [])
    total_jobs_scanned = scan_result.get("jobs_fetched", 0) + discovery_result.get("jobs_fetched", 0)
    jobs_accepted = scan_result.get("jobs_accepted", 0) + discovery_result.get("jobs_accepted", 0)
    jobs_rejected = scan_result.get("jobs_rejected", 0) + discovery_result.get("jobs_rejected", 0)

    return {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_jobs_scanned": total_jobs_scanned,
        "company_watchlist": scan_result,
        "discovery": discovery_result,
        "jobs_accepted": jobs_accepted,
        "jobs_rejected": jobs_rejected,
        "top_opportunities": [json_job(job) for job in digest_jobs],
        "warnings": warnings,
        "errors": errors,
        "output_files": {
            "jobs_archive": str(JOBS_ARCHIVE_FILE),
            "daily_digest": str(DAILY_DIGEST_FILE),
        },
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


def discover() -> int:
    result = run_discovery()
    print(f"Discovery sources checked: {result['sources_checked']}")
    print(f"Jobs fetched: {result['jobs_fetched']}")
    print(f"New jobs added: {result['new_jobs_added']}")
    print(f"Archive size: {result['archive_size']}")
    print(f"Wrote: {JOBS_ARCHIVE_FILE}")
    if result["warnings"]:
        print("Discovery warnings:")
        for error in result["warnings"][:20]:
            print(f"  - {error}")
    return 0


def json_run() -> int:
    payload = run_radar_pipeline()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if payload["errors"] else 0


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
        "practical_fit": job.get("practical_fit", ""),
        "practical_fit_label": job.get("practical_fit_label") or job.get("practical_fit", ""),
        "domain_barrier": job.get("domain_barrier", ""),
        "transferability_score": job.get("transferability_score", 0),
        "hireability_score": job.get("hireability_score", 0),
        "vehicle_barrier": bool(job.get("vehicle_barrier")),
        "commission_only_risk": bool(job.get("commission_only_risk")),
        "base_pay_signal": bool(job.get("base_pay_signal")),
        "vehicle_support_signal": bool(job.get("vehicle_support_signal")),
        "denver_metro_signal": bool(job.get("denver_metro_signal")),
        "localizable_signal": bool(job.get("localizable_signal")),
        "remote_only_signal": bool(job.get("remote_only_signal")),
        "remote_saas_signal": bool(job.get("remote_saas_signal")),
        "physical_industry_software_signal": bool(job.get("physical_industry_software_signal")),
        "side_cash_signal": bool(job.get("side_cash_signal")),
        "realism_notes": job.get("realism_notes", []),
        "category": job.get("company_category") or "Not categorized",
        "source": source_label(job),
        "applied_date": job.get("applied_date", ""),
        "why_it_matched": match_reasons(job) or ["matched scoring rules"],
    }


def source_label(job: dict) -> str:
    if job.get("source_kind") == "discovery":
        return f"Discovery source: {job.get('source_name') or job.get('ats_source') or 'Unknown'}"
    return "Curated company watchlist"


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
    jobs = rescore_jobs(jobs)
    save_archive(jobs)

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
    print("  python main.py discover")
    print("  python main.py digest")
    print("  python main.py enrich")
    print("  python main.py sync-applied")
    print("  python main.py serve")
    print("  python main.py list")
    print("  python main.py test")
    print("  python main.py validate")
    print("")
    print(f"Companies: {COMPANIES_FILE}")
    print(f"Discovery: {DISCOVERY_SOURCES_FILE}")
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
    if command == "discover":
        return discover()
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
