from __future__ import annotations

import textwrap

from config import DAILY_DIGEST_FILE, DIGEST_MAX_JOBS, DIGEST_MIN_SCORE
from storage import add_description_fields, dedupe_title_company, job_rank_key, load_archive, rescore_jobs
from targeting import is_hard_excluded, is_local_or_localizable, job_text, matching_required_positive_count
from utils import posting_age_days, today_iso


def top_digest_jobs() -> list[dict]:
    archive = rescore_jobs(load_archive())
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
    jobs = diversify_jobs(dedupe_title_company(jobs))
    return jobs[:DIGEST_MAX_JOBS]


TARGET_TITLE_TERMS = (
    "account manager",
    "architectural products sales",
    "building materials sales",
    "commercial market sales representative",
    "cabinet designer",
    "client success manager",
    "commercial interiors sales",
    "commercial sales representative",
    "contractor sales",
    "countertop sales",
    "design consultant",
    "design sales consultant",
    "cad designer",
    "cad drafter",
    "estimator",
    "flooring sales",
    "glass sales",
    "glazing sales",
    "inside sales",
    "kitchen and bath designer",
    "contractor sales",
    "customer success manager",
    "customer onboarding specialist",
    "field operations consultant",
    "ai evaluator",
    "ai trainer",
    "content evaluator",
    "domain expert",
    "implementation",
    "operations coordinator",
    "product specialist",
    "project consultant",
    "project coordinator",
    "sales representative",
    "sales consultant",
    "sales estimator",
    "sales domain expert",
    "showroom",
    "showroom consultant",
    "showroom sales consultant",
    "solar sales consultant",
    "solutions consultant",
    "territory sales representative",
    "tile sales",
    "trade sales representative",
    "trade representative",
    "market representative",
    "architectural representative",
    "a&d representative",
    "builder sales representative",
    "dealer sales representative",
    "specification sales",
    "specifier sales",
    "surface sales",
    "slab sales",
    "stone sales",
    "porcelain sales",
    "millwork sales",
    "technical designer",
    "drafting technician",
    "millwork designer",
    "commercial interiors designer",
    "window and door sales",
)

