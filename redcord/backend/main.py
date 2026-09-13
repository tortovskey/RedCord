from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from redcord import __version__
from redcord.backend.auth import issue_email_code, user_id_from_token, verify_email_code
from redcord.backend.database import SessionLocal, create_schema
from redcord.backend.models import SyncItem

logger = logging.getLogger(__name__)
app = FastAPI(title="RedCord Online Beta", version=__version__)


class RequestCodeIn(BaseModel):
    email: EmailStr


class VerifyCodeIn(BaseModel):
    email: EmailStr
    code: str


class PullIn(BaseModel):
    since: str = ""


class PushIn(BaseModel):
    projects: list[dict] = []
    documents: list[dict] = []
    concepts: list[dict] = []
    commits: list[dict] = []
    templates: list[dict] = []
    branches: list[dict] = []
    art_assets: list[dict] = []


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> str:
    user_id = user_id_from_token(db, authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user_id


@app.on_event("startup")
def startup() -> None:
    create_schema()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/auth/request-code")
def request_code(payload: RequestCodeIn, db: Session = Depends(get_db)) -> dict[str, str]:
    issue_email_code(db, payload.email)
    return {"message": "Email code requested. In dev mode check backend logs."}


@app.post("/auth/verify-code")
def verify_code(payload: VerifyCodeIn, db: Session = Depends(get_db)) -> dict[str, str]:
    token = verify_email_code(db, payload.email, payload.code)
    if not token:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    return {"token": token}


@app.post("/sync/status")
def sync_status(user_id: str = Depends(require_user), db: Session = Depends(get_db)) -> dict[str, object]:
    count = db.execute(select(SyncItem).where(SyncItem.user_id == user_id)).scalars().all()
    return {"user_id": user_id, "items": len(count), "server_time": datetime.now(timezone.utc).isoformat()}


@app.post("/sync/pull")
def sync_pull(payload: PullIn, user_id: str = Depends(require_user), db: Session = Depends(get_db)) -> dict[str, object]:
    rows = db.execute(select(SyncItem).where(SyncItem.user_id == user_id)).scalars().all()
    result: dict[str, list[dict]] = {
        "projects": [],
        "documents": [],
        "concepts": [],
        "commits": [],
        "templates": [],
        "branches": [],
        "art_assets": [],
    }
    for row in rows:
        key = row.entity_type if row.entity_type in result else f"{row.entity_type}s"
        if key in result:
            result[key].append(json.loads(row.payload_json))
    result["server_time"] = datetime.now(timezone.utc).isoformat()  # type: ignore[index]
    return result


@app.post("/sync/push")
def sync_push(payload: PushIn, user_id: str = Depends(require_user), db: Session = Depends(get_db)) -> dict[str, object]:
    changed = 0
    conflicts: list[dict[str, object]] = []
    singular_names = {"branches": "branch", "art_assets": "art_asset", "projects": "project", "documents": "document", "concepts": "concept", "commits": "commit", "templates": "template"}
    for entity_type in ["projects", "documents", "concepts", "commits", "templates", "branches", "art_assets"]:
        singular = singular_names[entity_type]
        for item in getattr(payload, entity_type):
            entity_id = str(item.get("id", ""))
            if not entity_id:
                continue
            revision = int(item.get("revision") or 0)
            existing = db.execute(
                select(SyncItem).where(
                    SyncItem.user_id == user_id,
                    SyncItem.entity_type == entity_type,
                    SyncItem.entity_id == entity_id,
                )
            ).scalar_one_or_none()
            if existing and existing.revision > revision:
                conflicts.append({"entity_type": singular, "entity_id": entity_id, "server_revision": existing.revision})
                continue
            if existing is None:
                existing = SyncItem(user_id=user_id, entity_type=entity_type, entity_id=entity_id, revision=revision)
                db.add(existing)
            existing.revision = revision
            existing.payload_json = json.dumps(item, ensure_ascii=False)
            changed += 1
    db.commit()
    return {"changed": changed, "conflicts": conflicts}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("redcord.backend.main:app", host="0.0.0.0", port=8088, reload=True)
