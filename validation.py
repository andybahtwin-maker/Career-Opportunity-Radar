from __future__ import annotations

from fetchers import FETCHERS
from utils import probe_url


def ats_probe_url(company: dict) -> str:
    ats_type = company.get("ats_type", "generic").lower()
    board = company.get("ats_board") or company.get("slug") or ""
    if ats_type == "greenhouse":
        return f"https://api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    if ats_type == "lever":
        return f"https://api.lever.co/v0/postings/{board}?mode=json"
    if ats_type == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{board}"
    if ats_type == "workable":
        return f"https://apply.workable.com/api/v1/widget/accounts/{board}?details=true"
    return company.get("careers_url", "")


def validate_companies(companies: list[dict]) -> list[dict]:
    results = []
    for company in companies:
        ats_type = company.get("ats_type", "generic").lower()
        fetcher = FETCHERS.get(ats_type)
        probe = probe_url(ats_probe_url(company))
        jobs = []
        fetch_errors = []

        if fetcher:
            jobs, fetch_errors = fetcher(company)
        else:
            fetch_errors = [f"unsupported ATS type: {ats_type}"]

        status = classify(company, probe, jobs, fetch_errors)
        results.append(
            {
                "company_name": company.get("company_name", ""),
                "category": company.get("category", ""),
                "priority": company.get("priority", 0),
                "ats_type": ats_type,
                "probe_url": probe["url"],
                "http_status": probe["status"],
                "jobs_found": len(jobs),
                "status": status,
                "anti_bot_likely": probe["anti_bot_likely"],
                "errors": fetch_errors or ([probe["error"]] if probe["error"] else []),
            }
        )
    return results


def classify(company: dict, probe: dict, jobs: list[dict], errors: list[str]) -> str:
    ats_type = company.get("ats_type", "generic").lower()
    if probe["anti_bot_likely"]:
        return "blocked_or_rate_limited"
    if probe["status"] == 404:
        return "broken_or_stale_config"
    if errors and not jobs:
        return "fetch_failed"
    if jobs:
        return "working"
    if ats_type == "generic" and probe["ok"]:
        return "reachable_no_parseable_jobs"
    if probe["ok"]:
        return "reachable_zero_jobs"
    return "unknown_failure"

