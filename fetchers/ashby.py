from __future__ import annotations

from utils import clean_text, safe_fetch_json, strip_html


def fetch_ashby(company: dict) -> tuple[list[dict], list[str]]:
    # Ashby exposes public job-board JSON:
    # https://api.ashbyhq.com/posting-api/job-board/{company}
    board = company.get("ats_board") or company.get("slug")
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
    data, error = safe_fetch_json(url)
    if error:
        return [], [f"{company['company_name']}: {error}"]

    jobs = []
    for item in data.get("jobs", []):
        location = clean_text(item.get("location") or "")
        job_url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{board}/{item.get('id', '')}"
        jobs.append(
            {
                "company": company["company_name"],
                "title": clean_text(item.get("title")),
                "location": location,
                "remote": "remote" in location.lower(),
                "url": job_url,
                "external_id": item.get("id") or "",
                "date_posted": item.get("publishedAt") or "",
                "ats_source": "ashby",
                "raw_description": strip_html(item.get("descriptionHtml") or item.get("descriptionPlain")),
            }
        )
    return jobs, []