EXCLUDED_DIGEST_TITLE_TERMS = (
    "backend",
    "director",
    "demand generation",
    "devops",
    "enterprise",
    "enterprise account executive",
    "engineer, 3d",
    "marketing",
    "procurement",
    "product manager",
    "product operations",
    "product support",
    "sales development",
    "sdr",
    "security",
    "senior sales engineer",
    "social media",
    "software engineer",
    "strategic account executive",
    "vp",
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
    hard_excluded, _ = is_hard_excluded(job)
    if hard_excluded:
        return False
    if job.get("practical_fit") in {
        "Semantic Match Only",
        "Likely ATS Reject",
        "Not a Fit",
        "Vehicle Barrier",
        "Commission-Only Risk",
    }:
        return False
    if job.get("non_denver_territory_signal"):
        return False
    if any(term in title for term in EXCLUDED_DIGEST_TITLE_TERMS):
        return False
    if not any(term in title for term in TARGET_TITLE_TERMS):
        return False
    if not is_local_or_localizable(job) and not job.get("side_cash_signal") and not job.get("physical_industry_software_signal"):
        return False
    local_fit_labels = {
        "Strong Construction/Design Sales Fit",
        "Strong Local Fit",
        "Realistic Local Sales Fit",
        "Realistic Local Design/Technical Fit",
        "Strong Construction Tech Fit",
        "Remote Physical-Industry Stretch",
        "Side-Cash Contractor",
    }
    if matching_required_positive_count(job_text(job)) < 2 and job.get("practical_fit_label") not in local_fit_labels:
        return False
    if any(term in location for term in NON_US_LOCATION_TERMS) and not any(
        term in location for term in ("united states", "usa")
    ):
        return False
    return not location or any(term in location for term in US_FRIENDLY_LOCATION_TERMS)


def diversify_jobs(jobs: list[dict]) -> list[dict]:
    ranked = sorted(jobs, key=job_rank_key)
    selected = []
    company_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for job in ranked:
        company = str(job.get("company") or "").lower()
        source = str(job.get("source_kind") or job.get("source_name") or "").lower()
        if company_counts.get(company, 0) >= 1:
            continue
        if source == "company_watchlist" and source_counts.get(source, 0) >= 4:
            continue
        selected.append(job)
        company_counts[company] = company_counts.get(company, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) >= DIGEST_MAX_JOBS:
            return selected

    selected_ids = {job.get("id") for job in selected}
    for job in ranked:
        if job.get("id") in selected_ids:
            continue
        selected.append(job)
        if len(selected) >= DIGEST_MAX_JOBS:
            break
    return selected


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
                    f"- Practical fit: {job.get('practical_fit_label') or job.get('practical_fit') or 'Not classified'}",
                    f"- Warnings: {', '.join(job.get('fit_warnings') or []) or 'none'}",
                    f"- Domain barrier: {job.get('domain_barrier') or 'unknown'}",
                    f"- Transferability score: {job.get('transferability_score', 0)}",
                    f"- Hireability score: {job.get('hireability_score', 0)}",
                    f"- Vehicle barrier: {'yes' if job.get('vehicle_barrier') else 'no'}",
                    f"- Commission-only risk: {'yes' if job.get('commission_only_risk') else 'no'}",
                    f"- Base/stable pay signal: {'yes' if job.get('base_pay_signal') else 'no'}",
                    f"- Category: {job.get('company_category') or 'Not categorized'}",
                    f"- Source: {source_label(job)}",
                    f"- Location: {job.get('location') or 'Not listed'}",
                    f"- Posting age: {age_text}",
                    f"- Why it matched: {why}",
                    f"- Job posting: [Apply / view description]({url})",
                    f"- Raw URL: {url}",
                    f"- Applied: {'yes' if job.get('applied') else 'no'}",
                    f"- Applied date: {job.get('applied_date') or 'not set'}",
                    *description_lines,
                    "",
                ]
            )

    content = "\n".join(lines).rstrip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return content, jobs


def source_label(job: dict) -> str:
    if job.get("source_kind") == "discovery":
        return f"Discovery source: {job.get('source_name') or job.get('ats_source') or 'Unknown'}"
    return "Curated company watchlist"


def match_reasons(job: dict) -> list[str]:
    tags = " ".join(job.get("tags", [])).lower()
    reasons = []
    category = job.get("company_category")
    if category:
        reasons.append(category.replace("_", " "))
    if job.get("practical_fit_label") or job.get("practical_fit"):
        reasons.append(job.get("practical_fit_label") or job.get("practical_fit"))
    if job.get("domain_barrier"):
        reasons.append(f"{job.get('domain_barrier')} domain barrier")
    if not job.get("side_cash_signal") and any(term in tags for term in ("construction", "contractor", "aec")):
        reasons.append("construction/AEC domain")
    if any(term in tags for term in ("field operations", "workflow")):
        reasons.append("operations workflow")
    if any(term in tags for term in ("technical demos", "demo", "presentations")):
        reasons.append("technical demos/presentations")
    if any(term in tags for term in ("customer-facing", "customer facing", "customer success")):
        reasons.append("customer-facing")
    if job.get("denver_metro_signal") or any(term in tags for term in ("hybrid", "denver", "target metro")):
        reasons.append("local/Denver-friendly")
    if ("remote saas stretch" in tags or job.get("remote_saas_signal")) and not job.get("physical_industry_software_signal"):
        reasons.append("remote SaaS stretch")
    if job.get("physical_industry_software_signal"):
        reasons.append("physical-industry software")
    if job.get("side_cash_signal"):
        reasons.append("paid contractor lane")
    if job.get("base_pay_signal"):
        reasons.append("base/stable pay signal")
    for warning in job.get("fit_warnings", [])[:2]:
        reasons.append(warning)
    if any(term in tags for term in ("account executive", "sales engineer", "solutions consultant", "implementation")):
        reasons.append("target role family")
    for note in job.get("realism_notes", [])[:2]:
        reasons.append(note)
    return dedupe(reasons)[:6]


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
