from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OperatorBase(BaseModel):
    name: str = Field(..., max_length=100)
    load_limit: int = Field(..., ge=0)
    is_active: bool = True


class OperatorCreate(OperatorBase):
    pass


class OperatorUpdate(BaseModel):
    load_limit: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class OperatorPublic(OperatorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class OperatorRead(OperatorPublic):
    active_contacts: int


class SourceBase(BaseModel):
    name: str = Field(..., max_length=100)


class SourceCreate(SourceBase):
    pass


class SourcePublic(SourceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class OperatorWeightCreate(BaseModel):
    operator_id: int
    weight: int = Field(..., ge=1)


class OperatorWeightPublic(BaseModel):
    id: int
    operator_id: int
    source_id: int
    weight: int

    model_config = ConfigDict(from_attributes=True)


class LeadPublic(BaseModel):
    id: int
    external_id: str

    model_config = ConfigDict(from_attributes=True)


class ContactBase(BaseModel):
    message: str | None = Field(default=None, max_length=500)


class ContactCreate(ContactBase):
    external_lead_id: str
    source_id: int


class ContactPublic(ContactBase):
    id: int
    lead_id: int
    source_id: int
    operator_id: int | None
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ContactDetailed(ContactBase):
    id: int
    lead: LeadPublic
    source: SourcePublic
    operator: OperatorPublic | None
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LeadWithContacts(LeadPublic):
    contacts: list[ContactPublic]


class DistributionStat(BaseModel):
    operator_id: int | None
    source_id: int
    contacts_count: int
