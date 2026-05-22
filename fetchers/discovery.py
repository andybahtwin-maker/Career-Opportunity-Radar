from __future__ import annotations

from urllib.parse import quote_plus

from config import DISCOVERY_SOURCES_FILE
from targeting import discovery_keywords, discovery_locations
from utils import clean_text, load_json, safe_fetch_json, strip_html


def load_discovery_sources(path=DISCOVERY_SOURCES_FILE) -> list[dict]:
    return load_json(path, [])


def fetch_discovery_sources(sources: list[dict] | None = None) -> tuple[list[dict], list[str]]:
    configured_sources = sources if sources is not None else load_discovery_sources()
    jobs = []
    errors = []

    for source in configured_sources:
        if not source.get("enabled", True):
            continue
        source_type = str(source.get("source_type", "")).lower()
        if source_type == "himalayas_api":
            source_jobs, source_errors = fetch_keyword_source(source, parse_himalayas_jobs)
        elif source_type == "remotejobs_api":
            source_jobs, source_errors = fetch_keyword_source(source, parse_remotejobs_jobs)
        else:
            source_jobs = []
            source_errors = [f"{source.get('name', 'Unnamed source')}: unsupported discovery source type {source_type}"]
        jobs.extend(source_jobs)
        errors.extend(source_errors)

    return dedupe_discovered_jobs(jobs), errors


def fetch_keyword_source(source: dict, parser) -> tuple[list[dict], list[str]]:
    name = source.get("name", "Unnamed source")
    template = source.get("search_url_template") or ""
    keywords = source.get("keywords") or [""]
    if source.get("use_profile_keywords", True):
        keywords = dedupe([*discovery_keywords(), *keywords])
    location_terms = source.get("location_terms") or [""]
    if source.get("use_profile_locations", True):
        location_terms = dedupe([*discovery_locations(), *location_terms])
    limit = int(source.get("max_results_per_keyword") or 20)

    jobs = []
    errors = []
    seen_urls = set()
    for keyword in keywords:
        for location in location_terms:
            url = build_search_url(template, keyword, location, limit)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            data, error = safe_fetch_json(url)
            if error:
                errors.append(f"{name}: {keyword or 'all jobs'} in {location or 'anywhere'}: {error}")
                continue
            jobs.extend(parser(data, source, keyword, location))
    return jobs, errors


def build_search_url(template: str, keyword: str, location: str, limit: int) -> str:
    return template.format(
        keyword=quote_plus(keyword),
        keyword_raw=keyword,
        location=quote_plus(location),
        location_raw=location,
        limit=limit,
    )


def parse_himalayas_jobs(data, source: dict, keyword: str, location: str) -> list[dict]:
    items = extract_items(data, ("jobs", "data", "results"))
    jobs = []
    source_name = source.get("name", "Himalayas")
    for item in items:
        if not isinstance(item, dict):
            continue
        company = clean_text(item.get("companyName") or item.get("company") or "")
        title = clean_text(item.get("title") or "")
        url = item.get("applicationLink") or item.get("url") or item.get("jobUrl") or ""
        description = strip_html(item.get("description") or item.get("excerpt") or "")
        location_text = location_from_himalayas(item)
        if "denver" in keyword.lower() and "denver" not in location_text.lower():
            location_text = f"Denver / {location_text}"
        if not title or not company or not url:
            continue
        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location_text,
                "remote": is_remote_location(location_text),
                "url": url,
                "external_id": str(item.get("guid") or url),
                "date_posted": item.get("pubDate") or "",
                "ats_source": "discovery:himalayas",
                "source_kind": "discovery",
                "source_name": source_name,
                "discovery_keyword": keyword,
                "raw_description": description,
            }
        )
    return jobs


def location_from_himalayas(item: dict) -> str:
    restrictions = item.get("locationRestrictions") or []
    timezones = item.get("timezoneRestriction") or []
    parts = []
    if restrictions:
        parts.append(", ".join(clean_text(value) for value in restrictions if value))
    if timezones:
        parts.append("Timezone " + ", ".join(clean_text(value) for value in timezones if value))
    return "; ".join(part for part in parts if part) or "Remote"


def parse_remotejobs_jobs(data, source: dict, keyword: str, location: str) -> list[dict]:
    items = extract_items(data, ("data", "jobs", "results"))
    jobs = []
    source_name = source.get("name", "RemoteJobs.org")
    for item in items:
        if not isinstance(item, dict):
            continue
        company_info = item.get("company") or {}
        company = clean_text(company_info.get("name") if isinstance(company_info, dict) else company_info)
        title = clean_text(item.get("title") or "")
        url = item.get("apply_url") or item.get("url") or ""
        description = strip_html(item.get("description") or "")
        location_text = clean_text(item.get("location") or location or "Remote")
        if "denver" in keyword.lower() and "denver" not in location_text.lower():
            location_text = f"Denver / {location_text}"
        if not title or not company or not url:
            continue
        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location_text,
                "remote": is_remote_location(location_text),
                "url": url,
                "external_id": str(item.get("id") or url),
                "date_posted": item.get("posted_at") or "",
                "ats_source": "discovery:remotejobs",
                "source_kind": "discovery",
                "source_name": source_name,
                "discovery_keyword": keyword,
                "raw_description": description,
            }
        )
    return jobs


def is_remote_location(location_text: str) -> bool:
    return "remote" in str(location_text or "").lower()


def extract_items(data, keys: tuple[str, ...]) -> list:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def dedupe_discovered_jobs(jobs: list[dict]) -> list[dict]:
    seen_urls = set()
    seen_title_company = set()
    result = []
    for job in jobs:
        url = str(job.get("url") or "").strip().lower()
        title_company = (
            str(job.get("company") or "").strip().lower(),
            str(job.get("title") or "").strip().lower(),
        )
        if url and url in seen_urls:
            continue
        if title_company in seen_title_company:
            continue
        if url:
            seen_urls.add(url)
        seen_title_company.add(title_company)
        result.append(job)
    return result


def dedupe(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        value = str(value or "").strip()
        if not value or value.lower() in seen:
            continue
        seen.add(value.lower())
        result.append(value)
    return result
