from __future__ import annotations

from uuid import uuid4


def create_conflict_copy_id(entity_id: str) -> str:
    return f"{entity_id}__conflict__{uuid4().hex[:10]}"
