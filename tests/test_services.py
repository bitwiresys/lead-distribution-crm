from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Contact, Operator, OperatorSourceWeight, Source
from app.services import create_contact_for_lead, get_distribution_stats


def test_distribution_roughly_follows_weights(db_session: Session) -> None:
    operator_a = Operator(name="operator-a", is_active=True, load_limit=100)
    operator_b = Operator(name="operator-b", is_active=True, load_limit=100)
    source = Source(name="bot-A")

    db_session.add_all([operator_a, operator_b, source])
    db_session.commit()

    db_session.refresh(operator_a)
    db_session.refresh(operator_b)
    db_session.refresh(source)

    weight_a = OperatorSourceWeight(operator_id=operator_a.id, source_id=source.id, weight=10)
    weight_b = OperatorSourceWeight(operator_id=operator_b.id, source_id=source.id, weight=30)
    db_session.add_all([weight_a, weight_b])
    db_session.commit()

    for _ in range(40):
        create_contact_for_lead(
            db_session,
            external_lead_id="lead-1",
            source_id=source.id,
            message=None,
        )

    stmt = select(Contact.operator_id)
    operator_ids = db_session.execute(stmt).scalars().all()

    count_a = sum(1 for operator_id in operator_ids if operator_id == operator_a.id)
    count_b = sum(1 for operator_id in operator_ids if operator_id == operator_b.id)

    assert count_a + count_b == 40
    assert count_b == 3 * count_a


def test_load_limit_respected(db_session: Session) -> None:
    operator_a = Operator(name="limited", is_active=True, load_limit=1)
    operator_b = Operator(name="unlimited", is_active=True, load_limit=100)
    source = Source(name="bot-B")

    db_session.add_all([operator_a, operator_b, source])
    db_session.commit()

    db_session.refresh(operator_a)
    db_session.refresh(operator_b)
    db_session.refresh(source)

    weight_a = OperatorSourceWeight(operator_id=operator_a.id, source_id=source.id, weight=10)
    weight_b = OperatorSourceWeight(operator_id=operator_b.id, source_id=source.id, weight=10)
    db_session.add_all([weight_a, weight_b])
    db_session.commit()

    for index in range(3):
        create_contact_for_lead(
            db_session,
            external_lead_id=f"lead-{index}",
            source_id=source.id,
            message=None,
        )

    stmt = select(Contact.operator_id)
    operator_ids = db_session.execute(stmt).scalars().all()

    count_a = sum(1 for operator_id in operator_ids if operator_id == operator_a.id)
    count_b = sum(1 for operator_id in operator_ids if operator_id == operator_b.id)

    assert count_a == 1
    assert count_b == 2


def test_contact_can_be_created_without_operator_when_no_candidates(db_session: Session) -> None:
    source = Source(name="bot-no-operators")
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    contact = create_contact_for_lead(
        db_session,
        external_lead_id="l-one",
        source_id=source.id,
        message=None,
    )

    assert contact.operator_id is None


def test_distribution_stats_aggregates_contacts(db_session: Session) -> None:
    operator_a = Operator(name="op-stats-a", is_active=True, load_limit=100)
    operator_b = Operator(name="op-stats-b", is_active=True, load_limit=100)
    source = Source(name="bot-stats")

    db_session.add_all([operator_a, operator_b, source])
    db_session.commit()

    db_session.refresh(operator_a)
    db_session.refresh(operator_b)
    db_session.refresh(source)

    weight_a = OperatorSourceWeight(operator_id=operator_a.id, source_id=source.id, weight=10)
    weight_b = OperatorSourceWeight(operator_id=operator_b.id, source_id=source.id, weight=10)
    db_session.add_all([weight_a, weight_b])
    db_session.commit()

    create_contact_for_lead(
        db_session,
        external_lead_id="lead-a",
        source_id=source.id,
        message=None,
    )
    create_contact_for_lead(
        db_session,
        external_lead_id="lead-b",
        source_id=source.id,
        message=None,
    )

    stats = get_distribution_stats(db_session)

    assert stats
    total_contacts = sum(item.contacts_count for item in stats)
    assert total_contacts == 2
