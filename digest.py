from __future__ import annotations

import textwrap

from config import DAILY_DIGEST_FILE, DIGEST_MAX_JOBS, DIGEST_MIN_SCORE
from storage import add_description_fields, dedupe_title_company, load_archive
from utils import posting_age_days, today_iso


def top_digest_jobs() -> list[dict]:
    archive = load_archive()
    for job in archive:
        add_description_fields(job)
    jobs = [
        job
        for job in archive
        if not job.get("ignored")
        and not job.get("applied")
        and job.get("fit_score", 0) >= DIGEST_MIN_SCORE
        and digest_eligible(job)
    ]
    jobs = dedupe_title_company(jobs)
    jobs.sort(key=lambda item: item.get("fit_score", 0), reverse=True)
    return jobs[:DIGEST_MAX_JOBS]


TARGET_TITLE_TERMS = (
    "account executive",
    "account manager",
    "construction success manager",
    "customer success manager",
    "director of customer success",
    "engagement manager",
    "implementation",
    "sales engineer",
    "solution engineer",
    "solutions engineer",
    "solution consultant",
    "solutions consultant",
    "strategic account executive",
    "technical account manager",
)

EXCLUDED_DIGEST_TITLE_TERMS = (
    "backend",
    "demand generation",
    "devops",
    "engineer, 3d",
    "marketing",
    "procurement",
    "product manager",
    "product operations",
    "product support",
    "sales development",
    "sdr",
    "security",
    "social media",
    "software engineer",
)

US_FRIENDLY_LOCATION_TERMS = (
    "remote",
    "united states",
    "usa",
    "denver",
    "austin",
    "boston",
    "chicago",
    "dallas",
    "fort worth",
    "houston",
    "los angeles",
    "new york",
    "raleigh",
    "san francisco",
)

NON_US_LOCATION_TERMS = (
    "australia",
    "austria",
    "belgium",
    "canada",
    "copenhagen",
    "emea",
    "france",
    "germany",
    "india",
    "london",
    "malmö",
    "netherlands",
    "pakistan",
    "pune",
    "singapore",
    "sweden",
    "switzerland",
    "sydney",
    "toronto",
    "uk",
    "vienna",
)


def digest_eligible(job: dict) -> bool:
    title = str(job.get("title", "")).lower()
    location = str(job.get("location", "")).lower()
    if any(term in title for term in EXCLUDED_DIGEST_TITLE_TERMS):
        return False
    if not any(term in title for term in TARGET_TITLE_TERMS):
        return False
    if any(term in location for term in NON_US_LOCATION_TERMS) and not any(
        term in location for term in ("united states", "usa")
    ):
        return False
    return not location or any(term in location for term in US_FRIENDLY_LOCATION_TERMS)


def write_digest(path=DAILY_DIGEST_FILE) -> tuple[str, list[dict]]:
    jobs = top_digest_jobs()
    lines = [f"# Career Opportunity Radar - {today_iso()}", ""]

    if not jobs:
        lines.append("No high-signal matches found today.")
    else:
        for index, job in enumerate(jobs, start=1):
            age = posting_age_days(job.get("date_posted"), job.get("first_seen"))
            age_text = "unknown age" if age is None else f"{age} days old"
            why = ", ".join(match_reasons(job)) or "matched scoring rules"
            url = job.get("url", "")
            description_lines = []
            if job.get("description_excerpt"):
                wrapped = textwrap.wrap(job.get("description_excerpt", ""), width=100)[:4]
                description_lines = ["- Description:"] + [f"  {line}" for line in wrapped]
            lines.extend(
                [
                    f"## {index}. {job.get('company')} - {job.get('title')}",
                    "",
                    f"- Score: {job.get('fit_score')}",
                    f"- Category: {job.get('company_category') or 'Not categorized'}",
                    f"- Location: {job.get('location') or 'Not listed'}",
                    f"- Posting age: {age_text}",
                    f"- Why it matched: {why}",
                    f"- Job posting: [Apply / view description]({url})",
                    f"- Raw URL: {url}",
                    f"- [{'x' if job.get('applied') else ' '}] Applied",
                    *description_lines,
                    "",
                ]
            )

    content = "\n".join(lines).rstrip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return content, jobs


def match_reasons(job: dict) -> list[str]:
    tags = " ".join(job.get("tags", [])).lower()
    reasons = []
    category = job.get("company_category")
    if category:
        reasons.append(category.replace("_", " "))
    if any(term in tags for term in ("construction", "contractor", "aec")):
        reasons.append("construction/AEC domain")
    if any(term in tags for term in ("field operations", "workflow")):
        reasons.append("operations workflow")
    if any(term in tags for term in ("technical demos", "demo", "presentations")):
        reasons.append("technical demos/presentations")
    if any(term in tags for term in ("customer-facing", "customer facing", "customer success")):
        reasons.append("customer-facing")
    if any(term in tags for term in ("remote", "hybrid", "denver")):
        reasons.append("remote/hybrid/Denver-friendly")
    if any(term in tags for term in ("account executive", "sales engineer", "solutions consultant", "implementation")):
        reasons.append("target role family")
    return dedupe(reasons)[:6]


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
