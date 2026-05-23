from __future__ import annotations

import re

from config import COMPANIES_FILE, DAILY_DIGEST_FILE, JOBS_ARCHIVE_FILE
from realism import evaluate_job
from scorers import score_job
from targeting import profile_hash
from utils import extract_readable_text, load_json, safe_fetch_text, save_json, stable_job_id, strip_html, today_iso


DESCRIPTION_EXCERPT_CHARS = 800
APPLIED_CHECKBOX_RE = re.compile(r"(?im)^\s*-\s*(?:\[[xX]\]\s*Applied|Applied:\s*\[[xX]\])\b")
SECTION_RE = re.compile(r"(?ms)^##\s+.*?(?=^##\s+|\Z)")
URL_RE = re.compile(
    r"(?im)^\s*-\s*(?:URL|Raw URL):\s*(\S+)\s*$|^\s*-\s*Job posting:\s*\[[^\]]+\]\(([^)]+)\)\s*$"
)


def normalized_title_company(job: dict) -> str:
    title = re.sub(r"[^a-z0-9]+", " ", job.get("title", "").lower()).strip()
    company = re.sub(r"[^a-z0-9]+", " ", job.get("company", "").lower()).strip()
    return f"{company}|{title}"


def job_identity(job: dict) -> str:
    external_id = str(job.get("external_id") or "").strip()
    if external_id:
        return stable_job_id(job.get("company", ""), job.get("title", ""), external_id)
    return stable_job_id(job.get("company", ""), job.get("title", ""), job.get("url", ""))


def load_companies() -> list[dict]:
    return load_json(COMPANIES_FILE, [])


def load_archive() -> list[dict]:
    return load_json(JOBS_ARCHIVE_FILE, [])


def save_archive(jobs: list[dict]) -> None:
    save_json(JOBS_ARCHIVE_FILE, jobs)


def rescore_jobs(jobs: list[dict]) -> list[dict]:
    fingerprint = profile_hash()
    rescored = []
    for job in jobs:
        add_description_fields(job)
        score, tags = score_job(job)
        realism = evaluate_job(job)
        job["fit_score"] = score
        job["tags"] = tags
        job["domain_barrier"] = realism["domain_barrier"]
        job["domain_matches"] = realism["domain_matches"]
        job["transferability_score"] = realism["transferability_score"]
        job["hireability_score"] = realism["hireability_score"]
        job["practical_fit"] = realism["practical_fit"]
        job["practical_fit_label"] = realism["practical_fit_label"]
        job["vehicle_barrier"] = realism["vehicle_barrier"]
        job["commission_only_risk"] = realism["commission_only_risk"]
        job["base_pay_signal"] = realism["base_pay_signal"]
        job["vehicle_support_signal"] = realism["vehicle_support_signal"]
        job["license_required_signal"] = realism["license_required_signal"]
        job["driving_record_signal"] = realism["driving_record_signal"]
        job["travel_supported_signal"] = realism["travel_supported_signal"]
        job["heavy_travel_signal"] = realism["heavy_travel_signal"]
        job["denver_metro_signal"] = realism["denver_metro_signal"]
        job["localizable_signal"] = realism["localizable_signal"]
        job["remote_only_signal"] = realism["remote_only_signal"]
        job["remote_saas_signal"] = realism["remote_saas_signal"]
        job["physical_industry_software_signal"] = realism["physical_industry_software_signal"]
        job["side_cash_signal"] = realism["side_cash_signal"]
        job["non_denver_territory_signal"] = realism["non_denver_territory_signal"]
        job["seniority_stretch_signal"] = realism["seniority_stretch_signal"]
        job["stale_posting_signal"] = realism["stale_posting_signal"]
        job["fit_warnings"] = realism["fit_warnings"]
        job["practical_fit_rank"] = realism["practical_fit_rank"]
        job["realism_notes"] = realism["realism_notes"]
        job["target_profile_hash"] = fingerprint
        rescored.append(job)
    return sorted(rescored, key=job_rank_key)


def job_rank_key(job: dict) -> tuple[int, int]:
    return int(job.get("practical_fit_rank", 5)), -int(job.get("fit_score", 0))


def job_matches_reference(job: dict, job_id: str = "", url: str = "") -> bool:
    return bool(
        (job_id and job.get("id") == job_id)
        or (url and job.get("url") == url)
    )


def update_archive_job(job_id: str = "", url: str = "", updates: dict | None = None) -> bool:
    jobs = load_archive()
    changed = False
    updates = updates or {}
    for job in jobs:
        if not job_matches_reference(job, job_id=job_id, url=url):
            continue
        job.update(updates)
        changed = True
        break
    if changed:
        save_archive(jobs)
    return changed


def sync_applied_from_digest(
    digest_path=DAILY_DIGEST_FILE,
    archive_path=JOBS_ARCHIVE_FILE,
) -> dict:
    digest_content = digest_path.read_text(encoding="utf-8") if digest_path.exists() else ""
    jobs = load_json(archive_path, [])
    jobs_by_url = {job.get("url"): job for job in jobs if job.get("url")}

    checked_urls = []
    unmatched_checked_urls = []
    updated_count = 0

    for section in SECTION_RE.findall(digest_content):
        if not APPLIED_CHECKBOX_RE.search(section):
            continue
        url_match = URL_RE.search(section)
        if not url_match:
            unmatched_checked_urls.append("")
            continue

        url = (url_match.group(1) or url_match.group(2)).strip()
        checked_urls.append(url)
        job = jobs_by_url.get(url)
        if not job:
            unmatched_checked_urls.append(url)
            continue
        if not job.get("applied"):
            job["applied"] = True
            if not str(job.get("applied_date") or "").strip():
                job["applied_date"] = today_iso()
            updated_count += 1

    save_json(archive_path, jobs)
    return {
        "checked_jobs_found": len(checked_urls),
        "archive_jobs_updated": updated_count,
        "unmatched_checked_urls": unmatched_checked_urls,
    }


