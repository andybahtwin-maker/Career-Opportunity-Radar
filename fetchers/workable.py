from __future__ import annotations

from utils import clean_text, safe_fetch_json, strip_html


def fetch_workable(company: dict) -> tuple[list[dict], list[str]]:
    # Workable's embeddable widget endpoint is public for many accounts:
    # https://apply.workable.com/api/v1/widget/accounts/{account}?details=true
    account = company.get("ats_board") or company.get("slug")
    url = f"https://apply.workable.com/api/v1/widget/accounts/{account}?details=true"
    data, error = safe_fetch_json(url)
    if error:
        return [], [f"{company['company_name']}: {error}"]

    jobs = []
    for item in data.get("jobs", []):
        location_info = item.get("location") or {}
        if isinstance(location_info, dict):
            location = clean_text(location_info.get("location_str") or location_info.get("city") or "")
        else:
            location = clean_text(str(location_info))
        jobs.append(
            {
                "company": company["company_name"],
                "title": clean_text(item.get("title")),
                "location": location,
                "remote": bool(item.get("remote")) or "remote" in location.lower(),
                "url": item.get("url") or item.get("application_url") or "",
                "external_id": item.get("shortcode") or item.get("id") or "",
                "date_posted": item.get("published") or "",
                "ats_source": "workable",
                "raw_description": strip_html(item.get("description") or ""),
            }
        )
    return jobs, []
