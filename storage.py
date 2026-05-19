from __future__ import annotations

import re

from config import COMPANIES_FILE, DAILY_DIGEST_FILE, JOBS_ARCHIVE_FILE
from scorers import score_job
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
    by_title_company = {}
    for job in existing_jobs:
        add_description_fields(job)
        job_id = job.get("id") or job_identity(job)
        job["id"] = job_id
        by_id[job_id] = job
        by_title_company[normalized_title_company(job)] = job_id

    new_count = 0
    today = today_iso()
    for job in fetched_jobs:
        job_id = job_identity(job)
        title_company_key = normalized_title_company(job)
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
            "raw_description": raw_description,
            "fit_score": score,
            "tags": tags,
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
        else:
            new_count += 1

        add_description_fields(normalized)
        score, tags = score_job(normalized)
        normalized["fit_score"] = score
        normalized["tags"] = tags

        by_id[job_id] = normalized
        by_title_company[title_company_key] = job_id

    return sorted(by_id.values(), key=lambda item: item.get("fit_score", 0), reverse=True), new_count


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