def clean_description(value: str | None) -> str:
    return strip_html(value or "")


def add_description_fields(job: dict) -> dict:
    description = clean_description(job.get("raw_description"))
    job["raw_description"] = description
    job["description_excerpt"] = description[:DESCRIPTION_EXCERPT_CHARS].strip()
    job["description_word_count"] = len(re.findall(r"\b[\w'-]+\b", description))
    job["has_description"] = bool(description)
    return job


def enrich_job_descriptions(jobs: list[dict]) -> tuple[int, list[str]]:
    enriched_count = 0
    warnings = []
    for job in jobs:
        add_description_fields(job)
        if job.get("has_description") or not job.get("url"):
            continue

        html, error = safe_fetch_text(job.get("url", ""))
        label = f"{job.get('company', '')} - {job.get('title', '')}".strip(" -")
        if error:
            warnings.append(f"{label}: description fetch failed: {error}")
            continue

        description = extract_readable_text(html)
        if not description:
            warnings.append(f"{label}: description fetch returned no readable text")
            continue

        job["raw_description"] = description
        add_description_fields(job)
        enriched_count += 1
    return enriched_count, warnings


def merge_jobs(existing_jobs: list[dict], fetched_jobs: list[dict]) -> tuple[list[dict], int]:
    by_id = {}
    by_url = {}
    by_title_company = {}
    for job in existing_jobs:
        add_description_fields(job)
        job_id = job.get("id") or job_identity(job)
        job["id"] = job_id
        job.setdefault("source_kind", "company_watchlist")
        job.setdefault("source_name", job.get("company", ""))
        by_id[job_id] = job
        if job.get("url"):
            by_url[job.get("url")] = job_id
        by_title_company[normalized_title_company(job)] = job_id

    new_count = 0
    today = today_iso()
    for job in fetched_jobs:
        job_id = job_identity(job)
        title_company_key = normalized_title_company(job)
        existing_id = by_url.get(job.get("url")) if job.get("url") else None
        if not existing_id:
            existing_id = by_title_company.get(title_company_key)
        if existing_id:
            job_id = existing_id

        raw_description = clean_description(job.get("raw_description"))
        score, tags = score_job({**job, "first_seen": today, "raw_description": raw_description})
        normalized = {
            "id": job_id,
            "company": job.get("company", ""),
            "company_category": job.get("company_category", ""),
            "company_priority": job.get("company_priority", 0),
            "title": job.get("title", ""),
            "location": job.get("location", ""),
            "remote": bool(job.get("remote")),
            "url": job.get("url", ""),
            "external_id": job.get("external_id", ""),
            "date_posted": job.get("date_posted", ""),
            "first_seen": today,
            "last_seen": today,
            "ats_source": job.get("ats_source", ""),
            "source_kind": job.get("source_kind", "company_watchlist"),
            "source_name": job.get("source_name") or job.get("company", ""),
            "raw_description": raw_description,
            "fit_score": score,
            "tags": tags,
            "domain_barrier": "",
            "domain_matches": [],
            "transferability_score": 0,
            "hireability_score": 0,
            "practical_fit": "",
            "practical_fit_label": "",
            "vehicle_barrier": False,
            "commission_only_risk": False,
            "base_pay_signal": False,
            "vehicle_support_signal": False,
            "license_required_signal": False,
            "driving_record_signal": False,
            "travel_supported_signal": False,
            "heavy_travel_signal": False,
            "denver_metro_signal": False,
            "localizable_signal": False,
            "remote_only_signal": False,
            "remote_saas_signal": False,
            "physical_industry_software_signal": False,
            "side_cash_signal": False,
            "non_denver_territory_signal": False,
            "seniority_stretch_signal": False,
            "stale_posting_signal": False,
            "fit_warnings": [],
            "practical_fit_rank": 5,
            "realism_notes": [],
            "target_profile_hash": profile_hash(),
            "ignored": False,
            "applied": False,
        }

        if job_id in by_id:
            previous = by_id[job_id]
            if not normalized["raw_description"] and previous.get("raw_description"):
                normalized["raw_description"] = clean_description(previous.get("raw_description"))
            normalized["first_seen"] = previous.get("first_seen") or today
            normalized["ignored"] = bool(previous.get("ignored", False))
            normalized["applied"] = bool(previous.get("applied", False))
            normalized["notes"] = previous.get("notes", "")
            normalized["applied_date"] = previous.get("applied_date", "")
        else:
            new_count += 1

        add_description_fields(normalized)
        score, tags = score_job(normalized)
        normalized["fit_score"] = score
        normalized["tags"] = tags

        by_id[job_id] = normalized
        if normalized.get("url"):
            by_url[normalized.get("url")] = job_id
        by_title_company[title_company_key] = job_id

    return rescore_jobs(list(by_id.values())), new_count


def dedupe_title_company(jobs: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for job in jobs:
        key = (job.get("company", "").lower(), job.get("title", "").lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(job)
    return result
