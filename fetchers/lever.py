from __future__ import annotations

from utils import clean_text, safe_fetch_json, strip_html


def fetch_lever(company: dict) -> tuple[list[dict], list[str]]:
    # Lever exposes public postings as JSON:
    # https://api.lever.co/v0/postings/{company}?mode=json
    slug = company.get("ats_board") or company.get("slug")
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    data, error = safe_fetch_json(url)
    if error:
        return [], [f"{company['company_name']}: {error}"]

    jobs = []
    for item in data or []:
        categories = item.get("categories") or {}
        location = clean_text(categories.get("location") or item.get("workplaceType") or "")
        description = " ".join(
            strip_html(section.get("content"))
            for section in item.get("lists", [])
            if isinstance(section, dict)
        )
        description = description or strip_html(item.get("descriptionPlain") or item.get("description"))
        jobs.append(
            {
                "company": company["company_name"],
                "title": clean_text(item.get("text")),
                "location": location,
                "remote": "remote" in f"{location} {categories.get('commitment', '')}".lower(),
                "url": item.get("hostedUrl") or item.get("applyUrl") or "",
                "external_id": item.get("id") or "",
                "date_posted": item.get("createdAt") or "",
                "ats_source": "lever",
                "raw_description": description,
            }
        )
    return jobs, []
