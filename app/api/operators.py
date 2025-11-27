from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Contact, Operator
from app.schemas import OperatorCreate, OperatorPublic, OperatorRead, OperatorUpdate

router = APIRouter()


@router.post("/", response_model=OperatorPublic, status_code=status.HTTP_201_CREATED)
def create_operator(
    payload: OperatorCreate,
    db: Session = Depends(get_session),
) -> OperatorPublic:
    existing_stmt = select(Operator).where(Operator.name == payload.name)
    if db.execute(existing_stmt).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operator with this name already exists",
        )

    operator = Operator(
        name=payload.name,
        load_limit=payload.load_limit,
        is_active=payload.is_active,
    )
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return OperatorPublic.model_validate(operator)


@router.get("/", response_model=list[OperatorRead])
def list_operators(db: Session = Depends(get_session)) -> list[OperatorRead]:
    stmt = select(Operator)
    operators = list(db.execute(stmt).scalars().all())

    if not operators:
        return []

    operator_ids = [op.id for op in operators]

    load_stmt = (
        select(Contact.operator_id, func.count(Contact.id))
        .where(
            Contact.is_active.is_(True),
            Contact.operator_id.in_(operator_ids),
        )
        .group_by(Contact.operator_id)
    )
    loads: dict[int, int] = {}
    for operator_id, count in db.execute(load_stmt).all():
        loads[int(operator_id)] = int(count or 0)

    result: list[OperatorRead] = []
    for op in operators:
        result.append(
            OperatorRead(
                id=op.id,
                name=op.name,
                is_active=op.is_active,
                load_limit=op.load_limit,
                active_contacts=loads.get(op.id, 0),
            )
        )
    return result


@router.patch("/{operator_id}", response_model=OperatorPublic)
def update_operator(
    operator_id: int,
    payload: OperatorUpdate,
    db: Session = Depends(get_session),
) -> OperatorPublic:
    operator = db.get(Operator, operator_id)
    if operator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")

    if payload.load_limit is not None:
        operator.load_limit = payload.load_limit
    if payload.is_active is not None:
        operator.is_active = payload.is_active

    db.commit()
    db.refresh(operator)
    return OperatorPublic.model_validate(operator)
