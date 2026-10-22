# Neil's DRP — Availability Scheduler

A small Flask website for collecting committee availability for the DRP presentation
(**Caffeine: Efficient Machine Unlearning via First-Order Taylor Approximation**).

| Page | Who | What |
| --- | --- | --- |
| `/` | public | "Welcome to Neil's DRP" landing page with project, advisor, committee, format |
| `/respond/<token>` | one committee member | **Private** hourly grid (9 AM–8 PM). Click/drag to paint free hours; autosaves. A member sees **only their own** answers |
| `/admin` | you | Password-protected dashboard: who responded, hourly overlap heatmap, every 2-hour window (any start time) where everyone is free, notes, and each member's private link |

**Stack:** Python 3.10+, Flask, Flask-SQLAlchemy, SQLite (default), vanilla JS/CSS — no build step.

---

## 1. Run it locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env (see below)
flask --app app init-db         # creates tables, seeds the 3 members, prints their private links
flask --app app run --debug     # http://127.0.0.1:5000
```

`.env`:

| Variable | Meaning |
| --- | --- |
| `ADMIN_PASSWORD` | Password for `/admin`. Pick something strong; only you use it. |
| `SECRET_KEY` | Signs the session cookie. Generate with `openssl rand -hex 32`. |
| `DATABASE_URL` | Optional. Defaults to SQLite at `instance/drp.sqlite3`. |

> macOS note: port 5000 is often taken by AirPlay Receiver. Use `flask --app app run --port 5050` if so.

Useful commands:

```bash
flask --app app init-db --base-url https://YOUR-SITE   # reprint links with the live domain
flask --app app reset-token "Nguyen"                   # rotate one member's link if it leaked
flask --app app reset-db --keep-members                # clear all responses, keep links (after testing)
flask --app app reset-db                               # wipe everything; then run init-db for fresh links
```

Or delete the file: `rm instance/drp.sqlite3` and run `init-db` again.

---

## 2. Host it for free — PythonAnywhere (recommended)

PythonAnywhere's free tier is permanent, always-on, gives you HTTPS at
`https://<username>.pythonanywhere.com`, and has a **persistent disk**, so SQLite just works.
No credit card.

1. Sign up at <https://www.pythonanywhere.com> (Beginner / free plan).
2. Open a **Bash console** and clone or upload the project:
   ```bash
   git clone https://github.com/<you>/drp-website.git   # or upload a zip via the Files tab
   cd drp-website
   python3.10 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env && nano .env                    # set ADMIN_PASSWORD and SECRET_KEY
   flask --app app init-db --base-url https://<username>.pythonanywhere.com
   ```
   Copy the printed private links somewhere safe.
3. **Web** tab → *Add a new web app* → *Manual configuration* → Python 3.10.
4. On the Web tab:
   - **Source code**: `/home/<username>/drp-website`
   - **Virtualenv**: `/home/<username>/drp-website/.venv`
   - **WSGI configuration file** → click it, replace the contents with
     [`pythonanywhere_wsgi.py`](pythonanywhere_wsgi.py) and set `PROJECT_DIR` to your path.
   - **Static files**: URL `/static/` → Directory `/home/<username>/drp-website/drp/static`
   - Tick **Force HTTPS**.
5. Click **Reload**. Visit `https://<username>.pythonanywhere.com`.

Free apps must be "renewed" by clicking a button on the Web tab every 3 months — irrelevant for a
one-month poll. To update code later: `git pull` in the console, then **Reload**.

### Alternative: Render (free web service)

`render.yaml` is included. Render's free tier has an **ephemeral disk**, so SQLite would be wiped
on each deploy/restart. If you use Render, also create a free Postgres on <https://neon.tech>,
set `DATABASE_URL` to its connection string (`postgresql+psycopg://…?sslmode=require`), and add
`psycopg[binary]` to `requirements.txt`. The free Render service also sleeps after 15 min idle, so
the first load takes ~30 s.

Other options that work with zero code changes: **Fly.io** (free allowance + 1 GB volume),
**Railway** (trial credits, enough for a month), **Koyeb** (free instance).

---

## 3. Send the links

1. Open `https://<your-site>/admin`, sign in with `ADMIN_PASSWORD`.
2. Click **Copy** next to each member and email that link **only to that person**.
   Never share the admin URL/password.
3. Watch the heatmap. Dark-green ★ cells = all three are free → that's your slot.

Suggested email:

> **Subject:** Neil's DRP — availability for a 2-hour presentation slot
>
> Dear Dr. ___,
>
> Could you mark the 2-hour blocks you're available for my DRP presentation (public talk followed
> by the private committee questioning) between Nov 2 and Dec 4? Here is your private link:
> `<link>` — it takes about a minute, saves automatically, and you can revisit it anytime to update.
>
> Thank you!
> Neil

---

## 4. Changing dates, times, or people

Everything lives in [`drp/config.py`](drp/config.py):

- `SCHEDULE_WINDOW` — start/end date, allowed weekdays, excluded dates (Thanksgiving is excluded by default).
- `DAY_START_HOUR` / `DAY_END_HOUR` — the hours members can mark (`9` / `20` → 9 AM–8 PM, one cell per hour).
  The dashboard finds every `duration_hours`-long window (any start hour, e.g. 10 AM–12 PM) where everyone is free.
- `DRP` — title, advisor, committee names/roles, contact email, duration.

After editing committee names, re-run `flask --app app init-db` — it only adds members that don't
exist yet. Changing the date window does **not** delete existing responses; blocks outside the
new window are simply ignored.

---

## Privacy model

- Each member's page is keyed by a 32-character random token in the URL. Tokens are shown only on
  `/admin`. Members cannot see, guess, or enumerate each other's pages.
- The save endpoint (`POST /api/availability`) identifies the member by token and only writes
  that member's row. Slot keys are validated against the configured window.
- `/admin` requires `ADMIN_PASSWORD` (constant-time compare); the session is a signed,
  `HttpOnly`, `SameSite=Lax` cookie, `Secure` in production.
- All pages send `noindex, nofollow`.

## Project layout

```
app.py                     # entry point (flask run / gunicorn app:app)
drp/
  __init__.py              # app factory, CLI commands (init-db, reset-token)
  config.py                # <-- edit dates, slots, names here
  models.py                # Member, Availability (SQLAlchemy)
  routes.py                # pages + JSON API + admin auth
  slots.py                 # slot enumeration & formatting helpers
  templates/               # Jinja templates
  static/css/style.css     # design (UO green/yellow)
  static/js/respond.js     # drag-to-paint grid + autosave
  static/js/admin.js       # copy-link buttons
render.yaml                # optional Render blueprint
pythonanywhere_wsgi.py     # optional PythonAnywhere WSGI entry
```
