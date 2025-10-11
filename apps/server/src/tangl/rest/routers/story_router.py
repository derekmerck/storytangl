from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from tangl.config import settings
from tangl.rest.dependencies import get_orchestrator, get_user_locks
from tangl.service import Orchestrator
from tangl.type_hints import UniqueLabel
from tangl.utils.uuid_for_secret import key_for_secret, uuid_for_key


class ChoiceRequest(BaseModel):
    """Request payload for resolving a player choice."""

    choice_id: UUID | None = None
    uid: UUID | None = None

    def resolve_choice_id(self) -> UUID:
        if self.choice_id is not None:
            return self.choice_id
        if self.uid is not None:
            return self.uid
        raise ValueError("choice_id or uid must be provided")


router = APIRouter(tags=["Story"])


def _call(orchestrator: Orchestrator, endpoint: str, /, **params: Any) -> Any:
    return orchestrator.execute(endpoint, **params)


@router.get("/update")
async def get_story_update(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
    limit: int = Query(default=10, ge=0),
):
    """Return journal fragments and available choices for the active user."""

    user_id = uuid_for_key(api_key)
    fragments = _call(
        orchestrator,
        "RuntimeController.get_journal_entries",
        user_id=user_id,
        limit=limit,
    )
    choices = _call(orchestrator, "RuntimeController.get_available_choices", user_id=user_id)
    return {"fragments": fragments, "choices": choices}


@router.post("/do")
async def do_story_action(
    request: ChoiceRequest = Body(...),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user_locks = Depends(get_user_locks),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
):
    """Resolve a player choice and return the resulting journal fragments."""

    user_id = uuid_for_key(api_key)
    try:
        choice_id = request.resolve_choice_id()
    except ValueError as exc:  # pragma: no cover - FastAPI handles validation
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with user_locks[user_id]:
        return _call(
            orchestrator,
            "RuntimeController.resolve_choice",
            user_id=user_id,
            choice_id=choice_id,
        )


@router.get("/status")
async def get_story_status(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    api_key: UniqueLabel = Header(example=key_for_secret(settings.client.secret), default=None),
):
    """Return a lightweight summary of the current story state."""

    user_id = uuid_for_key(api_key)
    return _call(orchestrator, "RuntimeController.get_story_info", user_id=user_id)


@router.delete("/drop")
async def reset_story():
    """Resetting stories is not yet supported in the orchestrated REST API."""

    raise HTTPException(status_code=501, detail="Story reset is not yet supported")
