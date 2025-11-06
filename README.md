AuraLog Registry
=================

What this contains
- AuraLog registration UI (`index.html` + `static/`) with neon/glassmorphism styling.
- AuraLog mission dashboard (`dashboard.html`) with progress & doubt tracking widgets.
- Flask backend (`app.py`) with SQLAlchemy ORM, Argon2 password hashing, and Flask-Migrate for schema migrations.
- API endpoints for registrations, progress logs, and doubts with accompanying Alembic migrations.
- Tests (`tests/`) covering registration, progress updates, and doubt submission flows.
- Optional helpers: PowerShell Waitress launcher (`scripts/start_waitress.ps1`) and Dockerfile.

Quick start (Windows PowerShell)
--------------------------------

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt

# ensure database schema exists (creates SQLite DB at registrations.db)
flask db upgrade  # or: python -c "from app import init_db; init_db()"

python app.py
```

Open http://127.0.0.1:5000/ to view the registration UI.
Open http://127.0.0.1:5000/dashboard to explore the mission dashboard.

Opening the static HTML directly?
--------------------------------
- The frontend now autodetects the API host. When launching `index.html` via the file system it defaults to `http://127.0.0.1:5000`.
- Run `python app.py` (or the Waitress/Docker options below) first so the API is reachable.
- Need a different host/port? Append `?api=http://127.0.0.1:8000` (or your base URL) to the page URL; the choice is remembered in `localStorage`.

Participant dashboard
---------------------
- `/dashboard` renders the neon mission-control view where teams can post updates, review blockers, and raise doubts.
- `POST /api/progress` accepts `username`, `title`, `summary`, optional `status`, `blockers`, `errors` and stores them in `progress_updates`.
- `GET /api/progress` returns the latest updates plus aggregate stats (total entries, items with issues, status breakdown).
- `POST /api/doubts` accepts `username`, `topic`, `question` to log new queries for mentors.
- `GET /api/doubts` lists raised questions so mentors can review and resolve them.
- Use the `errors` field of a progress update to attach failing-test output or bug descriptions—these surface in the dashboard as red chips, making “what went wrong” obvious during judging.

Database migrations (Flask-Migrate/Alembic)
-------------------------------------------
- Set environment: `set FLASK_APP=app.py` (PowerShell: `$env:FLASK_APP = 'app.py'`).
- Initialize once (already committed, but for new projects): `flask db init`.
- Generate migrations after model changes: `flask db migrate -m "message"`.
- Apply migrations: `flask db upgrade`.

Production-style run options
----------------------------

- PowerShell helper script (Waitress + migration upgrade + env vars):

```powershell
./scripts/start_waitress.ps1 -ListenHost 0.0.0.0 -Port 8000
```

- Manual Waitress run on Windows:

```powershell
.\.venv\Scripts\Activate
pip install waitress
flask db upgrade
.\.venv\Scripts\waitress-serve --listen=0.0.0.0:8000 app:app
```

- Docker:

```powershell
docker build -t auralog .
docker run --rm -p 5000:5000 auralog
```

Environment variables respected when running `python app.py`:
- `FLASK_DEBUG` (default 0)
- `FLASK_RUN_HOST` (default 127.0.0.1)
- `FLASK_RUN_PORT` (default 5000)
- `FLASK_SECRET_KEY` / `SECRET_KEY` (set this to override the default dev secret)
- `DATABASE` or `DATABASE_URL` (override SQLite location/URI)

Running tests
-------------

```powershell
.\.venv\Scripts\Activate
pytest -q
```

Tests spin up a temporary SQLite database using SQLAlchemy and verify password hashes are not stored in plaintext. Additional tests cover the progress and doubt APIs to guard against regressions in the dashboard workflow.

Security notes
--------------
- Passwords are hashed with Argon2 (argon2-cffi). The SQLite database stores only the hash.
- Use HTTPS and a reverse proxy (Nginx/IIS) in production.
- Consider adding CAPTCHA, email confirmation, rate limiting, and secrets management before public deployment.

Global launch checklist
-----------------------
1. Secure the AuraLog brand
	- Register the primary domain (`auralog.com` recommended) along with alternates such as `auralog.net` or `auralog.app` using any reputable registrar.
	- Configure DNS A/AAAA records to point at your hosting platform once deployment is ready.

2. Deploy AuraLog globally (Render free tier example)
	- Push this repository to GitHub (all files including `Dockerfile`).
	- Create a Render account → **New** → **Web Service** → connect your repo → choose the free instance type.
	- Keep **Environment = Docker**; Render will build from the provided `Dockerfile`.
	- Add environment variables in the Render dashboard:
		- `FLASK_SECRET_KEY` — generate a long random string (do not reuse the default).
		- `FLASK_APP=app.py`, `FLASK_DEBUG=0`.
	- Deploy. Render assigns a free HTTPS subdomain (e.g. `https://auralog.onrender.com/`). Note: the free plan clears the filesystem between restarts, so the bundled SQLite DB is ephemeral.
	- (Optional) Add a custom domain later by upgrading or using another DNS provider.
	- Add an uptime monitor (e.g., UptimeRobot) if you need alerts.

3. Search engine optimization (SEO)
	- Meta tags for description, keywords, and social previews are embedded in `index.html` and `dashboard.html`. Update their content if messaging evolves.
	- Sitemap is exposed at `/sitemap.xml` (see `static/sitemap.xml`). Update URLs/dates before each deployment.
	- In Google Search Console or Bing Webmaster Tools, add the live Render URL (e.g., `https://auralog.onrender.com/`) and verify ownership via the HTML `<meta>` tag method—paste the provided tag into the `<head>` of `index.html`, deploy, then click **Verify**.
	- Use the **URL Inspection** tool (“Request indexing”) for `/` and `/dashboard` after each major update.
	- Share the live URL on community sites, portfolio pages, and social media to build backlinks and improve ranking.

4. Localization roadmap (optional)
	- Use the existing structure to serve localized copies of the HTML or integrate a translation framework.
	- Expose language switchers and add `hreflang` tags when additional languages ship.

Next improvements (ideas)
- Add user login flow + JWT/session management.
- Add background job to send welcome emails.
- Add integration tests for the Docker image and CI automation.
