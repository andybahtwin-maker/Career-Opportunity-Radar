from __future__ import annotations

from utils import clean_text, safe_fetch_json, strip_html


def fetch_greenhouse(company: dict) -> tuple[list[dict], list[str]]:
    # Greenhouse exposes a simple public JSON board API:
    # https://api.greenhouse.io/v1/boards/{board}/jobs?content=true
    board = company.get("ats_board") or company.get("slug")
    url = f"https://api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    data, error = safe_fetch_json(url)
    if error:
        return [], [f"{company['company_name']}: {error}"]

    jobs = []
    for item in data.get("jobs", []):
        location = clean_text((item.get("location") or {}).get("name"))
        jobs.append(
            {
                "company": company["company_name"],
                "title": clean_text(item.get("title")),
                "location": location,
                "remote": "remote" in location.lower(),
                "url": item.get("absolute_url") or "",
                "external_id": str(item.get("id") or ""),
                "date_posted": item.get("updated_at") or "",
                "ats_source": "greenhouse",
                "raw_description": strip_html(item.get("content")),
            }
        )
    return jobs, []
