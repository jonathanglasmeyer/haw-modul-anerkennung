"""SQLAlchemy ORM models for NeonDB."""
from datetime import datetime
from typing import List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# Association table for Units ↔ Personen many-to-many relationship
units_personen = Table(
    "units_personen",
    Base.metadata,
    Column("unit_id", Integer, ForeignKey("units.id", ondelete="CASCADE"), primary_key=True),
    Column("person_id", Integer, ForeignKey("personen.id", ondelete="CASCADE"), primary_key=True),
)


class Person(Base):
    """Professor or staff member responsible for units."""
    __tablename__ = "personen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    units: Mapped[List["Unit"]] = relationship(
        "Unit",
        secondary=units_personen,
        back_populates="verantwortliche"
    )

    def __repr__(self) -> str:
        return f"<Person(id={self.id}, name='{self.name}')>"


class Module(Base):
    """Module definition."""
    __tablename__ = "module"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sws: Mapped[int | None] = mapped_column(Integer, nullable=True)
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lernziele: Mapped[str | None] = mapped_column(Text, nullable=True)
    pruefungsleistung: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    units: Mapped[List["Unit"]] = relationship("Unit", back_populates="module", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Module(id={self.id}, module_id='{self.module_id}', title='{self.title}')>"


class Unit(Base):
    """Unit (course component) definition."""
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    module_id: Mapped[int] = mapped_column(Integer, ForeignKey("module.id", ondelete="CASCADE"), nullable=False)
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sws: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workload: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lehrsprache: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lernziele: Mapped[str | None] = mapped_column(Text, nullable=True)
    inhalte: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    module: Mapped[Module] = relationship("Module", back_populates="units")
    verantwortliche: Mapped[List[Person]] = relationship(
        "Person",
        secondary=units_personen,
        back_populates="units"
    )

    def __repr__(self) -> str:
        return f"<Unit(id={self.id}, unit_id='{self.unit_id}', title='{self.title}')>"
