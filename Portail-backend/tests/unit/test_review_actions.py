import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from adgi360.interfaces.api.v1.routers.auto_review import delete_review, preview_report


def fixtures(status="approved", organization_id="agency"):
    review = SimpleNamespace(
        organization_id=organization_id, status=status,
        report_storage_key="reports/example.pptx", report_filename="example.pptx",
    )
    session = SimpleNamespace(get=AsyncMock(return_value=review), delete=AsyncMock(), commit=AsyncMock())
    storage = SimpleNamespace(delete=AsyncMock(), list_keys=AsyncMock(return_value=[]), presigned_url=AsyncMock(return_value="https://example.test/report.pdf"))
    return SimpleNamespace(organization_id="agency"), session, storage


def test_delete_removes_both_artifacts():
    user, session, storage = fixtures()
    asyncio.run(delete_review("review", user, session, storage))
    assert storage.delete.await_count == 2
    session.delete.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.parametrize("state", ["pending", "processing"])
def test_cannot_delete_active_report(state):
    user, session, storage = fixtures(status=state)
    with pytest.raises(HTTPException) as error:
        asyncio.run(delete_review("review", user, session, storage))
    assert error.value.status_code == 409
    storage.delete.assert_not_awaited()


def test_other_agency_cannot_delete():
    user, session, storage = fixtures(organization_id="other")
    with pytest.raises(HTTPException) as error:
        asyncio.run(delete_review("review", user, session, storage))
    assert error.value.status_code == 404
    storage.delete.assert_not_awaited()


def test_missing_preview_has_explicit_error():
    user, session, storage = fixtures()
    with pytest.raises(HTTPException) as error:
        asyncio.run(preview_report("review", user, session, storage))
    assert error.value.status_code == 404
    storage.presigned_url.assert_not_awaited()


def test_existing_preview_returns_signed_url():
    user, session, storage = fixtures()
    storage.list_keys.return_value = [{"key": "reports/example.pdf"}]
    result = asyncio.run(preview_report("review", user, session, storage))
    assert result.mode == "pdf"
    assert result.filename == "example.pdf"
    storage.presigned_url.assert_awaited_once_with("reports/example.pdf")
