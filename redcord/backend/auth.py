from __future__ import annotations

import hashlib
import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from redcord.backend.models import EmailCode, SessionToken, User

logger = logging.getLogger(__name__)


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def issue_email_code(db: Session, email: str) -> str:
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        EmailCode(
            email=email.strip().lower(),
            code_hash=hash_code(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
    )
    db.commit()
    _send_or_log_code(email, code)
    return code


def verify_email_code(db: Session, email: str, code: str) -> str | None:
    normalized = email.strip().lower()
    row = db.execute(
        select(EmailCode)
        .where(EmailCode.email == normalized, EmailCode.consumed_at.is_(None))
        .order_by(EmailCode.created_at.desc())
    ).scalar_one_or_none()
    if row is None or row.expires_at < datetime.now(timezone.utc):
        return None
    if row.code_hash != hash_code(code.strip()):
        return None
    row.consumed_at = datetime.now(timezone.utc)
    user = db.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    if user is None:
        user = User(id=secrets.token_hex(16), email=normalized, display_name=normalized.split("@")[0])
        db.add(user)
        db.flush()
    token = secrets.token_urlsafe(48)
    db.add(SessionToken(token=token, user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    db.commit()
    return token


def user_id_from_token(db: Session, authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    row = db.get(SessionToken, token)
    if row is None or row.expires_at < datetime.now(timezone.utc):
        return None
    return row.user_id


def _send_or_log_code(email: str, code: str) -> None:
    host = os.getenv("REDCORD_SMTP_HOST", "").strip()
    if not host:
        logger.warning("DEV EMAIL CODE for %s: %s", email, code)
        return
    message = EmailMessage()
    message["Subject"] = "RedCord login code"
    message["From"] = os.getenv("REDCORD_SMTP_FROM", "redcord@example.local")
    message["To"] = email
    message.set_content(f"Your RedCord login code is: {code}")
    port = int(os.getenv("REDCORD_SMTP_PORT", "587"))
    username = os.getenv("REDCORD_SMTP_USER", "")
    password = os.getenv("REDCORD_SMTP_PASSWORD", "")
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)
