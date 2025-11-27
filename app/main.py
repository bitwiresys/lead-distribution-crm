from __future__ import annotations

from fastapi import FastAPI

from app.api import contacts, operators, sources
from app.db import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lead Distribution CRM")

app.include_router(operators.router, prefix="/operators", tags=["operators"])
app.include_router(sources.router, prefix="/sources", tags=["sources"])
app.include_router(contacts.router, tags=["contacts"])
