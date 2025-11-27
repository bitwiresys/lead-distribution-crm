from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Contact, Lead, Operator, OperatorSourceWeight, Source


@dataclass
class DistributionInfo:
    operator_id: int | None
    source_id: int
    contacts_count: int


def get_or_create_lead(db: Session, *, external_id: str) -> Lead:
    stmt = select(Lead).where(Lead.external_id == external_id)
    lead = db.execute(stmt).scalar_one_or_none()
    if lead is not None:
        return lead

    lead = Lead(external_id=external_id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def calculate_operator_active_load(db: Session, operator_id: int) -> int:
    stmt = select(func.count(Contact.id)).where(
        Contact.operator_id == operator_id,
        Contact.is_active.is_(True),
    )
    count = db.execute(stmt).scalar_one()
    return int(count or 0)


def calculate_contacts_for_source(
    db: Session,
    *,
    operator_id: int,
    source_id: int,
) -> int:
    stmt = select(func.count(Contact.id)).where(
        Contact.operator_id == operator_id,
        Contact.source_id == source_id,
    )
    count = db.execute(stmt).scalar_one()
    return int(count or 0)


def pick_operator_for_source(db: Session, *, source_id: int) -> Operator | None:
    weights_stmt = (
        select(OperatorSourceWeight, Operator)
        .join(Operator, OperatorSourceWeight.operator_id == Operator.id)
        .where(
            OperatorSourceWeight.source_id == source_id,
            Operator.is_active.is_(True),
        )
    )
    rows = db.execute(weights_stmt).all()

    candidates: list[tuple[Operator, int, float]] = []
    for weight_row, operator in rows:
        active_load = calculate_operator_active_load(db, operator.id)
        if active_load >= operator.load_limit:
            continue

        contacts_for_source = calculate_contacts_for_source(
            db,
            operator_id=operator.id,
            source_id=source_id,
        )
        ratio = contacts_for_source / float(weight_row.weight)
        candidates.append((operator, weight_row.weight, ratio))

    if not candidates:
        return None

    # выбираем оператора с минимальным отношением "обращения / вес"
    candidates.sort(key=lambda item: (item[2], item[0].id))
    best_operator = candidates[0][0]
    return best_operator


def create_contact_for_lead(
    db: Session,
    *,
    external_lead_id: str,
    source_id: int,
    message: str | None,
) -> Contact:
    source = db.get(Source, source_id)
    if source is None:
        raise ValueError("Source not found")

    lead = get_or_create_lead(db, external_id=external_lead_id)
    operator = pick_operator_for_source(db, source_id=source_id)

    contact = Contact(
        lead_id=lead.id,
        source_id=source.id,
        operator_id=operator.id if operator is not None else None,
        message=message,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def get_distribution_stats(db: Session) -> list[DistributionInfo]:
    stmt = (
        select(
            Contact.operator_id,
            Contact.source_id,
            func.count(Contact.id),
        )
        .group_by(Contact.operator_id, Contact.source_id)
    )
    rows = db.execute(stmt).all()
    stats: list[DistributionInfo] = []
    for operator_id, source_id, count in rows:
        stats.append(
            DistributionInfo(
                operator_id=int(operator_id) if operator_id is not None else None,
                source_id=int(source_id),
                contacts_count=int(count or 0),
            )
        )
    return stats
