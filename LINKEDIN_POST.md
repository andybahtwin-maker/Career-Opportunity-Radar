I built a local-first Career Opportunity Radar to make job search review more targeted and less noisy.

It monitors a curated list of public company career pages and ATS boards, normalizes postings into a local archive, scores roles with transparent rules, and produces both a Markdown digest and a small local browser dashboard.

What it does:

- scans Lever, Greenhouse, Ashby, Workable, and selected company career pages
- stores job history locally in JSON
- pulls job descriptions when available
- ranks roles with explainable scoring
- generates a daily digest with direct job links
- provides a local dashboard with an applied-job toggle
- can be scheduled with n8n

What it does not do:

- no auto-applying
- no recruiter spam
- no cloud database
- no private account scraping

The interesting part was keeping it practical: simple Python, public job-board endpoints, local state, readable outputs, and just enough automation to reduce repetitive checking without removing human judgment.

Portfolio angle: this project demonstrates Python automation, ATS/job-board scraping, structured scoring, local web UI, n8n orchestration, and practical AI/workflow thinking.
