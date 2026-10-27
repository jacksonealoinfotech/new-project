"""SQLAlchemy 2.x Declarative Base metadata registry."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Standard naming convention for deterministic constraints across PostgreSQL and SQLite
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative Base class for all ORM models with explicit naming conventions."""

    metadata = MetaData(naming_convention=naming_convention)
