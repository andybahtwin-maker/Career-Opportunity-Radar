from __future__ import annotations

import re
from urllib.parse import urljoin

from utils import clean_text, safe_fetch_text, strip_html
from targeting import job_page_rejection_reasons, likely_job_posting


JOB_LINK_RE = re.compile(
    r'<a[^>]+href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<label>.{0,220}?)</a>',
    re.IGNORECASE | re.DOTALL,
)

ROLE_WORDS = (
    "account executive",
    "account manager",
    "analyst",
    "architectural products",
    "architectural representative",
    "architectural sales",
    "building materials",
    "builder sales",
    "cabinet designer",
    "cad designer",
    "cad drafter",
    "commercial interiors",
    "commercial market sales",
    "contractor sales",
    "countertop",
    "customer success manager",
    "customer experience",
    "customer support",
    "design consultant",
    "design sales",
    "estimator",
    "flooring",
    "field technician",
    "glazing",
    "inside sales",
    "implementation consultant",
    "implementation specialist",
    "kitchen",
    "preconstruction",
    "market representative",
    "millwork",
    "project coordinator",
    "sales consultant",
    "sales engineer",
    "sales estimator",
    "showroom",
    "slab sales",
    "solution consultant",
    "solutions consultant",
    "solutions engineer",
    "specification sales",
    "specifier sales",
    "stone sales",
    "surface sales",
    "territory sales",
    "technical account manager",
    "technical designer",
    "technical sales",
    "tile",
    "trade sales",
    "trade representative",
    "window",
)

JOB_URL_HINTS = (
    "/job/",
    "/jobs/",
    "jobid=",
    "gh_jid=",
    "apply",
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "paycomonline.net",
    "smartrecruiters.com",
)

NOISY_URL_PARTS = (
    "/about/",
    "/case-studies/",
    "/contact",
    "/trial",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    "/jobs/search",
)

NOISY_LABELS = {
    "careers",
    "job opportunities",
    "meet our teams",
    "products",
    "see all jobs",
    "see assignar in action",
    "skip to content",
    "text link",
    "view open positions",
    "win more. build more.",
}


def fetch_generic(company: dict) -> tuple[list[dict], list[str]]:
    # Generic mode is deliberately conservative. It parses ordinary links from
    # a careers page and keeps only links that look like specific job posts.
    # This avoids turning marketing/navigation links into fake jobs.
    url = company.get("careers_url") or ""
    html, error = safe_fetch_text(url)
    if error:
        return [], [f"{company['company_name']}: {error}"]

    jobs = []
    rejected_reasons: dict[str, int] = {}
    seen = set()
    for match in JOB_LINK_RE.finditer(html):
        label = strip_html(match.group("label"))
        href = urljoin(url, match.group("href"))
        label_lower = label.lower()
        href_lower = href.lower()
        if not label or label_lower in NOISY_LABELS:
            continue
        if href.endswith("#") or "#" in href:
            continue
        if any(part in href_lower for part in NOISY_URL_PARTS):
            continue
        has_role_label = any(word in label_lower for word in ROLE_WORDS)
        has_job_url = any(word in href_lower for word in JOB_URL_HINTS)
        nearby = clean_text(html[max(0, match.start() - 500) : match.end() + 500])
        candidate = {
            "company": company["company_name"],
            "title": label,
            "location": "",
            "remote": "remote" in nearby.lower(),
            "url": href,
            "external_id": href,
            "date_posted": "",
            "ats_source": "generic",
            "raw_description": nearby,
        }
        candidate_reasons = job_page_rejection_reasons(candidate)
        if candidate_reasons:
            for reason in candidate_reasons:
                rejected_reasons[reason] = rejected_reasons.get(reason, 0) + 1
            continue
        if not has_role_label and not has_job_url and not likely_job_posting(candidate):
            continue
        if len(label) < 6 or len(label) > 120 or href in seen:
            continue
        seen.add(href)
        if not likely_job_posting(candidate):
            continue
        jobs.append(candidate)
    warnings = [
        f"{company['company_name']}: generic rejected {count} pages for {reason.replace('_', ' ')}"
        for reason, count in sorted(rejected_reasons.items())
    ]
    return jobs, warnings
