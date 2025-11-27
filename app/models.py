from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    load_limit: Mapped[int] = mapped_column(Integer, nullable=False)

    contacts: Mapped[list[Contact]] = relationship(back_populates="operator")
    source_weights: Mapped[list[OperatorSourceWeight]] = relationship(back_populates="operator")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    contacts: Mapped[list[Contact]] = relationship(back_populates="source")
    operator_weights: Mapped[list[OperatorSourceWeight]] = relationship(back_populates="source")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    contacts: Mapped[list[Contact]] = relationship(back_populates="lead")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    lead: Mapped[Lead] = relationship(back_populates="contacts")
    source: Mapped[Source] = relationship(back_populates="contacts")
    operator: Mapped[Operator] = relationship(back_populates="contacts")


class OperatorSourceWeight(Base):
    __tablename__ = "operator_source_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)

    operator: Mapped[Operator] = relationship(back_populates="source_weights")
    source: Mapped[Source] = relationship(back_populates="operator_weights")
