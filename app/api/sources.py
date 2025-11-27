from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Operator, OperatorSourceWeight, Source
from app.schemas import (
    OperatorWeightCreate,
    OperatorWeightPublic,
    SourceCreate,
    SourcePublic,
)

router = APIRouter()


@router.post("/", response_model=SourcePublic, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceCreate,
    db: Session = Depends(get_session),
) -> SourcePublic:
    existing_stmt = select(Source).where(Source.name == payload.name)
    if db.execute(existing_stmt).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source with this name already exists",
        )

    source = Source(name=payload.name)
    db.add(source)
    db.commit()
    db.refresh(source)
    return SourcePublic.model_validate(source)


@router.get("/", response_model=list[SourcePublic])
def list_sources(db: Session = Depends(get_session)) -> list[SourcePublic]:
    stmt = select(Source)
    sources = db.execute(stmt).scalars().all()
    return [SourcePublic.model_validate(source) for source in sources]


@router.post("/{source_id}/weights", response_model=list[OperatorWeightPublic])
def set_source_weights(
    source_id: int,
    payload: list[OperatorWeightCreate],
    db: Session = Depends(get_session),
) -> list[OperatorWeightPublic]:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one operator weight must be provided",
        )

    operator_ids = [item.operator_id for item in payload]
    operators_stmt = select(Operator.id).where(Operator.id.in_(operator_ids))
    existing_ids = {row[0] for row in db.execute(operators_stmt).all()}
    missing = set(operator_ids) - existing_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some operators do not exist",
        )

    db.execute(delete(OperatorSourceWeight).where(OperatorSourceWeight.source_id == source_id))

    new_weights: list[OperatorSourceWeight] = []
    for item in payload:
        weight = OperatorSourceWeight(
            operator_id=item.operator_id,
            source_id=source_id,
            weight=item.weight,
        )
        db.add(weight)
        new_weights.append(weight)

    db.commit()

    for weight in new_weights:
        db.refresh(weight)

    return [OperatorWeightPublic.model_validate(weight) for weight in new_weights]


@router.get("/{source_id}/weights", response_model=list[OperatorWeightPublic])
def get_source_weights(
    source_id: int,
    db: Session = Depends(get_session),
) -> list[OperatorWeightPublic]:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    stmt = select(OperatorSourceWeight).where(OperatorSourceWeight.source_id == source_id)
    weights = db.execute(stmt).scalars().all()
    return [OperatorWeightPublic.model_validate(weight) for weight in weights]
