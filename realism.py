from __future__ import annotations

import re

from targeting import (
    contains_any,
    current_targeting,
    is_local_or_localizable,
    job_text,
    non_denver_territory_terms,
)


HIGH_BARRIER_DOMAINS = {
    "erp consulting": (
        "erp",
        "sap",
        "oracle cloud",
        "netsuite",
        "workday",
        "adaptive erp",
        "enterprise resource planning",
    ),
    "healthcare benefits consulting": (
        "healthcare benefits",
        "employee benefits",
        "benefits consultant",
        "health plan",
        "payer",
        "claims",
        "clinical",
        "medical billing",
        "medicare",
        "medicaid",
    ),
    "cybersecurity": (
        "cybersecurity",
        "cyber security",
        "security architecture",
        "infosec",
        "siem",
        "zero trust",
        "iam",
        "soc 2",
    ),
    "aerospace/defense technical programs": (
        "aerospace",
        "defense",
        "dod",
        "government programs",
        "clearance",
        "u.s. government",
        "us government",
        "systems engineering",
    ),
    "cloud architecture": (
        "cloud architecture",
        "solutions architect",
        "aws",
        "azure",
        "gcp",
        "kubernetes",
        "devops",
    ),
    "enterprise infrastructure": (
        "enterprise infrastructure",
        "networking",
        "data center",
        "database",
        "storage",
        "platform engineer",
        "remote access",
        "endpoint",
        "digital workplace",
        "it support",
    ),
    "finance SaaS": (
        "fintech",
        "banking",
        "lending",
        "financial services",
        "revenue cloud",
        "cpq",
        "billing platform",
    ),
    "enterprise procurement-heavy software": (
        "procurement",
        "sourcing platform",
        "supplier management",
        "rfp",
        "vendor management",
        "contract lifecycle",
    ),
}

MODERATE_BARRIER_DOMAINS = {
    "construction SaaS": ("construction saas", "aec", "construction software", "contractor software"),
    "contractor operations": ("contractor operations", "contractor workflow", "contractor-facing", "contractor facing", "homebuilding software"),
    "field operations software": ("field operations", "field service", "field-service operations", "dispatch", "work orders"),
    "facilities platforms": ("facilities", "facility operations", "maintenance operations"),
    "industrial operations": ("industrial operations", "industrial distribution", "commercial equipment"),
    "manufacturing operations": ("manufacturing operations", "manufacturing workflow", "supply chain operations"),
}

LOW_BARRIER_DOMAINS = {
    "building materials": ("building materials", "building products", "lumber", "millwork", "architectural millwork", "architectural products", "hardware", "fixtures", "lighting"),
    "commercial interiors": ("commercial interiors", "furniture dealer", "workplace interiors", "showroom"),
    "glass and glazing": ("glass", "glazing", "shower glass", "architectural glass"),
    "flooring and tile": ("flooring", "commercial flooring", "residential flooring", "tile", "carpet", "hardwood", "stone slab"),
    "cabinets and countertops": ("cabinet", "cabinetry", "countertop", "countertops", "solid surface", "quartz", "surface sales", "slab sales", "porcelain slab", "stone sales"),
    "windows and doors": ("windows and doors", "window and door", "replacement windows", "entry doors", "millwork"),
    "kitchen and bath": ("kitchen and bath", "kitchen design", "bath design", "bathroom design"),
    "home improvement": ("home improvement", "remodeling", "design-build", "in-home sales"),
    "project coordination": ("project coordinator", "project coordination", "project consultant"),
    "customer onboarding": ("customer onboarding", "onboarding specialist", "implementation support"),
    "contractor-facing sales": ("contractor sales", "contractor-facing", "contractor facing"),
    "operational account management": ("account manager", "territory manager", "territory sales"),
    "implementation support": ("implementation support", "implementation specialist", "training provided"),
}

