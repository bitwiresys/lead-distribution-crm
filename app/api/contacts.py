from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Contact, Lead, Source
from app.schemas import (
    ContactCreate,
    ContactPublic,
    DistributionStat,
    LeadWithContacts,
)
from app.services import DistributionInfo, create_contact_for_lead, get_distribution_stats

router = APIRouter()


@router.post("/contacts", response_model=ContactPublic, status_code=status.HTTP_201_CREATED)
def register_contact(
    payload: ContactCreate,
    db: Session = Depends(get_session),
) -> ContactPublic:
    source = db.get(Source, payload.source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    try:
        contact = create_contact_for_lead(
            db,
            external_lead_id=payload.external_lead_id,
            source_id=payload.source_id,
            message=payload.message,
        )
    except ValueError as exc:  # защита от расхождений в логике
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ContactPublic.model_validate(contact)


@router.get("/leads", response_model=list[LeadWithContacts])
def list_leads(db: Session = Depends(get_session)) -> list[LeadWithContacts]:
    stmt = select(Lead).options(selectinload(Lead.contacts))
    leads = db.execute(stmt).scalars().all()
    return [LeadWithContacts.model_validate(lead) for lead in leads]


@router.get("/stats/distribution", response_model=list[DistributionStat])
def distribution_stats(db: Session = Depends(get_session)) -> list[DistributionStat]:
    stats: list[DistributionInfo] = get_distribution_stats(db)
    return [
        DistributionStat(
            operator_id=item.operator_id,
            source_id=item.source_id,
            contacts_count=item.contacts_count,
        )
        for item in stats
    ]


@router.get("/contacts", response_model=list[ContactPublic])
def list_contacts(db: Session = Depends(get_session)) -> list[ContactPublic]:
    stmt = select(Contact)
    contacts = db.execute(stmt).scalars().all()
    return [ContactPublic.model_validate(contact) for contact in contacts]
