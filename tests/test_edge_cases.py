from __future__ import annotations

import pytest
from sqlalchemy.orm import Session as OrmSession

from app.db import get_session
from app.services import create_contact_for_lead


def test_create_contact_for_lead_raises_value_error_when_source_missing(
    db_session: OrmSession,
) -> None:
    with pytest.raises(ValueError):
        create_contact_for_lead(
            db_session,
            external_lead_id="missing-source",
            source_id=12345,
            message=None,
        )


def test_get_session_yields_session() -> None:
    generator = get_session()
    try:
        session = next(generator)
        assert isinstance(session, OrmSession)
    finally:
        generator.close()