STRONG_TRANSFER_TERMS = (
    "contractor workflows",
    "contractor workflow",
    "contractor-facing",
    "contractor facing",
    "construction",
    "design",
    "operational coordination",
    "operations coordinator",
    "consultative sales",
    "customer onboarding",
    "implementation support",
    "implementation specialist",
    "project-based communication",
    "project coordination",
    "showroom",
    "design consultant",
    "sales consultant",
    "kitchen",
    "bath",
    "flooring",
    "tile",
    "cabinet",
    "countertop",
    "window",
    "glass",
    "glazing",
    "home improvement",
    "in-home sales",
    "estimating",
    "estimator",
    "salesforce",
    "customer meetings",
    "field operations",
    "workflow",
    "process improvement",
    "building materials",
    "commercial interiors",
    "architectural products",
    "industrial distribution",
    "facilities operations",
    "design-build",
    "homebuilding",
    "geospatial",
    "drone",
    "reality capture",
    "manufacturing operations",
    "architects",
    "designers",
    "specifiers",
    "trade partners",
    "builders",
    "fabricators",
)

WEAK_TRANSFER_TERMS = (
    "erp implementation",
    "erp pre-sales",
    "erp presales",
    "healthcare systems",
    "cloud infrastructure",
    "aerospace engineering",
    "enterprise architecture",
    "technical pre-sales engineering",
    "solutions architect",
)

ATS_REJECT_TERMS = (
    "engineering degree required",
    "degree in engineering",
    "bachelor's degree in engineering",
    "bachelors degree in engineering",
    "math background",
    "degree in mathematics",
    "erp-specific experience",
    "erp experience required",
    "healthcare domain expertise",
    "healthcare experience required",
    "existing enterprise book",
    "enterprise book",
    "enterprise procurement",
    "rfp",
    "executive stakeholders",
    "c-suite",
    "highly technical",
    "certification required",
    "aws certified",
    "azure certification",
    "security clearance",
    "commission-only",
    "commission only",
    "door-to-door",
    "door to door",
    "insurance sales",
    "cdl",
    "warehouse-only",
    "installer-only",
    "laborer-only",
)

VEHICLE_BARRIER_TERMS = (
    "own vehicle required",
    "own car mandatory",
    "must have reliable vehicle",
    "reliable vehicle required",
    "personal vehicle",
    "use your own vehicle",
)

VEHICLE_MITIGATION_TERMS = (
    "company vehicle",
    "branded vehicle",
    "fleet vehicle",
    "vehicle provided",
    "company car",
    "mileage reimbursement",
    "mileage reimbursed",
    "travel reimbursement",
    "travel reimbursed",
    "car allowance",
)

COMMISSION_RISK_TERMS = (
    "commission only",
    "commission-only",
    "1099",
    "uncapped commission only",
)

BASE_PAY_TERMS = (
    "base salary",
    "base + bonus",
    "base and bonus",
    "base plus bonus",
    "base pay",
    "base compensation",
    "salary range",
    "hourly",
    "hourly + commission",
    "hourly plus commission",
    "plus commission",
    "commission eligible",
    "guaranteed",
    "paid training",
    "benefits",
    "$50",
    "$55",
    "$60",
    "$65",
    "$70",
)

STRONG_BASE_TERMS = (
    "$55",
    "$65",
    "$80",
    "55k base",
    "65k base",
    "80k base",
    "base salary of $55",
    "base salary of $65",
    "base salary of $80",
)

LOCAL_SALES_TITLE_TERMS = (
    "account manager",
    "architectural products sales",
    "building materials sales",
    "cabinet designer",
    "commercial sales representative",
    "commercial market sales representative",
    "contractor sales",
    "countertop sales",
    "design consultant",
    "design sales consultant",
    "estimator",
    "flooring sales",
    "glass sales",
    "glazing sales",
    "inside sales",
    "kitchen and bath designer",
    "project coordinator",
    "sales consultant",
    "sales estimator",
    "showroom",
    "territory sales",
    "tile sales",
    "trade sales",
    "trade representative",
    "market representative",
    "market sales representative",
    "a&d representative",
    "architectural representative",
    "builder sales representative",
    "dealer sales representative",
    "specification sales",
    "specifier sales",
    "architectural sales consultant",
    "surface sales",
    "slab sales",
    "stone sales",
    "porcelain sales",
    "millwork sales",
    "window and door sales",
)

LOCAL_TECHNICAL_DESIGN_TITLE_TERMS = (
    "cad designer",
    "solidworks designer",
    "technical designer",
    "drafting technician",
    "cad drafter",
    "millwork designer",
    "commercial interiors designer",
    "estimator cad",
    "design sales support",
    "sales engineer solidworks",
)

REALISTIC_REMOTE_TITLE_TERMS = (
    "customer onboarding",
    "customer success",
    "implementation",
    "mid-market",
    "onboarding",
    "smb",
)

