# EcoIQ — AI Industrial Audit Platform

An AI-powered facility modernisation platform that analyses industrial operations and delivers McKinsey-grade audit reports with ranked recommendations, ROI analysis, and phased implementation roadmaps.

Built with Django, Anthropic Claude, and WeasyPrint. Synchronous architecture — no workers, no containers, just `python manage.py runserver`.

---

## Features

- **Two-call AI orchestration** — Diagnostic (findings + root causes) → Recommendations (ROI + roadmap)
- **Enterprise audit reports** — 6 sections: Executive Summary, Projections, Before/After, Findings, Recommendations, Roadmap
- **PDF export** — Server-side WeasyPrint A4 PDFs
- **Priority scoring** — Composite score from ROI speed, complexity, savings scale, and quick-win status
- **Demo seeder** — Pre-built Oil Refinery and Logistics Warehouse demos

---

## Quick Start

```bash
# 1. Clone and set up virtual environment
git clone <repo-url>
cd ecoiq-v1
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Apply migrations
python manage.py migrate

# 5. Run the development server
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

---

## Seeding Demo Data

Run the built-in demo seeder to create two fully analysed example facilities:

```bash
# Both demos (Oil Refinery + Logistics Warehouse) — takes ~6-10 min
python manage.py seed_demos

# Single demo
python manage.py seed_demos --name refinery
python manage.py seed_demos --name warehouse

# Create sessions only, skip AI (useful for testing UI without API calls)
python manage.py seed_demos --skip-ai

# Re-create even if already exists
python manage.py seed_demos --force
```

---

## Project Structure

```
ecoiq-v1/
├── audit/                   # Industrial audit app
│   ├── models.py            # AuditSession, Finding, Recommendation, ActionPlan, AuditReport
│   ├── views.py             # All views + report context builder
│   ├── ai.py                # Two-call AI orchestration (diagnostic + recommendations)
│   ├── forms.py             # AuditSessionForm
│   ├── questions.py         # Questionnaire definitions
│   ├── urls.py              # Audit URL patterns
│   ├── templatetags/
│   │   └── audit_tags.py    # fmt_usd, fmt_num, fmt_usd_compact filters
│   └── management/commands/
│       └── seed_demos.py    # Demo data seeder
├── core/                    # ESG core app
├── templates/audit/         # All audit templates
│   ├── report.html          # Full enterprise web report
│   └── report_pdf.html      # WeasyPrint A4 PDF version
├── requirements.txt
├── .env.example
└── manage.py
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key (`sk-ant-...`) |
| `DJANGO_SECRET_KEY` | Yes (prod) | Django secret key — change in production |
| `DEBUG` | No | `True` for development, `False` for production |

---

## AI Model & Token Budget

| Call | Model | Max Tokens | Purpose |
|---|---|---|---|
| Diagnostic | `claude-sonnet-4-6` | 4,000 | 6–10 findings with root causes and financial impact |
| Recommendations | `claude-sonnet-4-6` | 16,000 | 6–10 recommendations + roadmap + projections |

A complete analysis typically takes 3–5 minutes.

---

## Tech Stack

- **Backend** — Django 5.2, SQLite, Python 3.11
- **AI** — Anthropic Claude (`claude-sonnet-4-6`) via `anthropic` SDK
- **PDF** — WeasyPrint 68.1 (server-side A4 rendering)
- **Document parsing** — pypdf (PDF text extraction)

---

## Deploying to Railway (recommended)

Railway provides free-tier hosting with zero-config Django support.

### 1. Install Railway CLI
```bash
npm install -g @railway/cli   # or brew install railway
railway login
```

### 2. Create a new project and deploy
```bash
railway init          # creates new Railway project
railway up            # deploys from current directory
```

### 3. Set environment variables in Railway dashboard
| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (your key) |
| `DJANGO_SECRET_KEY` | Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `yourapp.up.railway.app` (Railway gives you this URL) |
| `CSRF_TRUSTED_ORIGINS` | `https://yourapp.up.railway.app` |

### 4. First deploy runs automatically
- `migrate` runs via the `release` phase in `Procfile`
- `collectstatic` runs during Nixpacks build
- WeasyPrint system libraries (Cairo, Pango) are installed via `nixpacks.toml`

> **Note on SQLite + Railway:** Railway's filesystem is ephemeral — data resets on redeploy. For a persistent production database, upgrade to PostgreSQL (Railway has a one-click Postgres plugin). When ready, set `DATABASE_URL` and add `dj-database-url` to requirements.

---

## Deploying to Render (alternative)

1. Create a new **Web Service** pointing at your GitHub repo
2. Build command: `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate`
3. Start command: `gunicorn ecoiq.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 300`
4. Add the same environment variables as above

---

## Generating a Secure Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Set this as `DJANGO_SECRET_KEY` in your platform's environment variables. Never commit it.

---

## Roadmap (Future)

- [ ] PostgreSQL + Celery async analysis
- [ ] Multi-tenant with Wagtail CMS
- [ ] Sector benchmarking database
- [ ] Interactive charts (Chart.js)
- [ ] Email delivery of PDF reports
- [ ] CI/CD deployment (Railway / Render)
