from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from tangl.config import settings
from tangl.rest.dependencies import get_orchestrator, get_user_locks
from tangl.service import Orchestrator
from tangl.type_hints import UniqueLabel
from tangl.utils.hash_secret import key_for_secret, uuid_for_key


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


def _serialize(value: Any) -> Any:
    """Best-effort JSON encoding for fragments and response payloads."""

    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, set):
        return [_serialize(item) for item in sorted(value, key=str)]
    if isinstance(value, type):
        return value.__name__
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        data = value.model_dump(mode="python")
        return {key: _serialize(item) for key, item in data.items()}
    return value


def _call(orchestrator: Orchestrator, endpoint: str, /, **params: Any) -> Any:
    return orchestrator.execute(endpoint, **params)


@router.post("/story/create")
async def create_story(
    world_id: str = Query(..., description="World template to instantiate"),
    story_label: str | None = Query(None, description="Optional story label"),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Create a new story instance for the authenticated user."""

    user_id = uuid_for_key(api_key)
    kwargs: dict[str, Any] = {"world_id": world_id}
    if story_label:
        kwargs["story_label"] = story_label
    result = _call(orchestrator, "RuntimeController.create_story", user_id=user_id, **kwargs)
    ledger_obj = result.get("ledger") if isinstance(result, dict) else None
    if ledger_obj is not None and orchestrator.persistence is not None:
        orchestrator.persistence.save(ledger_obj)
        result = dict(result)
        result.pop("ledger", None)
    return result


# todo: maybe "journal" since update is used as a phase?
@router.get("/update")
async def get_story_update(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    limit: int = Query(default=10, ge=0),
) -> dict[str, Any]:
    """Return journal fragments and available choices for the active user."""

    user_id = uuid_for_key(api_key)
    fragments = _call(
        orchestrator,
        "RuntimeController.get_journal_entries",
        user_id=user_id,
        limit=limit,
    )
    choices = _call(orchestrator, "RuntimeController.get_available_choices", user_id=user_id)
    return {"fragments": _serialize(fragments), "choices": _serialize(choices)}


@router.post("/do")
async def do_story_action(
    request: ChoiceRequest = Body(...),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user_locks = Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
):
    """Resolve a player choice and return the resulting journal fragments."""

    user_id = uuid_for_key(api_key)
    try:
        choice_id = request.resolve_choice_id()
    except ValueError as exc:  # pragma: no cover - FastAPI handles validation
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with user_locks[user_id]:
        status = _call(
            orchestrator,
            "RuntimeController.resolve_choice",
            user_id=user_id,
            choice_id=choice_id,
        )

        fragments = _call(
            orchestrator,
            "RuntimeController.get_journal_entries",
            user_id=user_id,
            limit=0,
        )

    payload = _serialize(status)
    if not isinstance(payload, dict):
        payload = {"status": payload}
    payload["fragments"] = _serialize(fragments)
    return payload


@router.get("/status")
async def get_story_status(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
):
    """Return a lightweight summary of the current story state."""

    user_id = uuid_for_key(api_key)
    return _call(orchestrator, "RuntimeController.get_story_info", user_id=user_id)


@router.delete("/drop")
async def reset_story(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user_locks=Depends(get_user_locks),
    api_key: UniqueLabel = Header(
        ..., alias="X-API-Key", example=key_for_secret(settings.client.secret)
    ),
    archive: bool = Query(default=False, description="Retain the ledger if true."),
):
    """End the user's active story and optionally archive the ledger."""

    user_id = uuid_for_key(api_key)

    try:
        async with user_locks[user_id]:
            result = _call(
                orchestrator,
                "RuntimeController.drop_story",
                user_id=user_id,
                archive=archive,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _serialize(result)