REMOTE_SAAS_TERMS = (
    "b2b saas",
    "enterprise saas",
    "saas",
    "software platform",
    "software-as-a-service",
)

PHYSICAL_INDUSTRY_SOFTWARE_TERMS = (
    "aec technology",
    "construction saas",
    "construction software",
    "contractor software",
    "contractor workflow",
    "design-build",
    "field operations",
    "field operations software",
    "field-service software",
    "field-service operations",
    "facilities operations",
    "geospatial",
    "drone",
    "reality capture",
    "homebuilding",
    "homebuilding software",
    "jobsite",
    "building lifecycle",
    "architecture, engineering, and construction",
    "manufacturing operations",
)

PHYSICAL_SOFTWARE_DOMAIN_NAMES = {
    "construction SaaS",
    "contractor operations",
    "field operations software",
    "facilities platforms",
    "manufacturing operations",
}

SIDE_CASH_TERMS = (
    "ai evaluator",
    "ai trainer",
    "sales domain expert",
    "private investigator domain expert",
    "domain expert",
    "annotation",
    "content evaluator",
    "video annotation",
    "audio annotation",
    "image annotation",
)

PAID_PROJECT_TERMS = (
    "paid project",
    "hourly",
    "per hour",
    "/hr",
    "contractor",
    "freelance",
    "project-based",
)

SIDE_CASH_REJECT_TERMS = (
    "buy equipment",
    "purchase equipment",
    "upfront cost",
    "unpaid assessment",
    "unpaid test",
    "assessment longer than 30 minutes",
    "assessment takes 1 hour",
)

ENTERPRISE_SALES_TERMS = (
    "advisory",
    "director",
    "enterprise account executive",
    "enterprise customer success",
    "existing enterprise book",
    "fortune 500",
    "fortune-500",
    "gong",
    "head of",
    "large enterprise",
    "clari",
    "meddic",
    "principal",
    "senior strategic",
    "senior sales engineer",
    "strategic account executive",
    "vp",
)

SENIORITY_STRETCH_TITLE_TERMS = (
    "advisory",
    "director",
    "enterprise account executive",
    "enterprise customer success",
    "head of",
    "large enterprise",
    "principal",
    "senior sales engineer",
    "senior strategic",
    "strategic account executive",
    "vp",
)

FIVE_PLUS_SAAS_RE = re.compile(r"\b(?:5|6|7|8|9|10|11|12|13|14|15)\+?\s*(?:years|yrs)\b[^.]{0,80}\bsaas\b")
YEARS_REQUIRED_RE = re.compile(r"\b(?:7|8|9|10|11|12|13|14|15)\+?\s*(?:-|to)?\s*(?:\d+\s*)?years\b")


