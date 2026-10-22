import os
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import click
from dotenv import load_dotenv
from flask import Flask

from . import config as cfg
from .models import Member, db
from .slots import fmt_date, fmt_hour_short, fmt_range, fmt_range_short, parse_slot_key


def create_app() -> Flask:
    # override=True so edits to .env always win over stale shell variables.
    load_dotenv(override=True)

    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    database_url = os.environ.get("DATABASE_URL") or f"sqlite:///{Path(app.instance_path) / 'drp.sqlite3'}"
    # Heroku/Render-style URLs use the legacy "postgres://" scheme.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or "dev-only-secret-change-me",
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD") or "",
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production"
        or os.environ.get("RENDER") is not None
        or os.environ.get("PYTHONANYWHERE_DOMAIN") is not None,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
        MAX_CONTENT_LENGTH=256 * 1024,
    )

    db.init_app(app)

    from .routes import bp

    app.register_blueprint(bp)

    def fmt_dt_local(dt):
        """Render a stored (UTC) timestamp in Pacific time for the admin view."""
        if dt is None:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%b %-d, %-I:%M %p %Z")

    # Make config + formatters available in every template.
    @app.context_processor
    def inject_globals():
        return {
            "fmt_dt_local": fmt_dt_local,
            "DRP": cfg.DRP,
            "WINDOW": cfg.SCHEDULE_WINDOW,
            "SLOT_HOURS": cfg.SLOT_START_HOURS,
            "TZ_LABEL": cfg.TIME_ZONE_LABEL,
            "fmt_date": fmt_date,
            "fmt_range": fmt_range,
            "fmt_range_short": fmt_range_short,
            "fmt_hour_short": fmt_hour_short,
            "parse_slot_key": parse_slot_key,
        }

    @app.cli.command("init-db")
    @click.option("--base-url", default="http://127.0.0.1:5000", show_default=True,
                  help="Used only to print full private links.")
    def init_db(base_url: str) -> None:
        """Create tables and seed the committee from drp/config.py (idempotent)."""
        db.create_all()
        created = 0
        for person in cfg.DRP["committee"]:
            if not Member.query.filter_by(name=person["name"]).first():
                db.session.add(Member(name=person["name"], role=person["role"]))
                created += 1
        db.session.commit()

        click.echo(f"\nDatabase ready ({created} new member(s) added).")
        click.echo("Private links — share each ONLY with that person:\n")
        for m in Member.query.order_by(Member.id).all():
            click.echo(f"  {m.name:<24} {base_url.rstrip('/')}/respond/{m.token}")
        click.echo(f"\nAdmin dashboard: {base_url.rstrip('/')}/admin\n")

    @app.cli.command("reset-db")
    @click.option("--keep-members", is_flag=True,
                  help="Clear only responses/notes; keep members and their private links.")
    @click.confirmation_option(prompt="This deletes data. Continue?")
    def reset_db(keep_members: bool) -> None:
        """Wipe responses (and optionally members). Run init-db afterwards to re-seed."""
        from .models import Availability

        Availability.query.delete()
        if keep_members:
            Member.query.update({Member.note: None, Member.updated_at: None})
            db.session.commit()
            click.echo("Cleared all responses and notes. Members and links unchanged.")
        else:
            Member.query.delete()
            db.session.commit()
            click.echo("Cleared everything. Run `flask --app app init-db` to re-seed members (new links).")

    @app.cli.command("reset-token")
    @click.argument("member_name")
    def reset_token(member_name: str) -> None:
        """Rotate a member's private link if it was shared by mistake."""
        from .models import _new_token

        m = Member.query.filter(Member.name.ilike(f"%{member_name}%")).first()
        if not m:
            raise click.ClickException(f"No member matching '{member_name}'.")
        m.token = _new_token()
        db.session.commit()
        click.echo(f"{m.name}: /respond/{m.token}")

    return app
