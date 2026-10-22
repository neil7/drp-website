from __future__ import annotations

import secrets
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _new_token() -> str:
    return secrets.token_urlsafe(24)


class Member(db.Model):
    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120))
    email = db.Column(db.String(200))
    # Secret embedded in each member's private link: /respond/<token>
    token = db.Column(db.String(64), unique=True, nullable=False, default=_new_token)
    note = db.Column(db.Text)
    updated_at = db.Column(db.DateTime(timezone=True))

    availability = db.relationship(
        "Availability", backref="member", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def slot_keys(self) -> set[str]:
        return {a.slot_key for a in self.availability}

    @property
    def updated_at_iso(self) -> str | None:
        """ISO-8601 in UTC (SQLite drops tzinfo on read, so re-attach it)."""
        if self.updated_at is None:
            return None
        dt = self.updated_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()

    @property
    def initials(self) -> str:
        parts = self.name.replace("Dr.", "").split()
        return "".join(p[0] for p in parts if p).upper()


class Availability(db.Model):
    __tablename__ = "availability"

    member_id = db.Column(db.Integer, db.ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    # e.g. "2026-11-02|10"  => Nov 2, 2026, 10:00–12:00
    slot_key = db.Column(db.String(16), primary_key=True)


def replace_availability(member: Member, slot_keys: set[str], note: str | None) -> None:
    """Atomically replace a member's availability (single transaction)."""
    # delete-orphan cascade removes the old rows; flush first so the DELETEs
    # hit the DB before the INSERTs that may reuse the same primary keys.
    member.availability.clear()
    db.session.flush()
    member.availability.extend(Availability(slot_key=key) for key in sorted(slot_keys))
    member.note = note
    member.updated_at = datetime.now(timezone.utc)
    db.session.commit()