def evaluate_job(job: dict) -> dict:
    text = job_text(job)
    title = str(job.get("title") or "").lower()
    category = str(job.get("company_category") or "").replace("_", " ").lower()
    combined = f"{text} {category}"

    high_domains = matching_domains(combined, HIGH_BARRIER_DOMAINS)
    moderate_domains = matching_domains(combined, MODERATE_BARRIER_DOMAINS)
    low_domains = matching_domains(combined, LOW_BARRIER_DOMAINS)
    strong_transfer = contains_phrases(combined, STRONG_TRANSFER_TERMS)
    weak_transfer = contains_phrases(combined, WEAK_TRANSFER_TERMS)
    ats_barriers = contains_phrases(combined, ATS_REJECT_TERMS)
    vehicle_barriers = contains_phrases(combined, VEHICLE_BARRIER_TERMS)
    vehicle_mitigations = contains_phrases(combined, VEHICLE_MITIGATION_TERMS)
    commission_risks = contains_phrases(combined, COMMISSION_RISK_TERMS)
    base_pay_signals = contains_phrases(combined, BASE_PAY_TERMS) or bool(re.search(r"\$\s?(?:5[0-9]|6[0-9]|7[0-9]|8[0-9])(?:[,k]\d{0,3})?", combined))
    strong_base_signals = contains_phrases(combined, STRONG_BASE_TERMS)
    targeting = current_targeting()
    territory_conflicts = non_denver_territory_terms(job)
    denver_matches = contains_any(str(job.get("location") or "").lower(), targeting["locations_strong"])
    local_work_patterns = contains_any(combined, targeting["locations_moderate"])
    remote_job = bool(job.get("remote")) or "remote" in str(job.get("location") or "").lower()
    localizable = is_local_or_localizable(job)
    metro_local = bool(denver_matches) or "colorado" in str(job.get("location") or "").lower()
    remote_only = remote_job and not metro_local and not local_work_patterns
    remote_saas = remote_job and not metro_local and bool(contains_phrases(combined, REMOTE_SAAS_TERMS))
    physical_software_terms = contains_phrases(combined, PHYSICAL_INDUSTRY_SOFTWARE_TERMS)
    software_words = contains_phrases(combined, ("saas", "software", "platform", "technology"))
    physical_software_domains = [
        domain
        for domain in moderate_domains
        if domain in PHYSICAL_SOFTWARE_DOMAIN_NAMES
        and (domain != "field operations software" or software_words)
    ]
    physical_software_context = bool(physical_software_domains or physical_software_terms)
    local_vehicle_support = metro_local and bool(contains_phrases(combined, ("local territory", "denver territory", "denver office", "denver showroom")))
    vehicle_supported = bool(vehicle_mitigations or local_vehicle_support or strong_base_signals)
    vehicle_barrier = bool(vehicle_barriers and not vehicle_supported)
    commission_only_risk = bool(commission_risks and not base_pay_signals)
    if YEARS_REQUIRED_RE.search(combined):
        ats_barriers.append("7+ years required")
    if FIVE_PLUS_SAAS_RE.search(combined):
        ats_barriers.append("5+ years SaaS required")
    if "outside sales" in combined and vehicle_barrier:
        ats_barriers.append("outside sales personal vehicle")

    title_barrier = any(
        phrase in title
        for phrase in (
            "senior",
            "principal",
            "strategic",
            "enterprise",
            "director",
            "vp",
            "architect",
            "sales engineer",
            "solutions engineer",
            "solutions consultant",
        )
    )
    seniority_stretch = bool(
        contains_phrases(title, SENIORITY_STRETCH_TITLE_TERMS)
        or contains_phrases(combined, ENTERPRISE_SALES_TERMS)
    )

    if high_domains:
        domain_barrier = "high"
    elif moderate_domains:
        domain_barrier = "moderate"
    elif low_domains or strong_transfer:
        domain_barrier = "low"
    else:
        domain_barrier = "unknown"

    transferability_score = 0
    transferability_score += min(len(strong_transfer) * 4, 20)
    transferability_score += min(len(low_domains) * 3, 12)
    transferability_score += min(len(moderate_domains) * 2, 8)
    transferability_score -= min(len(weak_transfer) * 5, 15)
    transferability_score -= min(len(high_domains) * 4, 16)
    transferability_score = clamp(transferability_score, -20, 30)

    hireability_score = 12
    hireability_score += min(len(strong_transfer) * 2, 10)
    hireability_score += 5 if low_domains else 0
    hireability_score -= 8 if domain_barrier == "high" else 0
    hireability_score -= 3 if domain_barrier == "moderate" else 0
    hireability_score -= min(len(ats_barriers) * 8, 32)
    hireability_score -= 14 if vehicle_barrier else 0
    hireability_score -= 18 if commission_only_risk else 0
    hireability_score += 8 if base_pay_signals else 0
    hireability_score -= 6 if title_barrier else 0
    hireability_score = clamp(hireability_score, -30, 30)

    local_design_sales_fit = bool(low_domains) and any(
        domain in low_domains
        for domain in (
            "building materials",
            "commercial interiors",
            "glass and glazing",
            "flooring and tile",
            "cabinets and countertops",
            "windows and doors",
            "kitchen and bath",
            "home improvement",
            "contractor-facing sales",
            "operational account management",
            "project coordination",
        )
    )
    local_sales_title = contains_phrases(title, LOCAL_SALES_TITLE_TERMS)
    local_technical_title = contains_phrases(title, LOCAL_TECHNICAL_DESIGN_TITLE_TERMS)
    realistic_remote_title = contains_phrases(title, REALISTIC_REMOTE_TITLE_TERMS)
    enterprise_sales_barriers = contains_phrases(combined, ENTERPRISE_SALES_TERMS)
    construction_context = bool(
        low_domains
        or moderate_domains
        or contains_phrases(combined, ("aec", "building materials", "building products", "construction", "contractor", "homebuilding", "geospatial", "drone", "reality capture", "design-build"))
    )
    strong_remote_context = bool(
        construction_context
        or (realistic_remote_title and not enterprise_sales_barriers and not high_domains)
    )
    side_cash_terms = contains_phrases(combined, SIDE_CASH_TERMS)
    paid_project_terms = contains_phrases(combined, PAID_PROJECT_TERMS)
    side_cash_rejects = contains_phrases(combined, SIDE_CASH_REJECT_TERMS)
    low_side_cash_pay = bool(re.search(r"\$\s?(?:[0-9]|1[0-4])(?:\.\d{2})?\s*(?:/|per)\s*(?:hr|hour)", combined))
    side_cash_fit = bool(remote_job and side_cash_terms and paid_project_terms and not side_cash_rejects and not commission_only_risk)

    if commission_only_risk:
        label = "Commission-Only Risk"
    elif vehicle_barrier:
        label = "Vehicle Barrier"
    elif ats_barriers and (domain_barrier == "high" or hireability_score < 0):
        label = "Likely ATS Reject"
    elif domain_barrier == "high" and transferability_score < 14:
        label = "Not a Fit"
    elif side_cash_fit:
        label = "Side-Cash Contractor"
    elif remote_saas and not physical_software_context and not strong_remote_context and (enterprise_sales_barriers or transferability_score < 14):
        label = "Semantic Match Only"
    elif remote_saas and not physical_software_context and (title_barrier or enterprise_sales_barriers or not strong_remote_context):
        label = "Remote Stretch"
    elif transferability_score < 4 and hireability_score < 8:
        label = "Semantic Match Only"
    elif local_design_sales_fit and metro_local and transferability_score >= 14 and hireability_score >= 14:
        label = "Strong Construction/Design Sales Fit"
    elif metro_local and domain_barrier in {"low", "moderate"} and transferability_score >= 14 and hireability_score >= 14:
        label = "Strong Local Fit"
    elif localizable and metro_local and (local_sales_title or local_design_sales_fit) and hireability_score >= 8:
        label = "Realistic Local Sales Fit"
    elif localizable and metro_local and local_technical_title and (local_design_sales_fit or construction_context) and hireability_score >= 8:
        label = "Realistic Local Design/Technical Fit"
    elif remote_only and physical_software_context and strong_remote_context:
        label = (
            "Strong Construction Tech Fit"
            if transferability_score >= 14 and hireability_score >= 12 and not seniority_stretch and not territory_conflicts
            else "Remote Physical-Industry Stretch"
        )
    elif remote_only:
        label = "Remote Stretch"
    else:
        label = "Realistic Stretch"

    penalty = 0
    boost = 0
    if label in {"Strong Local Fit", "Strong Construction/Design Sales Fit"}:
        boost = 18 if label == "Strong Construction/Design Sales Fit" else 14
    elif label == "Realistic Local Sales Fit":
        boost = 12
    elif label == "Realistic Local Design/Technical Fit":
        boost = 10
    elif label == "Strong Construction Tech Fit":
        boost = 8
    elif label == "Remote Physical-Industry Stretch":
        boost = 2
    elif label == "Side-Cash Contractor":
        penalty = 4
    elif label == "Realistic Stretch":
        boost = 4
    elif label == "Remote Stretch":
        penalty = 12
    elif label == "Semantic Match Only":
        penalty = 28
    elif label == "Not a Fit":
        penalty = 34
    elif label == "Likely ATS Reject":
        penalty = 36
    elif label == "Vehicle Barrier":
        penalty = 28
    elif label == "Commission-Only Risk":
        penalty = 34

    notes = []
    if high_domains:
        notes.append("high barrier: " + ", ".join(high_domains[:3]))
    if moderate_domains:
        notes.append("moderate barrier: " + ", ".join(moderate_domains[:3]))
    if low_domains:
        notes.append("low barrier: " + ", ".join(low_domains[:3]))
    if strong_transfer:
        notes.append("transferable: " + ", ".join(strong_transfer[:4]))
    if weak_transfer:
        notes.append("weak transfer: " + ", ".join(weak_transfer[:3]))
    if ats_barriers:
        notes.append("ATS barrier: " + ", ".join(ats_barriers[:3]))
    if vehicle_barrier:
        notes.append("vehicle barrier: " + ", ".join(vehicle_barriers[:3]))
    elif vehicle_mitigations:
        notes.append("vehicle mitigated: " + ", ".join(vehicle_mitigations[:3]))
    elif local_vehicle_support:
        notes.append("vehicle local support signal")
    if commission_only_risk:
        notes.append("commission-only risk: " + ", ".join(commission_risks[:3]))
    if base_pay_signals:
        notes.append("base/stable pay signal")
    if denver_matches:
        notes.append("Denver metro: " + ", ".join(denver_matches[:3]))
    elif local_work_patterns:
        notes.append("local work pattern: " + ", ".join(local_work_patterns[:3]))
    if remote_saas:
        notes.append("remote SaaS stretch context")
    if physical_software_context:
        notes.append("physical-industry software: " + ", ".join((physical_software_terms or physical_software_domains)[:3]))
    if enterprise_sales_barriers:
        notes.append("enterprise sales barrier: " + ", ".join(enterprise_sales_barriers[:3]))
    if side_cash_fit:
        notes.append("paid remote contractor lane: " + ", ".join(side_cash_terms[:3]))
    if low_side_cash_pay:
        notes.append("side-cash pay under $15/hr")

    warnings = []
    if territory_conflicts:
        warnings.append("Non-Denver territory")
    if seniority_stretch:
        warnings.append("Senior/enterprise stretch")
    if remote_saas and not physical_software_context:
        warnings.append("Generic remote SaaS")
    if vehicle_barrier:
        warnings.append("Vehicle barrier")
    if commission_only_risk:
        warnings.append("Commission-only risk")
    if remote_only and label in {"Remote Stretch", "Remote Physical-Industry Stretch"}:
        warnings.append("Remote stretch")
    if job.get("applied"):
        warnings.append("Applied already")

    return {
        "domain_barrier": domain_barrier,
        "domain_matches": high_domains + moderate_domains + low_domains,
        "transferability_score": transferability_score,
        "hireability_score": hireability_score,
        "practical_fit": label,
        "practical_fit_label": label,
        "vehicle_barrier": vehicle_barrier,
        "commission_only_risk": commission_only_risk,
        "base_pay_signal": bool(base_pay_signals),
        "vehicle_support_signal": bool(vehicle_supported),
        "denver_metro_signal": bool(metro_local),
        "localizable_signal": bool(localizable),
        "remote_only_signal": bool(remote_only),
        "remote_saas_signal": bool(remote_saas),
        "physical_industry_software_signal": bool(physical_software_context),
        "side_cash_signal": bool(side_cash_fit),
        "non_denver_territory_signal": bool(territory_conflicts),
        "seniority_stretch_signal": bool(seniority_stretch),
        "fit_warnings": warnings,
        "practical_fit_rank": practical_fit_rank(label),
        "realism_score_delta": boost - penalty,
        "realism_notes": notes,
    }


