from __future__ import annotations

import hmac
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .config import SLOT_START_HOURS
from .models import Member, db, replace_availability
from .slots import find_windows, schedule_dates, slot_key, valid_slot_keys, weeks, window_hours

bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------


@bp.get("/")
def index():
    dates = schedule_dates()
    return render_template(
        "index.html",
        n_days=len(dates),
        n_slots=len(dates) * len(SLOT_START_HOURS),
    )


@bp.get("/respond/<token>")
def respond(token: str):
    member = Member.query.filter_by(token=token).first()
    if member is None:
        abort(404)
    return render_template(
        "respond.html",
        member=member,
        weeks=weeks(),
        selected=sorted(member.slot_keys),
        total_slots=len(valid_slot_keys()),
    )


@bp.post("/api/availability")
def save_availability():
    """
    Body: {"token": str, "slots": [str], "note": str}
    The token identifies the member; a member can only ever write their own row.
    """
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    if not isinstance(token, str) or not token:
        return jsonify(error="Missing token."), 400

    member = Member.query.filter_by(token=token).first()
    if member is None:
        return jsonify(error="Invalid link."), 404

    slots = data.get("slots")
    if not isinstance(slots, list) or not all(isinstance(s, str) for s in slots):
        return jsonify(error="`slots` must be a list of strings."), 400

    valid = valid_slot_keys()
    chosen = {s for s in slots if s in valid}

    note = data.get("note")
    note = note.strip()[:2000] if isinstance(note, str) and note.strip() else None

    replace_availability(member, chosen, note)
    return jsonify(ok=True, saved=len(chosen), updated_at=member.updated_at_iso)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


def _is_admin() -> bool:
    return bool(session.get("admin"))


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not _is_admin():
            return redirect(url_for("main.admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if _is_admin():
        return redirect(url_for("main.admin"))

    error = None
    if request.method == "POST":
        expected = current_app.config["ADMIN_PASSWORD"]
        given = request.form.get("password", "")
        if expected and hmac.compare_digest(given, expected):
            session.clear()
            session["admin"] = True
            session.permanent = True
            return redirect(url_for("main.admin"))
        error = "Incorrect password." if expected else "ADMIN_PASSWORD is not configured on the server."
    return render_template("admin_login.html", error=error)


@bp.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("main.index"))


@bp.get("/admin")
@admin_required
def admin():
    members = Member.query.order_by(Member.id).all()
    total = len(members)

    # slot_key -> [Member]
    by_slot: dict[str, list[Member]] = {}
    for m in members:
        for key in m.slot_keys:
            by_slot.setdefault(key, []).append(m)

    # 2-hour windows (any start hour) where everyone / all-but-one are free.
    everyone, near = find_windows({m.id: m.slot_keys for m in members}, total)
    name_of = {m.id: m.name for m in members}
    responded = sum(1 for m in members if m.updated_at is not None)

    # Hour cells that belong to at least one "everyone free" window (for highlighting).
    star_keys = {slot_key(d, h) for d, start, _ in everyone for h in window_hours(start)}

    return render_template(
        "admin.html",
        members=members,
        total=total,
        responded=responded,
        by_slot=by_slot,
        everyone=everyone,
        near=near,
        name_of=name_of,
        star_keys=star_keys,
        weeks=weeks(),
        slot_key=slot_key,
        base_url=request.url_root.rstrip("/"),
    )


@bp.app_errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404
