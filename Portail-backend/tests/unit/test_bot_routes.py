import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from adgi360.infrastructure.config import settings as settings_module
from adgi360.infrastructure.security import create_callback_token
from adgi360.interfaces.api.v1.routers.auto_review import fail_report
from adgi360.interfaces.api.v1.routers.bot import verify_bot_token
from adgi360.interfaces.api.v1.schemas.auto_review_schemas import FailReportRequest


def test_bot_disabled_without_token(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "bot_api_token", "")
    with pytest.raises(HTTPException) as error:
        asyncio.run(verify_bot_token("anything"))
    assert error.value.status_code == 503


def test_bot_rejects_wrong_token(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "bot_api_token", "secret")
    with pytest.raises(HTTPException) as error:
        asyncio.run(verify_bot_token("nope"))
    assert error.value.status_code == 401
    asyncio.run(verify_bot_token("secret"))  # ne lève pas


@pytest.mark.parametrize("state,expected", [("processing", "failed"), ("awaiting_approval", "awaiting_approval")])
def test_fail_callback_only_touches_running_reviews(state, expected):
    review = SimpleNamespace(status=state, error_message=None)
    session = SimpleNamespace(get=AsyncMock(return_value=review), commit=AsyncMock(), refresh=AsyncMock())
    asyncio.run(fail_report("r1", FailReportRequest(reason="Ollama hors ligne"),
                            create_callback_token("r1"), session))
    assert review.status == expected


def test_fail_callback_requires_valid_token():
    session = SimpleNamespace(get=AsyncMock())
    with pytest.raises(HTTPException) as error:
        asyncio.run(fail_report("r1", FailReportRequest(), "bad", session))
    assert error.value.status_code == 403