def matching_domains(text: str, domain_terms: dict[str, tuple[str, ...]]) -> list[str]:
    matches = []
    for domain, terms in domain_terms.items():
        if contains_phrases(text, terms):
            matches.append(domain)
    return matches


def contains_phrases(text: str, phrases: tuple[str, ...]) -> list[str]:
    matches = []
    for phrase in phrases:
        if phrase_in_text(text, phrase):
            matches.append(phrase)
    return matches


def phrase_in_text(text: str, phrase: str) -> bool:
    phrase = phrase.strip().lower()
    if not phrase:
        return False
    if re.fullmatch(r"[a-z0-9]{1,4}", phrase):
        return bool(re.search(rf"\b{re.escape(phrase)}\b", text))
    return phrase in text


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def practical_fit_rank(label: str) -> int:
    return {
        "Strong Construction/Design Sales Fit": 0,
        "Strong Local Fit": 0,
        "Realistic Local Sales Fit": 1,
        "Realistic Local Design/Technical Fit": 1,
        "Strong Construction Tech Fit": 2,
        "Realistic Stretch": 3,
        "Remote Physical-Industry Stretch": 3,
        "Side-Cash Contractor": 4,
        "Remote Stretch": 5,
        "Semantic Match Only": 6,
        "Not a Fit": 7,
        "Likely ATS Reject": 8,
        "Vehicle Barrier": 9,
        "Commission-Only Risk": 9,
    }.get(label, 5)
